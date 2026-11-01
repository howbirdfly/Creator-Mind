from typing import Literal, TypedDict


class CreationState(TypedDict, total=False):
    """Shared state passed between the MVP creation agents."""

    task_id: str
    topic: str
    status: Literal["queued", "researching", "writing", "verifying", "completed", "failed"]
    outline: list[str]
    retrieved_sources: list[dict[str, str]]
    draft: str
    verification_notes: list[dict[str, str]]