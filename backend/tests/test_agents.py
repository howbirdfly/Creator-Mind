import json
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from app.agents.intent import (
    Intent,
    IntentClassificationError,
    IntentResult,
    IntentSlots,
    classify_intent,
)
from app.agents.tools import ToolContractError, invoke_tool
from app.agents.workflow import execute_workflow
from app.core.config import settings


def make_result(
    intent: Intent,
    slots: IntentSlots | None = None,
    *,
    confidence: float = 0.9,
    missing_fields: list[str] | None = None,
    question: str | None = None,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        confidence=confidence,
        slots=slots or IntentSlots(),
        missing_fields=missing_fields or [],
        clarification_question=question,
    )


def mock_tools(
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]],
    *,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    retrieved = sources if sources is not None else [{"id": "source-1", "text": "evidence"}]

    def search(args: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
        calls.append(("search_materials", args, context))
        return {"status": "ok" if retrieved else "no_results", "sources": retrieved}

    def write(args: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
        calls.append(("write_draft", args, context))
        return {"draft": "A generated draft."}

    def verify(args: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
        calls.append(("verify_draft", args, context))
        return {"status": "verified", "verification_notes": [{"claim": "supported"}]}

    def revise(args: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
        calls.append(("revise_draft", args, context))
        return {"draft": "A revised draft."}

    def chat(args: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
        calls.append(("respond_chat", args, context))
        return {"message": "A chat response."}

    return {
        "search_materials": search,
        "write_draft": write,
        "verify_draft": verify,
        "revise_draft": revise,
        "respond_chat": chat,
    }


def test_classify_intent_parses_openai_compatible_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_base_url", "https://model.example/v1")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    content = json.dumps(
        {
            "intent": "create_content",
            "confidence": 0.92,
            "slots": {"topic": "可信 AI", "audience": "创作者"},
            "missing_fields": [],
            "clarification_question": None,
        }
    )
    captured: dict[str, Any] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = classify_intent("写一篇关于可信 AI 的文章", client=client)

    assert result.intent == Intent.CREATE_CONTENT
    assert result.slots.topic == "可信 AI"
    assert captured["url"] == "https://model.example/v1/chat/completions"
    assert captured["body"]["response_format"] == {"type": "json_object"}


def test_classify_intent_returns_clarification_for_low_confidence() -> None:
    content = json.dumps(
        {
            "intent": "chat",
            "confidence": 0.2,
            "slots": {},
            "missing_fields": [],
            "clarification_question": None,
        }
    )
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
    )
    with httpx.Client(transport=transport) as client:
        result = classify_intent("帮我看看", client=client)

    assert result.intent == Intent.CLARIFY
    assert result.clarification_question


def test_classify_intent_handles_empty_input_without_model_call() -> None:
    result = classify_intent("   ")

    assert result.intent == Intent.CLARIFY
    assert result.missing_fields == ["user_input"]


def test_classify_intent_rejects_invalid_model_json() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})
    )
    with httpx.Client(transport=transport) as client:
        with pytest.raises(IntentClassificationError):
            classify_intent("你好", client=client)


