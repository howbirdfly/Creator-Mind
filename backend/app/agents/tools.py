from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchMaterialsInput(ToolInput):
    query: str = Field(min_length=1)
    source_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class WriteDraftInput(ToolInput):
    topic: str = Field(min_length=1)
    format: str | None = None
    audience: str | None = None
    length: int | None = Field(default=None, ge=1, le=100_000)
    sources: list[dict[str, Any]]


class VerifyDraftInput(ToolInput):
    text: str = Field(min_length=1)
    sources: list[dict[str, Any]]


class ReviseDraftInput(ToolInput):
    draft_id: str = Field(min_length=1)
    instruction: str = Field(min_length=1)


class RespondChatInput(ToolInput):
    message: str = Field(min_length=1)


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchMaterialsOutput(ToolOutput):
    status: Literal["ok", "no_results"]
    sources: list[dict[str, Any]]

    @model_validator(mode="after")
    def validate_status_matches_sources(self) -> "SearchMaterialsOutput":
        if (self.status == "no_results") != (not self.sources):
            raise ValueError("status 必须与 sources 是否为空一致")
        return self


class WriteDraftOutput(ToolOutput):
    draft: str = Field(min_length=1)


class VerifyDraftOutput(ToolOutput):
    status: Literal["verified", "partial", "not_verified"]
    verification_notes: list[dict[str, Any]]


class ReviseDraftOutput(ToolOutput):
    draft: str = Field(min_length=1)


class RespondChatOutput(ToolOutput):
    message: str = Field(min_length=1)


@dataclass(frozen=True)
class ToolDefinition:
    """Validated contract for a capability supplied by another project module."""

    name: str
    description: str
    input_model: type[ToolInput]
    output_model: type[ToolOutput]

    @property
    def parameters(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()


ToolExecutor = Callable[[dict[str, Any], Mapping[str, Any]], dict[str, Any]]
ToolRegistry = Mapping[str, ToolExecutor]


# These are interfaces, not implementations. The owning modules inject executors.
TOOL_DEFINITIONS = {
    "search_materials": ToolDefinition(
        name="search_materials",
        description="在当前用户授权的素材范围内检索参考资料。空结果必须显式返回 no_results。",
        input_model=SearchMaterialsInput,
        output_model=SearchMaterialsOutput,
    ),
    "write_draft": ToolDefinition(
        name="write_draft",
        description="根据主题、写作要求和检索证据生成草稿。",
        input_model=WriteDraftInput,
        output_model=WriteDraftOutput,
    ),
    "verify_draft": ToolDefinition(
        name="verify_draft",
        description="对草稿中的事实主张进行核查并返回结构化状态和说明。",
        input_model=VerifyDraftInput,
        output_model=VerifyDraftOutput,
    ),
    "revise_draft": ToolDefinition(
        name="revise_draft",
        description="根据用户要求修改指定草稿。",
        input_model=ReviseDraftInput,
        output_model=ReviseDraftOutput,
    ),
    "respond_chat": ToolDefinition(
        name="respond_chat",
        description="回答一般交流或创作咨询，不执行素材或草稿操作。",
        input_model=RespondChatInput,
        output_model=RespondChatOutput,
    ),
}


class WorkflowToolUnavailable(RuntimeError):
    def __init__(self, tool_name: str) -> None:
        super().__init__(f"工作流工具尚未接入：{tool_name}")
        self.tool_name = tool_name


class ToolContractError(RuntimeError):
    """Raised when a tool input or output does not match its declared contract."""

    def __init__(self, tool_name: str, direction: Literal["input", "output"]) -> None:
        super().__init__(f"工作流工具 {tool_name} 的{direction}不符合约定")
        self.tool_name = tool_name
        self.direction = direction


def invoke_tool(
    registry: ToolRegistry,
    name: str,
    arguments: dict[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate both sides of an allowlisted tool call."""
    definition = TOOL_DEFINITIONS.get(name)
    if definition is None:
        raise ValueError(f"未声明的工作流工具：{name}")
    executor = registry.get(name)
    if executor is None:
        raise WorkflowToolUnavailable(name)
    try:
        validated_input = definition.input_model.model_validate(arguments)
    except ValidationError as exc:
        raise ToolContractError(name, "input") from exc

    result = executor(validated_input.model_dump(), context or {})
    if not isinstance(result, dict):
        raise ToolContractError(name, "output")
    try:
        validated_output = definition.output_model.model_validate(result)
    except ValidationError as exc:
        raise ToolContractError(name, "output") from exc
    return validated_output.model_dump()
