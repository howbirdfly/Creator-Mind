from app.workers.celery_app import celery_app


@celery_app.task(name="system.ping")
def ping() -> dict[str, str]:
    """Small smoke-test task for validating the worker and broker."""
    return {"status": "ok"}