# 意图识别与 Workflow

本文说明 `backend/app/agents` 中已经实现的意图识别、工具契约和工作流路由，并列出其他模块接入所需的接口。当前仓库尚未把该工作流挂到 FastAPI 或 Celery；检索、写作、核查、草稿和聊天工具也由各业务模块提供。

## 当前实现

| 文件 | 已实现内容 |
|---|---|
| `intent.py` | 调用 OpenAI-compatible Chat Completions；校验模型返回的意图、置信度和槽位；识别低置信度、缺少主题等需要澄清的请求 |
| `tools.py` | 定义五种工具的 Pydantic 输入/输出 Schema；只允许调用注册表中的工具，并在调用前后校验数据 |
| `state.py` | 定义意图、槽位、流程步骤、检索来源、草稿、核查结果和错误状态 |
| `workflow.py` | 按已识别的意图确定性路由；处理澄清、工具缺失、工具契约错误及执行失败 |

业务工具的实现、HTTP 接口、Celery 任务、会话/任务持久化不在本模块中。

## 意图识别

调用 `classify_intent(user_input, context=None)`，返回 `IntentResult`：

| 意图 | 用途 | 必要槽位 |
|---|---|---|
| `create_content` | 创建内容 | `topic` |
| `retrieve_material` | 搜索素材 | 可选 `query`；缺省时使用原始输入 |
| `revise_draft` | 修改已有草稿 | `draft_id`、`instruction` |
| `fact_check` | 核查文本/主张 | `text` |
| `chat` | 一般对话或创作咨询 | 无 |
| `clarify` | 意图不明或置信度过低 | `clarification_question` |

可抽取槽位还有 `format`、`audience`、`length` 和 `source_ids`。未明确提供的槽位不应由模型猜测。置信度阈值在 `intent.py` 中设为 `0.65`，这是尚未用真实请求校准的临时值。

模型配置来自 `app.core.config.settings`：

- `CREATORMIND_LLM_BASE_URL`：OpenAI-compatible API base URL；代码会追加 `/chat/completions`。
- `CREATORMIND_LLM_MODEL`：模型名。
- `CREATORMIND_LLM_API_KEY`：API Key；支持不需要 Key 的本地服务。

模型需要返回符合 `IntentResult` 的 JSON。请求失败或输出不符合 Schema 时，分类器抛出 `IntentClassificationError`；`execute_workflow()` 会把它转换为 `failed` 状态。

## Workflow 路由

```text
create_content     → search_materials → write_draft → verify_draft
retrieve_material  → search_materials
revise_draft       → revise_draft → search_materials → verify_draft
fact_check         → search_materials → verify_draft
chat               → respond_chat
clarify            → 返回澄清问题，不调用工具
```

模型只产出受 Schema 约束的意图与槽位；工具选择由 Python 路由固定决定，不接受模型生成的函数名或代码。检索无来源时，创作/核查流程会返回 `not_verified` 说明，不会调用核查工具并声称已完成核查。

`execute_workflow()` 返回 `CreationState`，主要状态如下：

| `status` | 含义 |
|---|---|
| `completed` | 路由已执行完；需结合 `result.verification.status` 判断内容是否核查通过 |
| `needs_clarification` | 必要信息不足或分类器无法确定意图 |
| `unsupported` | 对应工具尚未注册 |
| `failed` | 模型、工具执行或工具契约发生错误 |

## 工具接入契约

API/任务调用方建立工具实现，并传入 `tools` 注册表。每个执行器的签名为：

```python
def executor(arguments: dict, execution_context: Mapping[str, Any]) -> dict:
    ...
```

`arguments` 会先经对应 Pydantic 输入 Schema 校验，再传给执行器；返回的 `dict` 也会按输出 Schema 校验。`execution_context` 是调用方提供的可信上下文，可包含 `user_id`、`conversation_id`、`task_id`。工具需使用可信 `user_id` 校验素材或草稿权限，不要从用户输入或模型槽位中取身份信息。

| 工具 | 输入字段 | 必须返回 |
|---|---|---|
| `search_materials` | `query`、`source_ids`（默认空数组）、`limit`（默认 5） | `status` 为 `ok` 或 `no_results`，以及 `sources`；`ok` 必须有来源，`no_results` 必须为空 |
| `write_draft` | `topic`、`format`、`audience`、`length`、`sources` | 非空 `draft` |
| `verify_draft` | `text`、`sources` | `status` 为 `verified`、`partial` 或 `not_verified`，以及 `verification_notes` |
| `revise_draft` | `draft_id`、`instruction` | 非空 `draft` |
| `respond_chat` | `message` | 非空 `message` |

## 调用示例

下列业务执行器由对应模块提供；本目录不包含它们的实现：

```python
from app.agents.workflow import execute_workflow

tools = {
    "search_materials": search_materials_executor,
    "write_draft": write_draft_executor,
    "verify_draft": verify_draft_executor,
    "revise_draft": revise_draft_executor,
    "respond_chat": respond_chat_executor,
}

state = execute_workflow(
    "写一篇面向知识创作者的可信 AI 工作流文章",
    tools=tools,
    context=None,  # 可选：对话模块提供的有限上下文文本
    execution_context={"user_id": authenticated_user_id, "conversation_id": conversation_id},
)
```

当前 `execute_workflow()` 为同步函数。接入时由 API/任务模块负责调用它，并将返回的 `CreationState` 映射到自己的响应或任务状态接口。对话模块可将有限历史作为 `context` 传给分类器；会话历史的读取和保存由对话模块负责。

## 意图评测与阈值扫描

`backend/tests/data/intent_eval.jsonl` 包含 30 条手工标注的中文样例，每种意图各 5 条。它用于初步比较分类路由、澄清率和槽位抽取表现，不代表已经校准完成的通用基准。

在 `backend` 目录配置好 `CREATORMIND_LLM_BASE_URL`、`CREATORMIND_LLM_MODEL` 和可选的 `CREATORMIND_LLM_API_KEY` 后运行：

```powershell
python -m app.agents.evaluation
```

命令对每条样例调用一次模型，再在本地扫描 `0.00` 到 `1.00` 的置信度阈值，并输出准确率、Macro-F1、澄清率和已标注槽位精确匹配率。可用 `--thresholds 0.50,0.60,0.65,0.70` 指定候选阈值。阈值建议依据 Macro-F1 选择，平分时优先靠近当前值 `0.65`；脚本只给建议，不自动修改生产配置。每次评测会发起 30 次模型请求，阈值扫描不会重复调用模型。
