from typing import Any, Literal, TypedDict

from app.agents.intent import Intent, IntentSlots


class CreationState(TypedDict, total=False):
    """Data passed through intent routing and the creation workflow."""

    task_id: str
    conversation_id: str
    user_input: str
    intent: Intent
    intent_confidence: float
    intent_slots: IntentSlots
    status: Literal[
        "needs_clarification",
        "running",
        "completed",
        "failed",
        "unsupported",
    ]
    current_step: str
    clarification_question: str | None
    retrieved_sources: list[dict[str, Any]]
    draft: str
    verification_notes: list[dict[str, Any]]
    result: dict[str, Any]
    error_code: str
    error_message: str