def test_tool_contract_validates_input_and_passes_trusted_context() -> None:
    observed: dict[str, Any] = {}

    def search(args: dict[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
        observed["args"] = args
        observed["context"] = context
        return {"status": "ok", "sources": [{"id": "s1"}]}

    result = invoke_tool(
        {"search_materials": search},
        "search_materials",
        {"query": "topic"},
        {"user_id": "user-1"},
    )

    assert result["status"] == "ok"
    assert observed["args"] == {"query": "topic", "source_ids": [], "limit": 5}
    assert observed["context"] == {"user_id": "user-1"}


def test_tool_contract_rejects_invalid_input_and_output() -> None:
    with pytest.raises(ToolContractError) as invalid_input:
        invoke_tool({"respond_chat": lambda *_: {"message": "ok"}}, "respond_chat", {"message": ""})
    assert invalid_input.value.direction == "input"

    with pytest.raises(ToolContractError) as invalid_output:
        invoke_tool({"respond_chat": lambda *_: {}}, "respond_chat", {"message": "hello"})
    assert invalid_output.value.direction == "output"


def test_search_tool_rejects_inconsistent_empty_status() -> None:
    with pytest.raises(ToolContractError) as error:
        invoke_tool(
            {"search_materials": lambda *_: {"status": "ok", "sources": []}},
            "search_materials",
            {"query": "topic"},
        )
    assert error.value.direction == "output"


def test_create_content_workflow_runs_three_tools_in_order() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    result = make_result(
        Intent.CREATE_CONTENT,
        IntentSlots(topic="可信 AI", format="article", audience="创作者"),
    )

    state = execute_workflow(
        "写文章",
        tools=mock_tools(calls),
        execution_context={"user_id": "user-1", "task_id": "task-1"},
        classifier=lambda *_: result,
    )

    assert state["status"] == "completed"
    assert state["draft"] == "A generated draft."
    assert state["result"]["verification"]["status"] == "verified"
    assert [call[0] for call in calls] == ["search_materials", "write_draft", "verify_draft"]
    assert all(call[2]["user_id"] == "user-1" for call in calls)


def test_create_content_without_sources_is_explicitly_unverified() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    state = execute_workflow(
        "写文章",
        tools=mock_tools(calls, sources=[]),
        classifier=lambda *_: make_result(
            Intent.CREATE_CONTENT,
            IntentSlots(topic="可信 AI"),
        ),
    )

    assert state["status"] == "completed"
    assert state["result"]["verification"]["status"] == "not_verified"
    assert [call[0] for call in calls] == ["search_materials", "write_draft"]


def test_fact_check_routes_through_search_then_verification() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    state = execute_workflow(
        "核查这个说法",
        tools=mock_tools(calls),
        classifier=lambda *_: make_result(
            Intent.FACT_CHECK,
            IntentSlots(text="事实主张"),
        ),
    )

    assert state["status"] == "completed"
    assert [call[0] for call in calls] == ["search_materials", "verify_draft"]


def test_retrieve_material_returns_explicit_no_results() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    state = execute_workflow(
        "找一下有关可信 AI 的素材",
        tools=mock_tools(calls, sources=[]),
        classifier=lambda *_: make_result(
            Intent.RETRIEVE_MATERIAL,
            IntentSlots(query="可信 AI"),
        ),
    )

    assert state["status"] == "completed"
    assert state["result"]["status"] == "no_results"
    assert state["retrieved_sources"] == []
    assert [call[0] for call in calls] == ["search_materials"]


def test_revise_draft_searches_evidence_before_verification() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    state = execute_workflow(
        "修改草稿",
        tools=mock_tools(calls),
        classifier=lambda *_: make_result(
            Intent.REVISE_DRAFT,
            IntentSlots(draft_id="draft-1", instruction="简洁一些"),
        ),
    )

    assert state["status"] == "completed"
    assert [call[0] for call in calls] == ["revise_draft", "search_materials", "verify_draft"]


def test_chat_routes_to_chat_tool() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    state = execute_workflow(
        "什么是可信创作？",
        tools=mock_tools(calls),
        classifier=lambda *_: make_result(Intent.CHAT),
    )

    assert state["status"] == "completed"
    assert state["result"]["message"] == "A chat response."
    assert [call[0] for call in calls] == ["respond_chat"]


def test_clarification_does_not_call_tools() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    state = execute_workflow(
        "帮我处理一下",
        tools=mock_tools(calls),
        classifier=lambda *_: make_result(
            Intent.CLARIFY,
            question="你想处理什么？",
        ),
    )

    assert state["status"] == "needs_clarification"
    assert state["clarification_question"] == "你想处理什么？"
    assert calls == []


def test_missing_tool_returns_unsupported() -> None:
    state = execute_workflow(
        "你好",
        tools={},
        classifier=lambda *_: make_result(Intent.CHAT),
    )

    assert state["status"] == "unsupported"
    assert state["error_code"] == "tool_unavailable"


def test_tool_failure_returns_failed_state() -> None:
    calls: list[tuple[str, dict[str, Any], Mapping[str, Any]]] = []
    tools = mock_tools(calls)
    tools["search_materials"] = lambda *_: {"status": "ok", "sources": []}
    state = execute_workflow(
        "写文章",
        tools=tools,
        classifier=lambda *_: make_result(
            Intent.CREATE_CONTENT,
            IntentSlots(topic="可信 AI"),
        ),
    )

    assert state["status"] == "failed"
    assert state["error_code"] == "tool_contract_error"


def test_intent_classification_failure_returns_failed_state() -> None:
    def fail_classifier(*_: Any) -> IntentResult:
        raise IntentClassificationError("model unavailable")

    state = execute_workflow("你好", tools={}, classifier=fail_classifier)

    assert state["status"] == "failed"
    assert state["error_code"] == "intent_classification_failed"
