import asyncio
import hashlib
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.source import Source, SourceChunk
from app.retrieval.embedding import EmbeddingClient
from app.retrieval.image import VisionClient, image_index_text
from app.retrieval.parser import TextChunk, TextPage, parse_source, split_pages
from app.retrieval.storage import get_source_storage
from app.schemas.source import CitationResponse, EvidenceItem, SearchRequest, SearchResponse


async def index_source(source_id: UUID, db: AsyncSession) -> None:
    source = await db.scalar(select(Source).where(Source.id == source_id).with_for_update())
    if source is None or source.status != "pending":
        return
    source.status = "processing"
    source.error = None
    await db.commit()

    try:
        if source.object_key is None:
            raise ValueError("原始文件不存在")
        data = await asyncio.to_thread(get_source_storage().get, source.object_key)
        if len(data) > settings.source_max_bytes:
            raise ValueError("文件超过大小限制")
        if hashlib.sha256(data).hexdigest() != source.sha256:
            raise ValueError("原始文件校验失败")
        image_source = source.content_type.startswith("image/")
        if image_source:
            analysis = await VisionClient().analyze(data, source.content_type)
            pages = [TextPage(image_index_text(analysis))]
        else:
            pages = parse_source(data, source.filename)
        if sum(len(page.text) for page in pages) > settings.source_max_chars:
            raise ValueError("提取文字超过处理上限")
        chunks = split_pages(pages)
        if not chunks:
            raise ValueError("未生成可检索的文本片段")
        if len(chunks) > settings.source_max_chunks:
            raise ValueError("切片数量超过处理上限")
        vectors = await EmbeddingClient().embed(
            [embedding_text(source.title, chunk) for chunk in chunks]
        )
        source = await db.scalar(
            select(Source)
            .where(Source.id == source_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if source is None or source.status != "processing":
            await db.rollback()
            return
        await db.execute(delete(SourceChunk).where(SourceChunk.source_id == source_id))
        for ordinal, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            db.add(
                SourceChunk(
                    id=uuid4(),
                    source_id=source_id,
                    user_id=source.user_id,
                    ordinal=ordinal,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    context_before=chunk.context_before,
                    context_after=chunk.context_after,
                    origin="image_analysis" if image_source else "document",
                    extraction_model=settings.vision_model if image_source else None,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    source_version=source.version,
                    embedding_model=settings.embedding_model,
                    embedding=vector,
                )
            )
        source.status = "ready"
        await db.commit()
    except Exception as exc:
        await db.rollback()
        source = await db.scalar(
            select(Source).where(Source.id == source_id).execution_options(populate_existing=True)
        )
        if source is not None and source.status == "processing":
            source.status = "failed"
            source.error = str(exc)[:500] if isinstance(exc, ValueError) else type(exc).__name__
            await db.commit()
        raise


def embedding_text(title: str, chunk: TextChunk) -> str:
    """Give the index local context while keeping the cited excerpt unchanged."""
    parts = [f"资料标题：{title}"]
    if chunk.section:
        parts.append(f"章节：{chunk.section}")
    if chunk.page_number:
        parts.append(f"页码：{chunk.page_number}")
    if chunk.context_before:
        parts.append(f"前文：{chunk.context_before[-120:]}")
    parts.append(f"正文：{chunk.content}")
    if chunk.context_after:
        parts.append(f"后文：{chunk.context_after[:120]}")
    return "\n".join(parts)


async def search_sources(
    db: AsyncSession,
    user_id: str,
    request: SearchRequest,
    embedding_client: EmbeddingClient | None = None,
) -> SearchResponse:
    source_filters = [
        Source.user_id == user_id,
        Source.kind == request.kind,
        Source.status == "ready",
    ]
    if request.source_ids is not None:
        if not request.source_ids:
            return SearchResponse(evidence=[], gap="指定的资料范围为空")
        source_filters.append(Source.id.in_(request.source_ids))
    available = await db.scalar(select(Source.id).where(*source_filters).limit(1))
    if available is None:
        return SearchResponse(evidence=[], gap="当前范围没有已建立索引的授权资料")

    if request.mode == "keyword":
        escaped = request.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = (
            select(SourceChunk, Source.title)
            .join(Source, Source.id == SourceChunk.source_id)
            .where(
                *source_filters,
                SourceChunk.user_id == user_id,
                or_(
                    SourceChunk.content.ilike(pattern, escape="\\"),
                    Source.title.ilike(pattern, escape="\\"),
                ),
            )
            .order_by(Source.created_at.desc(), SourceChunk.ordinal)
            .limit(request.limit)
        )
        rows = [(chunk, title, 0.0) for chunk, title in (await db.execute(statement)).all()]
    else:
        client = embedding_client or EmbeddingClient()
        query_text = request.query
        if request.context:
            query_text = f"任务背景：{request.context}\n当前检索问题：{request.query}"
        query_vector = (await client.embed([query_text]))[0]
        distance = SourceChunk.embedding.cosine_distance(query_vector)
        statement = (
            select(SourceChunk, Source.title, distance.label("distance"))
            .join(Source, Source.id == SourceChunk.source_id)
            .where(
                *source_filters,
                SourceChunk.user_id == user_id,
                SourceChunk.embedding_model == settings.embedding_model,
            )
            .order_by(distance)
            .limit(max(20, request.limit * 4))
        )
        rows = (await db.execute(statement)).all()
    evidence: list[EvidenceItem] = []
    for chunk, title, cosine_distance in rows:
        similarity = max(-1.0, min(1.0, 1.0 - float(cosine_distance)))
        if request.mode == "semantic" and similarity < settings.retrieval_min_similarity:
            continue
        if any(_mostly_overlaps(item, chunk) for item in evidence):
            continue
        evidence.append(
            EvidenceItem(
                evidence_id=f"E{len(evidence) + 1}",
                source_id=chunk.source_id,
                chunk_id=chunk.id,
                source_version=chunk.source_version,
                source_kind=request.kind,
                title=title,
                excerpt=chunk.content,
                page_number=chunk.page_number,
                section=chunk.section,
                context_before=chunk.context_before,
                context_after=chunk.context_after,
                origin=chunk.origin,
                extraction_model=chunk.extraction_model,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                similarity=round(similarity, 4),
                method=request.mode,
            )
        )
        if len(evidence) >= request.limit:
            break
    return SearchResponse(
        evidence=evidence,
        gap=None if evidence else "没有找到足够相关的授权资料，请补充资料或调整检索问题",
    )


def _mostly_overlaps(item: EvidenceItem, chunk: SourceChunk) -> bool:
    if item.source_id != chunk.source_id or item.page_number != chunk.page_number:
        return False
    overlap = max(
        0, min(item.end_offset, chunk.end_offset) - max(item.start_offset, chunk.start_offset)
    )
    shorter = min(item.end_offset - item.start_offset, chunk.end_offset - chunk.start_offset)
    return overlap > 0 and overlap * 2 >= shorter


async def resolve_citation(
    db: AsyncSession, user_id: str, source_id: UUID, chunk_id: UUID
) -> CitationResponse | None:
    source = await db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == user_id)
    )
    if source is None:
        return None
    if source.status == "deleted":
        return CitationResponse(
            source_id=source_id,
            chunk_id=chunk_id,
            status="deleted",
            title=source.title,
            source_version=source.version,
        )
    chunk = await db.scalar(
        select(SourceChunk).where(
            SourceChunk.id == chunk_id,
            SourceChunk.source_id == source_id,
            SourceChunk.user_id == user_id,
        )
    )
    if chunk is None or source.status != "ready":
        return CitationResponse(
            source_id=source_id,
            chunk_id=chunk_id,
            status="missing",
            title=source.title,
            source_version=source.version,
        )
    return CitationResponse(
        source_id=source_id,
        chunk_id=chunk_id,
        status="valid",
        title=source.title,
        source_version=chunk.source_version,
        excerpt=chunk.content,
        page_number=chunk.page_number,
        section=chunk.section,
        context_before=chunk.context_before,
        context_after=chunk.context_after,
        origin=chunk.origin,
        extraction_model=chunk.extraction_model,
        start_offset=chunk.start_offset,
        end_offset=chunk.end_offset,
    )


async def delete_source(db: AsyncSession, user_id: str, source_id: UUID) -> bool:
    source = await db.scalar(
        select(Source).where(Source.id == source_id, Source.user_id == user_id).with_for_update()
    )
    if source is None:
        return False
    if source.status == "deleted":
        return True
    source.status = "deleting"
    await db.commit()
    if source.object_key:
        await asyncio.to_thread(get_source_storage().delete, source.object_key)
    await db.execute(delete(SourceChunk).where(SourceChunk.source_id == source_id))
    source.object_key = None
    source.status = "deleted"
    source.error = None
    await db.commit()
    return True
