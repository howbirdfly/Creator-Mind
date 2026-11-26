# CreatorMind API

CreatorMind 的 FastAPI 后端。开发与启动方式见仓库根目录 `README.md`。

## 素材库与 RAG 联调

启动 PostgreSQL 和 MinIO，安装新的后端依赖并执行 `alembic upgrade head`。按根目录 README 初始化本机账号后登录。素材接口按当前用户查询和写入，上传需要 CSRF 令牌。开发模式下第一次上传会在需要时创建配置的素材桶。

如果本地无法拉取项目的 MinIO 镜像，可以先用 `docker compose up -d postgres redis` 启动数据库和 Redis，再在 `backend/.env` 中配置可访问的 S3 兼容服务。连接配置为 `CREATORMIND_S3_ENDPOINT_URL`、`CREATORMIND_S3_ACCESS_KEY`、`CREATORMIND_S3_SECRET_KEY` 和 `CREATORMIND_S3_BUCKET`。

| 接口 | 用途 |
| --- | --- |
| `POST /api/v1/sources` | 用 `multipart/form-data` 上传 `file`，可选 `source_url`，成功返回 201。 |
| `GET /api/v1/sources` | 按导入时间倒序分页，支持 `limit` 和 `offset`。 |
| `GET /api/v1/sources/count` | 返回素材总数 `{"total": N}`，供首页统计使用。 |
| `GET /api/v1/sources/{asset_id}` | 查询素材元数据。上传响应里的 `id` 就是 `asset_id`。 |

支持 PDF、Markdown 和 TXT，单文件上限为 20 MiB。可在 `/docs` 或前端「作品与素材库」验证上传。

RAG 后台可调用 `await read_source_file(db, asset_id, user_id=user_id)`，函数位于 `app.services.source_storage`，返回 `(素材记录, 原文件字节)`。任务应保存从认证会话得到的用户 ID。素材不存在或不归该用户时返回 `None`。

### 从认证合入前的素材库草稿升级

旧素材库草稿与认证迁移曾使用相同的编号 `20261122_0003`。如果数据库在该编号且有 `sources` 表但没有 `users` 表，先备份数据库和对象存储，将旧素材表移到独立备份 schema，再用 `alembic stamp 20261120_0002` 恢复迁移起点并执行 `alembic upgrade head`。初始化账号后，按明确的归属复制要保留的旧素材记录，保留原 ID 和对象键，并填入对应的 `user_id`。已有对话时，认证迁移会要求先处理对话归属。已应用团队认证迁移的数据库直接运行 `alembic upgrade head`。
