"""Private object storage for original source files."""

import logging
from contextlib import closing
from functools import lru_cache
from typing import BinaryIO
from uuid import UUID

from boto3.session import Session
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.models.source import Source

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _s3():
    return Session().client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
        config=Config(
            s3={"addressing_style": "path"},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
            connect_timeout=3,
            read_timeout=15,
            retries={"mode": "standard", "total_max_attempts": 2},
        ),
    )


def put_source_object(source: Source, file: BinaryIO) -> None:
    client = _s3()
    params = {
        "Bucket": settings.s3_bucket,
        "Key": source.object_key,
        "Body": file,
        "ContentLength": source.size_bytes,
        "ContentType": source.content_type,
    }
    try:
        client.put_object(**params)
    except ClientError as exc:
        if settings.environment != "development" or exc.response["Error"]["Code"] != "NoSuchBucket":
            raise
        try:
            client.create_bucket(Bucket=settings.s3_bucket)
        except ClientError as bucket_error:
            if bucket_error.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                raise
        file.seek(0)
        client.put_object(**params)


def discard_source_object(object_key: str) -> None:
    """Best-effort compensation when the metadata is known to be uncommitted."""
    try:
        _s3().delete_object(Bucket=settings.s3_bucket, Key=object_key)
    except (BotoCoreError, ClientError):
        logger.exception("Could not clean up source object %s", object_key)


def _read_object(object_key: str) -> bytes:
    response = _s3().get_object(Bucket=settings.s3_bucket, Key=object_key)
    with closing(response["Body"]) as body:
        return body.read()


async def get_owned_source(db: AsyncSession, asset_id: UUID, *, user_id: UUID) -> Source | None:
    return await db.scalar(select(Source).where(Source.id == asset_id, Source.user_id == user_id))


async def read_source_file(
    db: AsyncSession, asset_id: UUID, *, user_id: UUID
) -> tuple[Source, bytes] | None:
    """Read an original scoped to the user who scheduled the backend job."""
    source = await get_owned_source(db, asset_id, user_id=user_id)
    if source is None:
        return None
    return source, await run_in_threadpool(_read_object, source.object_key)
