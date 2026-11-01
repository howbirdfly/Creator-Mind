# CreatorMind 架构说明（v0.1）

## 1. 架构目标

CreatorMind 的核心不是单次文本生成，而是一条可追踪、可审核、可复现的知识创作流水线：

```text
授权素材 → 检索 → 写作 → 事实核查 → 人工审核 → 反馈与记忆更新
```

架构设计围绕以下原则：

- **用户控制**：内容、记忆和授权数据均可查看、修改和删除。
- **证据优先**：关键主张应关联来源、定位信息和核查结论。
- **流程可替换**：模型、检索器和 Agent 节点均应可替换。
- **成本可控**：通过异步任务、上下文裁剪和预算限制控制 Token 消耗。
- **渐进式复杂化**：先跑通三阶段闭环，再引入 Supervisor 和更多 Agent。

## 2. 系统分层

```text
Vue 3 Web
    │ REST / SSE
FastAPI API
    ├─ PostgreSQL + pgvector
    ├─ Redis + Celery
    ├─ S3 / MinIO
    └─ LangGraph Agent Runtime
             └─ LLM Provider
```

### 前端

- Vue 3 + TypeScript + Vite
- Vue Router 管理页面
- Pinia 管理用户、任务和会话状态
- Tiptap 承担富文本编辑与引用标记
- 后续通过 SSE 或 WebSocket 展示 Agent 流式进度

### 后端

- FastAPI 提供版本化 REST API
- Pydantic 负责请求、响应和 Agent 状态校验
- SQLAlchemy 2 异步访问 PostgreSQL
- Alembic 管理数据库结构
- Celery 执行文档解析、向量化和长耗时创作任务
- LangGraph 描述 Agent 状态、路由和重试

## 3. 建议模块边界

```text
backend/app/
├─ api/          # 路由与依赖注入
├─ core/         # 配置、安全、日志、异常
├─ db/           # 数据库连接与 Base
├─ models/       # 持久化实体
├─ schemas/      # API 与内部数据契约
├─ repositories/ # 数据访问
├─ services/     # 业务用例
├─ agents/       # Agent 节点、状态与图
├─ retrieval/    # 切片、Embedding、混合检索
├─ storage/      # S3 适配
└─ workers/      # Celery 任务
```

路由层只处理参数、权限和响应；复杂业务放在 service；数据访问集中在 repository，避免 Agent 直接操作数据库。

## 4. 计划中的数据模型

| 实体 | 主要职责 |
|---|---|
| User | 用户身份与配置 |
| Work | 创作者导入的历史作品 |
| Source | 用户授权的参考资料 |
| SourceChunk | 文本切片、向量、页码与定位 |
| Memory | 用户偏好、创作经验及来源 |
| CreationTask | 一次创作任务及执行状态 |
| DraftVersion | 草稿内容与版本历史 |
| Claim | 从草稿中提取的事实主张 |
| Evidence | 主张与来源片段的关联 |
| Feedback | 用户确认、修改与拒绝记录 |

所有用户数据表应包含 `user_id` 和必要的审计字段。向量字段使用 pgvector，检索时可结合 PostgreSQL 全文检索、BM25 与 Reranker。

## 5. Agent 工作流

当前骨架实现：

```text
START → Research → Writer → Verification → END
```

后续目标：

```text
Supervisor
  ├─ Research Agent
  ├─ Memory Agent
  ├─ Writer Agent
  ├─ Verification Agent
  └─ Editor Agent
```

约束：

- Memory Agent 只能读取用户授权且未删除的记忆。
- Verification Agent 输出结构化结论，不能只返回自然语言“已核查”。
- Editor Agent 的修改需保留变更说明。
- Supervisor 设置最大重试次数、超时与 Token 预算。
- 任何 Agent 都不能绕过人工审核直接发布。

## 6. API 设计原则

- API 前缀：`/api/v1`
- 资源命名使用复数：`/works`、`/sources`、`/creations`
- 长任务创建接口立即返回 `task_id`，通过轮询或 SSE 获取状态
- 所有错误使用统一结构：`code`、`message`、`details`
- 用户反馈和记忆更新必须记录来源与确认状态

建议的下一批接口：

```text
POST   /api/v1/sources
GET    /api/v1/sources
POST   /api/v1/creations
GET    /api/v1/creations/{task_id}
POST   /api/v1/creations/{task_id}/feedback
GET    /api/v1/memories
PATCH  /api/v1/memories/{memory_id}
DELETE /api/v1/memories/{memory_id}
```

## 7. 安全与隐私

- 认证后所有资源强制执行用户级权限校验。
- 对象存储使用短期签名 URL，不直接暴露凭证。
- 上传文件限制类型、大小和解析超时。
- 日志中避免记录原始私密内容和模型密钥。
- 支持删除素材、向量、记忆与相关衍生数据。
- 模型调用前明确数据发送范围，并提供成本上限。

## 8. 验证策略

- `pytest`：配置、API、业务服务和 Agent 节点单元测试
- 集成测试：PostgreSQL、Redis、对象存储与迁移
- `Vitest`：前端状态与组件逻辑
- Playwright：导入、创作、核查、反馈和导出主链路
- 实验指标：事实错误率、证据支持率、偏好评分、人工修改时间、任务成功率和 Token 成本

## 9. 里程碑

### M1：工程骨架（当前）

前后端可启动，基础设施可编排，健康检查可用。

### M2：素材与创作闭环

认证、上传、解析、索引、三阶段流程、草稿保存和人工审核。

### M3：可信验证

结构化主张、证据定位、冲突检测、引用覆盖率和核查报告。

### M4：个性化记忆

显式偏好、确认反馈归纳、可解释记忆和删除审计。

### M5：实验与评测

可复现实验配置、对照方案、自动指标和成本统计。