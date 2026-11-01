import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe that does not depend on external services."""
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReadinessResponse:
    """Readiness probe for PostgreSQL and Redis."""
    checks: dict[str, str] = {}

    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=3)
        checks["postgres"] = "ok"
    except Exception as exc:  # pragma: no cover - depends on external services
        checks["postgres"] = f"error: {type(exc).__name__}"

    redis = Redis.from_url(settings.redis_url)
    try:
        await asyncio.wait_for(redis.ping(), timeout=3)
        checks["redis"] = "ok"
    except Exception as exc:  # pragma: no cover - depends on external services
        checks["redis"] = f"error: {type(exc).__name__}"
    finally:
        await redis.aclose()

    ready = all(value == "ok" for value in checks.values())
    response.status_code = 200 if ready else 503
    return ReadinessResponse(status="ready" if ready else "degraded", checks=checks)