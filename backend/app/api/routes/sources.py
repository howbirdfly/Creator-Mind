import logging
from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID, uuid4

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from pydantic import HttpUrl
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.deps import CsrfProtected, CurrentIdentity, DbSession
from app.models.source import Source
from app.schemas.source import SourceCount, SourceOut
from app.services.source_storage import discard_source_object, get_owned_source, put_source_object

logger = logging.getLogger(__name__)
MAX_SOURCE_BYTES = 20 * 1024 * 1024
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


router = APIRouter(prefix="/sources", tags=["sources"])


@router.post(
    "", response_model=SourceOut, status_code=status.HTTP_201_CREATED, dependencies=[CsrfProtected]
)
async def upload_source(
    db: DbSession,
    identity: CurrentIdentity,
    file: Annotated[UploadFile, File()],
    source_url: Annotated[HttpUrl | None, Form()] = None,
) -> Source:
    original_name = (file.filename or "").replace("\\", "/")
    filename = PurePosixPath(original_name).name.strip()
    if not filename or len(filename) > 255 or any(ord(char) < 32 for char in filename):
        raise HTTPException(status_code=422, detail="文件名无效")

    suffix = PurePosixPath(filename).suffix.lower()
    content_type = CONTENT_TYPES.get(suffix)
    if content_type is None:
        raise HTTPException(status_code=415, detail="支持 PDF、Markdown 和 TXT 文件")
    if not file.size:
        raise HTTPException(status_code=422, detail="文件不能为空")
    if file.size > MAX_SOURCE_BYTES:
        raise HTTPException(status_code=413, detail="文件大小不能超过 20 MiB")
    if suffix == ".pdf":
        if await file.read(5) != b"%PDF-":
            raise HTTPException(status_code=415, detail="文件不是有效的 PDF")
        await file.seek(0)

    asset_id = uuid4()
    source = Source(
        id=asset_id,
        user_id=identity.user.id,
        filename=filename,
        content_type=content_type,
        size_bytes=file.size,
        source_url=str(source_url) if source_url is not None else None,
        object_key=f"sources/{asset_id}{suffix}",
    )
    object_key = source.object_key
    db.add(source)
    try:
        await db.flush()
    except SQLAlchemyError:
        logger.exception("Could not stage source metadata %s", asset_id)
        raise HTTPException(status_code=503, detail="素材数据库暂不可用") from None

    try:
        await run_in_threadpool(put_source_object, source, file.file)
    except (BotoCoreError, ClientError):
        logger.exception("Could not store source object %s", asset_id)
        await run_in_threadpool(discard_source_object, object_key)
        raise HTTPException(status_code=503, detail="文件存储暂不可用，素材上传失败") from None

    try:
        await db.commit()
    except IntegrityError:
        await run_in_threadpool(discard_source_object, object_key)
        logger.exception("Source metadata was rejected for %s", asset_id)
        raise HTTPException(status_code=503, detail="素材记录保存失败") from None
    except SQLAlchemyError:
        # A lost commit acknowledgment may still mean the row was committed.
        logger.exception("Could not confirm metadata commit for source %s", asset_id)
        raise HTTPException(
            status_code=503, detail="素材记录保存结果未确认，请先刷新列表"
        ) from None

    return source


@router.get("", response_model=list[SourceOut])
async def list_sources(
    db: DbSession,
    identity: CurrentIdentity,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Source]:
    result = await db.scalars(
        select(Source)
        .where(Source.user_id == identity.user.id)
        .order_by(Source.created_at.desc(), Source.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.all())


@router.get("/count", response_model=SourceCount)
async def count_sources(db: DbSession, identity: CurrentIdentity) -> SourceCount:
    total = await db.scalar(
        select(func.count()).select_from(Source).where(Source.user_id == identity.user.id)
    )
    return SourceCount(total=total or 0)


@router.get("/{asset_id}", response_model=SourceOut)
async def get_source(asset_id: UUID, db: DbSession, identity: CurrentIdentity) -> Source:
    source = await get_owned_source(db, asset_id, user_id=identity.user.id)
    if source is None:
        raise HTTPException(status_code=404, detail="素材不存在")
    return source
