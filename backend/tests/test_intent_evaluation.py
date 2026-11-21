from pathlib import Path

import pytest

from app.agents.evaluation import (
    IntentEvalCase,
    evaluate_threshold,
    load_eval_cases,
    scan_thresholds,
)
from app.agents.intent import Intent, IntentResult, IntentSlots, apply_intent_policy


def test_eval_dataset_is_valid_and_covers_each_intent() -> None:
    cases = load_eval_cases(Path(__file__).parent / "data" / "intent_eval.jsonl")

    assert len(cases) == 30
    assert {case.expected_intent for case in cases} == set(Intent)


def test_intent_policy_marks_missing_required_slots() -> None:
    result = IntentResult(
        intent=Intent.REVISE_DRAFT,
        confidence=0.9,
        slots=IntentSlots(draft_id="draft-1"),
    )

    decision = apply_intent_policy(result)

    assert decision.missing_fields == ["instruction"]
    assert decision.clarification_question == "你希望如何修改这份草稿？"
    assert result.missing_fields == []


@pytest.mark.parametrize(
    ("intent", "slots", "missing", "question"),
    [
        (Intent.CREATE_CONTENT, IntentSlots(), "topic", "你想创作什么主题的内容？"),
        (
            Intent.FACT_CHECK,
            IntentSlots(),
            "text",
            "请提供需要核查的文本或事实主张。",
        ),
        (
            Intent.REVISE_DRAFT,
            IntentSlots(draft_id="draft-1"),
            "instruction",
            "你希望如何修改这份草稿？",
        ),
    ],
)
def test_policy_asks_for_required_slots(intent, slots, missing, question) -> None:
    decision = apply_intent_policy(
        IntentResult(intent=intent, confidence=0.9, slots=slots)
    )

    assert decision.missing_fields == [missing]
    assert decision.clarification_question == question


def test_low_confidence_candidate_is_routed_to_clarify_without_mutating_source() -> None:
    candidate = IntentResult(
        intent=Intent.CHAT,
        confidence=0.5,
        slots=IntentSlots(),
    )

    decision = apply_intent_policy(candidate, threshold=0.65)

    assert candidate.intent == Intent.CHAT
    assert decision.intent == Intent.CLARIFY


def test_threshold_sweep_uses_clarification_policy_and_slots() -> None:
    cases = [
        {
            "id": "clear-create",
            "text": "写文章",
            "expected_intent": Intent.CREATE_CONTENT,
            "expected_slots": {"topic": "机器学习"},
        },
        {
            "id": "uncertain",
            "text": "帮我处理一下",
            "expected_intent": Intent.CLARIFY,
            "expected_slots": {},
        },
    ]
    predictions = [
        IntentResult(
            intent=Intent.CREATE_CONTENT,
            confidence=0.9,
            slots=IntentSlots(topic="机器学习"),
        ),
        IntentResult(
            intent=Intent.CHAT,
            confidence=0.5,
            slots=IntentSlots(),
        ),
    ]
    parsed_cases = [IntentEvalCase.model_validate(case) for case in cases]
    low_threshold = evaluate_threshold(parsed_cases, predictions, 0.4)
    high_threshold = evaluate_threshold(parsed_cases, predictions, 0.7)
    scanned = scan_thresholds(parsed_cases, predictions, [0.4, 0.7])

    assert low_threshold.accuracy == 0.5
    assert high_threshold.accuracy == 1.0
    assert high_threshold.clarification_rate == 0.5
    assert high_threshold.slot_accuracy == 1.0
    assert scanned == [low_threshold, high_threshold]
