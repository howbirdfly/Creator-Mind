import logging
from collections.abc import Callable, Mapping
from typing import Any, TypedDict

from app.agents.intent import Intent, IntentClassificationError, IntentResult, classify_intent
from app.agents.state import CreationState
from app.agents.tools import (
    ToolContractError,
    ToolRegistry,
    WorkflowToolUnavailable,
    invoke_tool,
)

logger = logging.getLogger(__name__)


class WorkflowContext(TypedDict, total=False):
    """Trusted execution metadata supplied by the API/task caller, never by the LLM."""

    user_id: str
    conversation_id: str
    task_id: str


IntentClassifier = Callable[[str, str | None], IntentResult]


def _run_tool(
    tools: ToolRegistry,
    name: str,
    arguments: dict[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    return invoke_tool(tools, name, arguments, context)


def _clarification_state(state: CreationState, intent: IntentResult) -> CreationState:
    return {
        **state,
        "intent": intent.intent,
        "intent_confidence": intent.confidence,
        "intent_slots": intent.slots,
        "status": "needs_clarification",
        "current_step": "clarify",
        "clarification_question": intent.clarification_question,
        "result": {"question": intent.clarification_question},
    }


def _verification_result(
    tools: ToolRegistry,
    text: str,
    sources: list[dict[str, Any]],
    execution_context: Mapping[str, Any],
) -> dict[str, Any]:
    if not sources:
        return {
            "status": "not_verified",
            "verification_notes": [
                {"status": "not_verified", "message": "没有检索到可用于核查的来源。"}
            ],
        }
    return _run_tool(
        tools,
        "verify_draft",
        {"text": text, "sources": sources},
        execution_context,
    )


def execute_workflow(
    user_input: str,
    *,
    tools: ToolRegistry,
    context: str | None = None,
    execution_context: WorkflowContext | None = None,
    classifier: IntentClassifier = classify_intent,
) -> CreationState:
    """Classify a request and route it through the allowlisted MVP workflow.

    Tool implementations are injected by the modules that own retrieval, drafting,
    verification, and chat. The LLM selects only an intent; it cannot name a callable.
    """
    trusted_context = dict(execution_context or {})
    state: CreationState = {
        "user_input": user_input,
        "status": "running",
        "current_step": "classify_intent",
    }
    if trusted_context.get("conversation_id"):
        state["conversation_id"] = str(trusted_context["conversation_id"])
    if trusted_context.get("task_id"):
        state["task_id"] = str(trusted_context["task_id"])

    try:
        intent_result = classifier(user_input, context)
    except IntentClassificationError as exc:
        logger.warning(
            "Intent classification failed (task_id=%s, error_type=%s)",
            trusted_context.get("task_id"),
            type(exc).__name__,
        )
        state.update(
            status="failed",
            error_code="intent_classification_failed",
            error_message=str(exc),
        )
        return state

    state.update(
        intent=intent_result.intent,
        intent_confidence=intent_result.confidence,
        intent_slots=intent_result.slots,
    )
    if intent_result.intent == Intent.CLARIFY or intent_result.missing_fields:
        return _clarification_state(state, intent_result)

    slots = intent_result.slots
    try:
        if intent_result.intent == Intent.CHAT:
            state["current_step"] = "respond_chat"
            result = _run_tool(
                tools, "respond_chat", {"message": user_input}, trusted_context
            )
            state.update(status="completed", result=result)
            return state

        if intent_result.intent == Intent.RETRIEVE_MATERIAL:
            state["current_step"] = "search_materials"
            result = _run_tool(
                tools,
                "search_materials",
                {"query": slots.query or user_input, "source_ids": slots.source_ids},
                trusted_context,
            )
            state.update(
                status="completed",
                retrieved_sources=result["sources"],
                result=result,
            )
            return state

        if intent_result.intent == Intent.CREATE_CONTENT:
            if not slots.topic:
                return _clarification_state(
                    state,
                    intent_result.model_copy(
                        update={
                            "missing_fields": ["topic"],
                            "clarification_question": "你想创作什么主题的内容？",
                        }
                    ),
                )
            state["current_step"] = "research"
            research = _run_tool(
                tools,
                "search_materials",
                {"query": slots.topic, "source_ids": slots.source_ids},
                trusted_context,
            )
            sources = research["sources"]
            state["retrieved_sources"] = sources

            state["current_step"] = "writer"
            writing = _run_tool(
                tools,
                "write_draft",
                {
                    "topic": slots.topic,
                    "format": slots.format,
                    "audience": slots.audience,
                    "length": slots.length,
                    "sources": sources,
                },
                trusted_context,
            )
            draft = writing["draft"]
            state["draft"] = draft

            state["current_step"] = "verification"
            verification = _verification_result(tools, draft, sources, trusted_context)
            state.update(
                status="completed",
                verification_notes=verification["verification_notes"],
                result={"draft": draft, "sources": sources, "verification": verification},
            )
            return state

        if intent_result.intent == Intent.FACT_CHECK:
            if not slots.text:
                return _clarification_state(
                    state,
                    intent_result.model_copy(
                        update={
                            "missing_fields": ["text"],
                            "clarification_question": "请提供需要核查的文本或事实主张。",
                        }
                    ),
                )
            state["current_step"] = "research"
            research = _run_tool(
                tools,
                "search_materials",
                {"query": slots.text, "source_ids": slots.source_ids},
                trusted_context,
            )
            sources = research["sources"]
            state["retrieved_sources"] = sources
            state["current_step"] = "verification"
            verification = _verification_result(tools, slots.text, sources, trusted_context)
            state.update(
                status="completed",
                verification_notes=verification["verification_notes"],
                result={"sources": sources, "verification": verification},
            )
            return state

        if intent_result.intent == Intent.REVISE_DRAFT:
            missing = []
            if not slots.draft_id:
                missing.append("draft_id")
            if not slots.instruction:
                missing.append("instruction")
            if missing:
                return _clarification_state(
                    state,
                    intent_result.model_copy(
                        update={
                            "missing_fields": missing,
                            "clarification_question": "请提供要修改的草稿及具体修改要求。",
                        }
                    ),
                )

            state["current_step"] = "revise_draft"
            revision = _run_tool(
                tools,
                "revise_draft",
                {"draft_id": slots.draft_id, "instruction": slots.instruction},
                trusted_context,
            )
            draft = revision["draft"]
            state["draft"] = draft

            state["current_step"] = "research"
            research = _run_tool(
                tools,
                "search_materials",
                {"query": draft[:2_000], "source_ids": slots.source_ids},
                trusted_context,
            )
            sources = research["sources"]
            state["retrieved_sources"] = sources
            state["current_step"] = "verification"
            verification = _verification_result(tools, draft, sources, trusted_context)
            state.update(
                status="completed",
                verification_notes=verification["verification_notes"],
                result={"draft": draft, "sources": sources, "verification": verification},
            )
            return state

        state.update(status="unsupported", current_step="route")
        return state
    except WorkflowToolUnavailable as exc:
        state.update(
            status="unsupported",
            error_code="tool_unavailable",
            error_message=str(exc),
        )
        return state
    except ToolContractError as exc:
        logger.error(
            "Workflow tool contract failed (task_id=%s, step=%s, tool=%s, direction=%s)",
            trusted_context.get("task_id"),
            state.get("current_step"),
            exc.tool_name,
            exc.direction,
        )
        state.update(
            status="failed",
            error_code="tool_contract_error",
            error_message=str(exc),
        )
        return state
    except Exception as exc:
        logger.error(
            "Workflow step failed (task_id=%s, step=%s, error_type=%s)",
            trusted_context.get("task_id"),
            state.get("current_step", "unknown"),
            type(exc).__name__,
        )
        state.update(
            status="failed",
            error_code="workflow_step_failed",
            error_message=(
                f"步骤 {state.get('current_step', 'unknown')} 执行失败：{type(exc).__name__}"
            ),
        )
        return state
