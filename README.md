# CreatorMind

CreatorMind 是面向科技、教育、科普类知识创作者的**个性化可信多智能体创作平台**。系统基于用户授权的历史作品与知识素材，协助完成资料检索、图文写作、事实核查和编辑优化，并确保最终内容由用户审核。

当前仓库是 **v0.1 工程骨架**，重点完成前后端基础架构、开发环境和后续功能扩展边界。

## 当前能力

- Vue 3 + TypeScript 前端应用外壳
- 创作工作台、作品与素材库、多 Agent 创作、多对话、个性化记忆、系统设置六个业务页面及独立登录页
- Tiptap 富文本编辑器
- 路由、Pinia 状态管理与后端健康检查
- FastAPI 应用、配置管理、CORS 与版本化 API
- PostgreSQL / Redis 就绪检查
- Celery Worker 与 LangGraph 三阶段流程占位
- Alembic 数据库迁移与 pgvector 扩展
- Docker Compose 本地基础设施，以及可选的完整容器开发环境
- 素材库支持导入 PDF、Markdown 和 TXT，原文件保存在 MinIO，来源和文件信息保存在 PostgreSQL

- 本机单账号认证：登录、退出、修改密码、本机初始化与重置
- 会话与消息持久化，素材和会话均按用户隔离

> 首期支持本机单账号使用。RAG、聊天生成和任务持久化仍待接入。

## 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Tailwind CSS、Tiptap |
| 后端 | Python 3.12+、FastAPI、Pydantic v2、SQLAlchemy 2、Alembic |
| 数据 | PostgreSQL 16、pgvector、Redis |
| 异步与 Agent | Celery、LangGraph、OpenAI-compatible 模型接口 |
| 存储 | S3 兼容对象存储（开发环境使用 MinIO） |
| 工程 | Docker Compose、pytest、Vitest、Ruff |

## 目录结构

```text
CreatorMind/
├─ backend/
│  ├─ app/
│  │  ├─ agents/       # LangGraph 状态与工作流
│  │  ├─ api/          # FastAPI 路由
│  │  ├─ core/         # 配置等跨模块能力
│  │  ├─ db/           # SQLAlchemy 会话与 Base
│  │  ├─ models/       # ORM 模型（待扩展）
│  │  ├─ schemas/      # Pydantic Schema
│  │  └─ workers/      # Celery 应用与任务
│  ├─ alembic/         # 数据库迁移
│  └─ tests/
├─ frontend/
│  ├─ src/
│  │  ├─ api/          # 前端 API 客户端
│  │  ├─ components/   # 公共组件
│  │  ├─ layouts/      # 应用布局
│  │  ├─ router/       # Vue Router
│  │  ├─ stores/       # Pinia
│  │  └─ views/        # 页面
│  └─ ...
├─ docs/
│  └─ architecture.md
├─ scripts/
├─ compose.yaml
└─ .env.example
```

## 快速启动

当前推荐采用**Docker 运行基础设施、前后端在本机运行**的方式。这样既能保持 PostgreSQL、Redis、MinIO 环境一致，也能保留前后端热更新效率。

### 1. 启动基础设施

需要 Docker Desktop：

```powershell
Copy-Item .env.example .env
docker compose up -d
```

该命令默认只启动：

- PostgreSQL + pgvector：`localhost:5433`
- Redis：`localhost:6382`
- MinIO API：`localhost:19000`
- MinIO Console：`localhost:19001`

### 2. 启动后端

```powershell
.\scripts\setup.ps1
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli.auth init-user --username creator
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --no-proxy-headers
```

初始化命令通过隐藏输入读取并确认密码，不接受明文密码参数；已有账号时拒绝再次初始化。用户名为 3–32 位 ASCII 字母、数字、下划线或连字符，密码为 15–128 个字符。

