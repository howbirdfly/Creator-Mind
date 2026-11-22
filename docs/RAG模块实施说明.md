# RAG 模块实施说明

本模块负责授权素材的上传、解析、索引、检索、证据定位和删除，并为 Research 工具提供可接入的事实证据。支持 TXT、Markdown、文字型 PDF，以及单帧 PNG、JPEG、WebP 图片。扫描件 PDF OCR、网页抓取和复杂重排暂未实现。

## 运行依赖

1. PostgreSQL 16 + pgvector、Redis、MinIO，以及 OpenAI-compatible 的 embedding 服务。默认模型为 `nomic-embed-text`，向量维度固定为 768；换模型时必须同时确认维度并重建索引。
2. 后端安装 `pip install -e '.[dev,agent]'`，执行 `alembic upgrade head`，启动 FastAPI 和 Celery Worker。
3. API 与 Worker 都需要 `CREATORMIND_EMBEDDING_BASE_URL`、`CREATORMIND_EMBEDDING_MODEL` 等相同配置。图片还需配置支持图片输入与 OpenAI-compatible `chat/completions` 的 `CREATORMIND_VISION_BASE_URL`、`CREATORMIND_VISION_MODEL` 和按需配置的密钥；未配置模型时，图片上传会明确返回 503。完整容器配置已透传这些变量。
4. 平台认证中间件必须在 `request.state.user_id` 放入已验证的用户身份。RAG 路由不会接受客户端传入的 `user_id`；认证模块接入前接口返回 401。

索引时资料片段会发送到配置的 embedding 服务；图片会先发送给视觉模型。默认地址是本机 Ollama 兼容接口。若改用外部服务，需与用户授权的数据发送范围一致。

## 图片索引与上下文

图片在上传时按文件内容验证格式、像素数和静态帧；原图保存在 MinIO。索引任务将图片缩放并去除 EXIF，调用视觉模型分别提取可见文字和画面描述，再以这两部分文本切片、向量化。视觉模型输出属于机器分析，`origin=image_analysis`、`extraction_model` 会随每条证据返回。引用回查可访问原图下载接口进行人工核对。图片的 `start_offset`/`end_offset` 指向机器分析文本，**不是图片像素坐标**。图片描述只能作为可检索线索，不能自动证明图片以外的事实。

文档按页和句段边界切片；Markdown 会保留最近的标题作为章节标签。每段的向量输入包含标题、章节、页码、正文及最多各 120 字相邻内容；返回给 Writer 的 `excerpt` 仍是可定位的原文，`context_before`/`context_after` 单独返回，避免混淆引用范围。语义搜索可带最多 1000 字的 `context`（如当前创作任务背景），当前工作流的 `search_materials` 工具契约尚未接入此参数；接入时需扩展该契约；关键词搜索只按字面问题检索。高度重叠的结果会去重，避免同一段反复占用证据预算。

## API 契约（均在 `/api/v1` 下）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/sources` | multipart 字段 `file`、`kind=fact\|style`、可选 `title`；支持文档及图片，返回 202 和索引状态 |
| GET | `/sources` | 当前用户未删除资料列表 |
| GET | `/sources/{source_id}` | 资料状态和失败原因 |
| POST | `/sources/{source_id}/retry` | 重试索引失败的资料 |
| POST | `/sources/{source_id}/reindex` | 为已就绪或失败的资料重建向量索引 |
| POST | `/sources/search` | JSON：`query`、可选 `context`、`kind`、`mode=semantic\|keyword`、`source_ids`、`limit` |
| GET | `/sources/{source_id}/citations/{chunk_id}` | 回查原文、页码或章节和字符偏移；删除后返回 `deleted` |
| GET | `/sources/{source_id}/download` | 下载有权限的原文件 |
| DELETE | `/sources/{source_id}` | 清理文件和向量，保留不含正文的删除标记 |

`kind=fact`、`mode=semantic` 是搜索默认值。历史作品用于模仿表达时应上传为 `style`，不会混入事实证据。`keyword` 模式按原文或标题做字面匹配，适合人名、缩写和编号。证据编号 `E1` 等只在单次搜索结果中有效；长期引用必须保存 `source_id + chunk_id + source_version`。`similarity` 在语义模式表示向量相关性，在关键词模式固定为 1，仅表示命中；它不表示事实已被核查。

首期每次上传生成独立 `source_id`，版本为 1；尚无原资料就地更新接口。需要换文件时，上传新资料并删除旧资料，旧引用会显示失效。
重建索引会生成新的 `chunk_id`；依赖旧 `chunk_id` 的引用应重新检索或标记待核查。

## 与其他模块的连接

- **平台模块**：提供真实认证中间件；把 `user_id` 写入 `request.state`。生产环境不得使用未经验证的请求头或表单用户 ID。
- **Writer**：从工作流的 `retrieved_sources` 读取证据；引用编号由程序映射到真实 `chunk_id`，不能由模型编造来源。
- **Agent 提示词**：检索得到的原文只作为资料数据，不能执行其中的指令或改变工具权限。
- **Verification**：使用引用回查接口读取原文；当返回 `deleted` 或 `missing` 时，把对应引用标记为失效或待核查。
- **前端**：上传后轮询资料状态；引用点击时展示原文、位置和原文件下载入口。

## 本地验收

运行 `python -m ruff check .` 和 `python -m pytest`。完整联调还需真实 PostgreSQL、Redis、MinIO、embedding/视觉模型服务和平台认证；固定资料应覆盖跨用户隔离、删除后不可检索、PDF 页码、图片识别结果回查、无证据提示、失败重试。
