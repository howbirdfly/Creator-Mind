import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agents.intent import (
    INTENT_CLARIFICATION_THRESHOLD,
    Intent,
    IntentClassificationError,
    IntentResult,
    IntentSlots,
    apply_intent_policy,
    classify_intent_candidate,
)


class IntentEvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    expected_intent: Intent
    expected_slots: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ThresholdMetrics:
    threshold: float
    accuracy: float
    macro_f1: float
    clarification_rate: float
    slot_accuracy: float | None


def load_eval_cases(path: Path) -> list[IntentEvalCase]:
    cases: list[IntentEvalCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = IntentEvalCase.model_validate_json(line)
            IntentSlots.model_validate(case.expected_slots)
            cases.append(case)
        except ValidationError as exc:
            raise ValueError(f"评测数据第 {line_number} 行格式错误") from exc
    if not cases:
        raise ValueError("评测数据为空")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("评测数据中的 id 必须唯一")
    return cases


def _slot_value_matches(expected: Any, actual: Any) -> bool:
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().casefold() == actual.strip().casefold()
    return expected == actual


def _routed_intent(candidate: IntentResult, threshold: float) -> Intent:
    decision = apply_intent_policy(candidate, threshold=threshold)
    if decision.intent == Intent.CLARIFY or decision.missing_fields:
        return Intent.CLARIFY
    return decision.intent


def evaluate_threshold(
    cases: list[IntentEvalCase],
    predictions: list[IntentResult],
    threshold: float,
) -> ThresholdMetrics:
    if len(cases) != len(predictions):
        raise ValueError("样例数与预测数不一致")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold 必须在 0 到 1 之间")

    labels = list(Intent)
    routed = [_routed_intent(prediction, threshold) for prediction in predictions]
    correct = sum(
        predicted == case.expected_intent for case, predicted in zip(cases, routed, strict=True)
    )
    f1_scores = []
    for label in labels:
        true_positive = sum(
            actual == label and predicted == label
            for actual, predicted in zip(
                (case.expected_intent for case in cases), routed, strict=True
            )
        )
        false_positive = sum(
            actual != label and predicted == label
            for actual, predicted in zip(
                (case.expected_intent for case in cases), routed, strict=True
            )
        )
        false_negative = sum(
            actual == label and predicted != label
            for actual, predicted in zip(
                (case.expected_intent for case in cases), routed, strict=True
            )
        )
        denominator = 2 * true_positive + false_positive + false_negative
        f1_scores.append(2 * true_positive / denominator if denominator else 0.0)

    slot_total = 0
    slot_correct = 0
    for case, prediction in zip(cases, predictions, strict=True):
        slots = prediction.slots.model_dump()
        for key, expected in case.expected_slots.items():
            slot_total += 1
            if _slot_value_matches(expected, slots.get(key)):
                slot_correct += 1

    return ThresholdMetrics(
        threshold=threshold,
        accuracy=correct / len(cases),
        macro_f1=sum(f1_scores) / len(labels),
        clarification_rate=sum(intent == Intent.CLARIFY for intent in routed) / len(routed),
        slot_accuracy=slot_correct / slot_total if slot_total else None,
    )


def scan_thresholds(
    cases: list[IntentEvalCase],
    predictions: list[IntentResult],
    thresholds: list[float],
) -> list[ThresholdMetrics]:
    if not thresholds:
        raise ValueError("至少提供一个 threshold")
    return [evaluate_threshold(cases, predictions, threshold) for threshold in thresholds]


def _parse_thresholds(value: str) -> list[float]:
    try:
        thresholds = [float(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("阈值需为逗号分隔的数字") from exc
    if not thresholds or any(not 0 <= item <= 1 for item in thresholds):
        raise argparse.ArgumentTypeError("阈值必须在 0 到 1 之间")
    return thresholds


def main() -> None:
    parser = argparse.ArgumentParser(description="使用配置模型评测意图识别并扫描澄清阈值")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "tests" / "data" / "intent_eval.jsonl",
    )
    parser.add_argument(
        "--thresholds",
        type=_parse_thresholds,
        default=[round(index / 100, 2) for index in range(0, 101, 5)],
        help="逗号分隔的候选阈值；默认扫描 0.00 到 1.00，每次递增 0.05",
    )
    args = parser.parse_args()

    try:
        cases = load_eval_cases(args.dataset)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    predictions: list[IntentResult] = []
    with httpx.Client(timeout=30) as client:
        for index, case in enumerate(cases, start=1):
            try:
                prediction = classify_intent_candidate(case.text, client=client)
            except IntentClassificationError as exc:
                raise SystemExit(f"评测在样例 {case.id} 失败：{exc}") from exc
            predictions.append(prediction)
            print(
                f"[{index}/{len(cases)}] {case.id}: "
                f"{prediction.intent.value} (confidence={prediction.confidence:.2f})"
            )

    metrics = scan_thresholds(cases, predictions, args.thresholds)
    print("\nthreshold  accuracy  macro_f1  clarification_rate  slot_accuracy")
    for item in metrics:
        slot_accuracy = "n/a" if item.slot_accuracy is None else f"{item.slot_accuracy:.3f}"
        print(
            f"{item.threshold:9.2f}  {item.accuracy:8.3f}  {item.macro_f1:8.3f}  "
            f"{item.clarification_rate:18.3f}  {slot_accuracy:>13}"
        )

    best = max(
        metrics,
        key=lambda item: (
            item.macro_f1,
            -abs(item.threshold - INTENT_CLARIFICATION_THRESHOLD),
        ),
    )
    print(
        f"\n当前阈值：{INTENT_CLARIFICATION_THRESHOLD:.2f}；"
        f"本次样例集 macro-F1 最优阈值：{best.threshold:.2f} "
        f"（macro-F1={best.macro_f1:.3f}，覆盖率={1 - best.clarification_rate:.3f}）。"
    )
    print("阈值建议仅适用于本次样例集；确认样例代表性后再更新生产阈值。")


if __name__ == "__main__":
    main()
