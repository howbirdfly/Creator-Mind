import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.retrieval.service import index_source
from app.workers.celery_app import celery_app


@celery_app.task(name="system.ping")
def ping() -> dict[str, str]:
    """Small smoke-test task for validating the worker and broker."""
    return {"status": "ok"}


@celery_app.task(name="sources.index", soft_time_limit=300)
def index_source_task(source_id: str) -> None:
    async def run() -> None:
        # Celery calls asyncio.run per task, so connections must not survive its event loop.
        engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as db:
                await index_source(UUID(source_id), db)
        finally:
            await engine.dispose()

    asyncio.run(run())
