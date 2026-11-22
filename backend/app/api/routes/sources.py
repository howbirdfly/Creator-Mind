import asyncio
import hashlib
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_id
from app.core.config import settings
from app.db.session import get_db
from app.models.source import Source
from app.retrieval.image import prepare_image
from app.retrieval.parser import content_type_for
from app.retrieval.service import delete_source, resolve_citation, search_sources
from app.retrieval.storage import get_source_storage
from app.schemas.source import (
    CitationResponse,
    SearchRequest,
    SearchResponse,
    SourceKind,
    SourceResponse,
)
from app.workers.tasks import index_source_task

router = APIRouter(prefix="/sources", tags=["sources"])
Db = Annotated[AsyncSession, Depends(get_db)]
UserId = Annotated[str, Depends(get_current_user_id)]


def enqueue_index(source: Source) -> None:
    try:
        index_source_task.delay(str(source.id))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="索引队列暂不可用，请稍后重试") from exc


@router.post("", response_model=SourceResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_source(
    db: Db,
    user_id: UserId,
    file: Annotated[UploadFile, File()],
    kind: Annotated[SourceKind, Form()],
    title: Annotated[str | None, Form(max_length=255)] = None,
) -> Source:
    filename = Path((file.filename or "").replace("\\", "/")).name
    if len(filename) > 255:
        raise HTTPException(status_code=422, detail="文件名过长")
    try:
        content_type = content_type_for(filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    data = await file.read(settings.source_max_bytes + 1)
    await file.close()
    if not data:
        raise HTTPException(status_code=422, detail="文件为空")
    if len(data) > settings.source_max_bytes:
        raise HTTPException(status_code=413, detail="文件超过大小限制")
    if content_type.startswith("image/"):
        if not settings.vision_model:
            raise HTTPException(status_code=503, detail="图片索引需要配置视觉模型")
        try:
            await asyncio.to_thread(prepare_image, data, content_type)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    source_id = uuid4()
    object_key = f"sources/{source_id}"
    try:
        await asyncio.to_thread(get_source_storage().put, object_key, data, content_type)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="文件存储暂不可用") from exc
    source = Source(
        id=source_id,
        user_id=user_id,
        title=(title or filename).strip() or filename,
        filename=filename,
        content_type=content_type,
        kind=kind,
        status="pending",
        version=1,
        object_key=object_key,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )
    try:
        db.add(source)
        await db.commit()
    except Exception:
        await db.rollback()
        await asyncio.to_thread(get_source_storage().delete, object_key)
        raise
    await db.refresh(source)
    try:
        enqueue_index(source)
    except HTTPException:
        source.status = "failed"
        source.error = "索引队列暂不可用"
        await db.commit()
        raise
    return source


@router.get("", response_model=list[SourceResponse])
async def list_sources(db: Db, user_id: UserId) -> list[Source]:
    return list(
        (
            await db.scalars(
                select(Source)
                .where(Source.user_id == user_id, Source.status != "deleted")
                .order_by(Source.created_at.desc())
            )
        ).all()
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, db: Db, user_id: UserId) -> SearchResponse:
    try:
        return await search_sources(db, user_id, request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="检索服务暂不可用") from exc


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: UUID, db: Db, user_id: UserId) -> Source:
    source = await db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == user_id)
    )
    if source is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    return source


@router.get("/{source_id}/download")
async def download_source(source_id: UUID, db: Db, user_id: UserId) -> Response:
    source = await db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == user_id)
    )
    if source is None or source.object_key is None or source.status in ("deleting", "deleted"):
        raise HTTPException(status_code=404, detail="资料不存在")
    try:
        data = await asyncio.to_thread(get_source_storage().get, source.object_key)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="文件存储暂不可用") from exc
    return Response(
        content=data,
        media_type=source.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(source.filename)}"},
    )


@router.get("/{source_id}/citations/{chunk_id}", response_model=CitationResponse)
async def get_citation(
    source_id: UUID, chunk_id: UUID, db: Db, user_id: UserId
) -> CitationResponse:
    citation = await resolve_citation(db, user_id, source_id, chunk_id)
    if citation is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    return citation


@router.post("/{source_id}/retry", response_model=SourceResponse, status_code=202)
async def retry_source(source_id: UUID, db: Db, user_id: UserId) -> Source:
    source = await db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == user_id).with_for_update()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    if source.status != "failed":
        raise HTTPException(status_code=409, detail="只有索引失败的资料可以重试")
    return await queue_existing_source(db, source)


@router.post("/{source_id}/reindex", response_model=SourceResponse, status_code=202)
async def reindex_source(source_id: UUID, db: Db, user_id: UserId) -> Source:
    source = await db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == user_id).with_for_update()
    )
    if source is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    if source.status not in ("ready", "failed"):
        raise HTTPException(status_code=409, detail="当前状态不能重建索引")
    return await queue_existing_source(db, source)


async def queue_existing_source(db: AsyncSession, source: Source) -> Source:
    source.status = "pending"
    source.error = None
    await db.commit()
    try:
        enqueue_index(source)
    except HTTPException:
        source.status = "failed"
        source.error = "索引队列暂不可用"
        await db.commit()
        raise
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def remove_source(source_id: UUID, db: Db, user_id: UserId) -> None:
    try:
        removed = await delete_source(db, user_id, source_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="删除未完成，请重试") from exc
    if not removed:
        raise HTTPException(status_code=404, detail="资料不存在")
