# CreatorMind

CreatorMind 是面向科技、教育、科普类知识创作者的**个性化可信多智能体创作平台**。系统基于用户授权的历史作品与知识素材，协助完成资料检索、图文写作、事实核查和编辑优化，并确保最终内容由用户审核。

当前仓库是 **v0.1 工程骨架**，重点完成前后端基础架构、开发环境和后续功能扩展边界。

## 当前能力

- Vue 3 + TypeScript 前端应用外壳
- 创作工作台、作品与素材库、多 Agent 创作、个性化记忆、系统设置五个页面
- Tiptap 富文本编辑器
- 路由、Pinia 状态管理与后端健康检查
- FastAPI 应用、配置管理、CORS 与版本化 API
- PostgreSQL / Redis 就绪检查
- Celery Worker 与 LangGraph 三阶段流程占位
- Alembic 数据库迁移与 pgvector 扩展
- Docker Compose 本地基础设施，以及可选的完整容器开发环境

> 当前版本尚未实现登录、文件上传、RAG、真实模型调用和内容持久化。

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
py -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install --upgrade pip
.\backend\.venv\Scripts\python.exe -m pip install -e ".\backend[dev,agent]"
Copy-Item backend/.env.example backend/.env
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

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

前后端和 Celery Worker 已放入 `full` profile，只在明确需要容器化联调或部署预演时启用：

```powershell
docker compose --profile full up --build
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

## 环境变量

根目录 `.env` 用于 Docker Compose；`backend/.env` 用于本地运行 FastAPI。后端的应用配置统一使用 `CREATORMIND_` 前缀，避免与系统环境变量冲突。

关键配置包括：

- `CREATORMIND_DATABASE_URL`
- `CREATORMIND_REDIS_URL`
- `CREATORMIND_CELERY_BROKER_URL`
- `CREATORMIND_CELERY_RESULT_BACKEND`
- `CREATORMIND_S3_ENDPOINT_URL`
- `CREATORMIND_LLM_BASE_URL`
- `CREATORMIND_LLM_MODEL`
- `CREATORMIND_LLM_API_KEY`

## 下一阶段

1. 用户认证与权限隔离
2. 素材上传、解析、切片和向量索引
3. 创建任务 API 与 Celery 异步执行
4. 接入真实 LLM、检索与引用定位
5. 事实主张结构化、证据关联与冲突提示
6. 草稿版本、审核反馈和导出
7. 个性化记忆的确认、编辑与删除流程

更多设计说明见 [docs/architecture.md](docs/architecture.md)。