`setup.ps1` 保留已有配置，在 `backend/.env` 缺少认证密钥时生成随机密钥，不显示其内容；该文件不能提交或复制到前端。迁移若发现旧版无所有者会话会明确拒绝，不自动清空或认领数据。

忘记密码时，在 `backend` 目录通过本机维护命令重置，重置会撤销全部登录：

```powershell
.\.venv\Scripts\python.exe -m app.cli.auth reset-password --username creator
```

登录使用服务端 8 小时绝对有效期会话，退出当前会话，改密后其他登录失效。浏览器统一访问 `http://localhost:5173`；不要混用 `127.0.0.1` 期待共享 Cookie。首期草稿仅在内存中，同账号认证过期后可恢复，主动退出清空，刷新或关闭页面后不恢复。

### 3. 启动前端

在新终端中执行：

```powershell
Set-Location frontend
npm install
npm run dev
```

访问：

- 前端：<http://localhost:5173>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health>
- 就绪检查：<http://localhost:8000/api/v1/health/ready>
- MinIO Console：<http://localhost:19001>

停止基础设施：

```powershell
docker compose down
```

### 可选：完整 Docker 环境

前后端和 Celery Worker 已放入 `full` profile，只在明确需要容器化联调或部署预演时启用。先执行 `setup.ps1` 准备 `backend/.env` 中的认证密钥；此模式仍然只向本机发布端口，不是生产模板：

```powershell
docker compose --profile full up --build
```

新数据库首次启动后，在另一个终端创建唯一账号（已初始化则不重复执行）：

```powershell
docker compose --profile full exec backend python -m app.cli.auth init-user --username creator
```

该方式会同时以容器运行前端、后端和 Worker。停止全部服务：

```powershell
docker compose --profile full down
```

也可以执行初始化脚本安装本地依赖：

```powershell
.\scripts\setup.ps1
```
## 质量检查

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest

Set-Location ..\frontend
npm run typecheck
npm test
npm run build
```

或执行：

```powershell
.\scripts\check.ps1
```

认证集成测试需要显式设置 `CREATORMIND_TEST_DATABASE_URL`（`postgresql+asyncpg://`）与 `CREATORMIND_TEST_REDIS_URL`，不从实际业务配置隐式取地址。测试只在随机隔离 schema 和专用 Redis 键中读写并清理自己的资源；未配置时会明确跳过相关集成项，不等于集成验收通过。应使用授权的测试实例，数据库账号需具备创建 schema 权限。

## 环境变量

根目录 `.env` 用于 Docker Compose；`backend/.env` 用于本地运行 FastAPI。后端的应用配置统一使用 `CREATORMIND_` 前缀，避免与系统环境变量冲突。

关键配置包括：

- `CREATORMIND_DATABASE_URL`
- `CREATORMIND_AUTH_SECRET_KEY`（必须为随机服务端密钥，无默认值）
- `CREATORMIND_AUTH_TRUSTED_ORIGINS`（与 CORS 来源一致）
- `CREATORMIND_AUTH_TRUSTED_HOSTS`
- `CREATORMIND_AUTH_SESSION_TTL_SECONDS`
- `CREATORMIND_REDIS_URL`
- `CREATORMIND_CELERY_BROKER_URL`
- `CREATORMIND_CELERY_RESULT_BACKEND`
- `CREATORMIND_S3_ENDPOINT_URL`
- `CREATORMIND_LLM_BASE_URL`
- `CREATORMIND_LLM_MODEL`
- `CREATORMIND_LLM_API_KEY`

## 下一阶段

1. 公网认证与运行安全演进（当前仅本机单账号闭环）
2. 素材上传、解析、切片和向量索引
3. 创建任务 API 与 Celery 异步执行
4. 接入真实 LLM、检索与引用定位
5. 事实主张结构化、证据关联与冲突提示
6. 草稿版本、审核反馈和导出
7. 个性化记忆的确认、编辑与删除流程

更多设计说明见 [docs/architecture.md](docs/architecture.md)。
