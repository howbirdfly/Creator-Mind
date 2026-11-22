import hashlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.dialects import postgresql

from app.api.routes import sources
from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.models.source import Source
from app.retrieval import embedding as embedding_module
from app.retrieval import image as image_module
from app.retrieval import service
from app.retrieval import storage as storage_module
from app.retrieval.parser import TextPage, content_type_for, parse_source, split_pages
from app.retrieval.service import search_sources
from app.schemas.source import EvidenceItem, SearchRequest, SearchResponse


def test_parser_preserves_exact_locations() -> None:
    text = "# 第一节\n" + "资料能被准确定位。" * 160
    pages = parse_source(text.encode(), "reference.md")
    chunks = split_pages(pages, max_chars=100, overlap=20)

    assert len(chunks) > 1
    assert all(text[chunk.start_offset : chunk.end_offset] == chunk.content for chunk in chunks)
    assert all(chunk.page_number is None for chunk in chunks)
    assert any(chunk.section == "第一节" for chunk in chunks[1:])
    assert any(chunk.context_before for chunk in chunks[1:])
    assert chunks[0].context_before == ""


def test_parser_rejects_unreadable_or_unsupported_files() -> None:
    assert content_type_for("notes.TXT") == "text/plain"
    assert content_type_for("picture.png") == "image/png"
    with pytest.raises(ValueError, match="仅支持"):
        content_type_for("picture.svg")
    with pytest.raises(ValueError, match="视觉模型"):
        parse_source(b"not an image", "picture.png")
    with pytest.raises(ValueError, match="UTF-8"):
        parse_source(b"\xff", "bad.txt")
    with pytest.raises(ValueError, match="有效 PDF"):
        parse_source(b"not a pdf", "bad.pdf")
    with pytest.raises(ValueError, match="OCR"):
        parse_source(b" \n ", "empty.txt")


def test_pdf_page_numbers_survive_chunking() -> None:
    chunks = split_pages([TextPage("第一页内容。", 1), TextPage("第二页内容。", 2)])
    assert [chunk.page_number for chunk in chunks] == [1, 2]
    assert chunks[1].context_before == ""


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (12, 10), (255, 255, 255, 0)).save(output, format="PNG")
    return output.getvalue()


def test_image_validation_rejects_spoofing_and_converts_transparency() -> None:
    data = png_bytes()
    jpeg = image_module.prepare_image(data, "image/png")
    with Image.open(BytesIO(jpeg)) as image:
        assert image.format == "JPEG"
        assert image.getpixel((0, 0)) == (255, 255, 255)
    with pytest.raises(ValueError, match="不一致"):
        image_module.prepare_image(data, "image/jpeg")
    with pytest.raises(ValueError, match="解析失败"):
        image_module.prepare_image(b"broken", "image/png")


def test_image_pixel_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(image_module.settings, "image_max_pixels", 100)
    with pytest.raises(ValueError, match="像素超过"):
        image_module.prepare_image(png_bytes(), "image/png")


@pytest.mark.asyncio
async def test_vision_extracts_searchable_text_and_model_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(image_module.settings, "vision_model", "vision-test")
    sent = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, object]:
            content = '```json\n{"visible_text":"图中写着 RAG","description":"一张流程图"}\n```'
            return {"choices": [{"message": {"content": content}}]}

    class FakeHttpClient:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "FakeHttpClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, path: str, **kwargs: object) -> FakeResponse:
            sent["path"] = path
            sent["payload"] = kwargs["json"]
            return FakeResponse()

    monkeypatch.setattr(image_module.httpx, "AsyncClient", FakeHttpClient)
    result = await image_module.VisionClient().analyze(png_bytes(), "image/png")
    assert sent["path"] == "chat/completions"
    assert sent["payload"]["model"] == "vision-test"
    image_url = sent["payload"]["messages"][1]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/jpeg;base64,")
    assert (
        image_module.image_index_text(result)
        == "图片可见文字：\n图中写着 RAG\n\n图片画面描述：\n一张流程图"
    )


@pytest.mark.asyncio
async def test_image_upload_validates_before_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources.settings, "vision_model", "vision-test")
    stored = []
    queued = []

    class FakeStore:
        def put(self, key: str, data: bytes, content_type: str) -> None:
            stored.append((key, data, content_type))

    class FakeDb:
        source = None

        def add(self, source: Source) -> None:
            self.source = source

        async def commit(self) -> None:
            pass

        async def refresh(self, source: Source) -> None:
            pass

    monkeypatch.setattr(sources, "get_source_storage", lambda: FakeStore())
    monkeypatch.setattr(sources, "enqueue_index", lambda source: queued.append(source.id))
    db = FakeDb()
    data = png_bytes()
    result = await sources.upload_source(
        db, "user-a", UploadFile(file=BytesIO(data), filename="flow.png"), "fact"
    )
    assert result.content_type == "image/png"
    assert stored[0][1] == data
    assert queued == [result.id]
    with pytest.raises(HTTPException) as error:
        await sources.upload_source(
            db, "user-a", UploadFile(file=BytesIO(b"broken"), filename="fake.png"), "fact"
        )
    assert error.value.status_code == 422
    assert len(stored) == 1
    monkeypatch.setattr(sources.settings, "vision_model", "")
    with pytest.raises(HTTPException) as unavailable:
        await sources.upload_source(
            db, "user-a", UploadFile(file=BytesIO(data), filename="flow.png"), "fact"
        )
    assert unavailable.value.status_code == 503
    assert len(stored) == 1


def test_rag_api_requires_server_authenticated_identity() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/sources").status_code == 401
        assert client.post("/api/v1/sources/search", json={"query": "可信创作"}).status_code == 401


def test_search_api_uses_authenticated_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_db() -> object:
        yield object()

    async def fake_search(db: object, user_id: str, request: SearchRequest) -> SearchResponse:
        assert user_id == "user-a"
        assert request.query == "可信创作"
        return SearchResponse(evidence=[], gap="没有资料")

    monkeypatch.setattr(sources, "search_sources", fake_search)
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_user_id] = lambda: "user-a"
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/sources/search", json={"query": "可信创作"})
            forged = client.post(
                "/api/v1/sources/search", json={"query": "可信创作", "user_id": "user-b"}
            )
        assert response.status_code == 200
        assert response.json()["gap"] == "没有资料"
        assert forged.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_reports_gap_before_calling_embedding_when_no_sources() -> None:
    class EmptyDb:
        async def scalar(self, statement: object) -> None:
            return None

    class EmbeddingMustNotRun:
        async def embed(self, texts: list[str]) -> None:
            raise AssertionError("No embedding request expected")

    result = await search_sources(
        EmptyDb(), "user-a", SearchRequest(query="可信创作"), EmbeddingMustNotRun()
    )
    assert result.evidence == []
    assert result.gap is not None


@pytest.mark.asyncio
async def test_search_filters_user_and_returns_resolvable_evidence() -> None:
    source_id = uuid4()
    chunk_id = uuid4()
    chunk = SimpleNamespace(
        id=chunk_id,
        source_id=source_id,
        source_version=1,
        content="可追溯的原文",
        page_number=3,
        section=None,
        context_before="前文",
        context_after="后文",
        origin="document",
        extraction_model=None,
        start_offset=10,
        end_offset=18,
    )

    class Result:
        def all(self) -> list[tuple[object, str, float]]:
            return [(chunk, "参考资料", 0.2)]

    class FakeDb:
        query = None

        async def scalar(self, statement: object) -> object:
            return source_id

        async def execute(self, statement: object) -> Result:
            self.query = statement
            return Result()

    class FakeEmbedding:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["可信创作"]
            return [[0.1] * 768]

    db = FakeDb()
    result = await search_sources(db, "user-a", SearchRequest(query="可信创作"), FakeEmbedding())
    sql = str(db.query.compile(dialect=postgresql.dialect()))
    assert "sources.user_id" in sql and "source_chunks.user_id" in sql
    assert "sources.status" in sql and "sources.kind" in sql
    assert result.evidence[0].evidence_id == "E1"
    assert result.evidence[0].chunk_id == chunk_id
    assert result.evidence[0].page_number == 3
    assert result.evidence[0].method == "semantic"
    assert result.evidence[0].context_before == "前文"


@pytest.mark.asyncio
async def test_search_uses_task_context_for_embedding() -> None:
    inputs = []

    class FakeResult:
        def all(self) -> list[object]:
            return []

    class FakeDb:
        async def scalar(self, statement: object) -> object:
            return uuid4()

        async def execute(self, statement: object) -> FakeResult:
            return FakeResult()

    class FakeEmbedding:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            inputs.extend(texts)
            return [[0.1] * 768]

    await search_sources(
        FakeDb(),
        "user-a",
        SearchRequest(query="它有什么作用", context="主题是 RAG 证据链"),
        FakeEmbedding(),
    )
    assert inputs == ["任务背景：主题是 RAG 证据链\n当前检索问题：它有什么作用"]


def test_overlapping_results_are_deduplicated_without_crossing_pages() -> None:
    source_id = uuid4()
    item = EvidenceItem(
        evidence_id="E1",
        source_id=source_id,
        chunk_id=uuid4(),
        source_version=1,
        source_kind="fact",
        title="资料",
        excerpt="原文",
        page_number=1,
        section=None,
        start_offset=100,
        end_offset=200,
        similarity=0.8,
        method="semantic",
    )
    overlapping = SimpleNamespace(
        source_id=source_id, page_number=1, start_offset=150, end_offset=250
    )
    next_page = SimpleNamespace(
        source_id=source_id, page_number=2, start_offset=150, end_offset=250
    )
    assert service._mostly_overlaps(item, overlapping)
    assert not service._mostly_overlaps(item, next_page)


@pytest.mark.asyncio
async def test_keyword_search_escapes_wildcards_without_embedding() -> None:
    class EmptyResult:
        def all(self) -> list[object]:
            return []

    class FakeDb:
        query = None

        async def scalar(self, statement: object) -> object:
            return uuid4()

        async def execute(self, statement: object) -> EmptyResult:
            self.query = statement
            return EmptyResult()

    class EmbeddingMustNotRun:
        async def embed(self, texts: list[str]) -> None:
            raise AssertionError("Keyword search should not call embedding")

    db = FakeDb()
    result = await search_sources(
        db, "user-a", SearchRequest(query="A_100%", mode="keyword"), EmbeddingMustNotRun()
    )
    sql = db.query.compile(dialect=postgresql.dialect())
    assert "\\_" in str(sql.params) and "\\%" in str(sql.params)
    assert result.evidence == []



@pytest.mark.asyncio
async def test_indexing_creates_located_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    data = "# 标题\n资料内容。".encode()
    source_id = uuid4()
    source = Source(
        id=source_id,
        user_id="user-a",
        title="资料",
        filename="source.md",
        content_type="text/markdown",
        kind="fact",
        status="pending",
        version=1,
        object_key=f"sources/{source_id}",
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )
    db = SimpleNamespace(
        scalar=AsyncMock(side_effect=[source, source]),
        execute=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        add=Mock(),
    )

    class FakeStorage:
        def get(self, key: str) -> bytes:
            assert key == source.object_key
            return data

    class FakeEmbedding:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["资料标题：资料\n正文：# 标题\n资料内容。"]
            return [[0.1] * 768]

    monkeypatch.setattr(service, "get_source_storage", lambda: FakeStorage())
    monkeypatch.setattr(service, "EmbeddingClient", FakeEmbedding)
    await service.index_source(source_id, db)
    assert source.status == "ready"
    assert db.commit.await_count == 2
    indexed = db.add.call_args.args[0]
    assert indexed.user_id == "user-a"
    assert indexed.content == "# 标题\n资料内容。"
    assert indexed.start_offset == 0
    assert indexed.source_version == 1


@pytest.mark.asyncio
async def test_image_indexing_records_machine_derived_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = png_bytes()
    source_id = uuid4()
    source = Source(
        id=source_id,
        user_id="user-a",
        title="流程图",
        filename="flow.png",
        content_type="image/png",
        kind="fact",
        status="pending",
        version=1,
        object_key=f"sources/{source_id}",
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )
    db = SimpleNamespace(
        scalar=AsyncMock(side_effect=[source, source]),
        execute=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        add=Mock(),
    )

    class FakeStorage:
        def get(self, key: str) -> bytes:
            return data

    class FakeVision:
        async def analyze(self, raw: bytes, content_type: str) -> image_module.ImageAnalysis:
            assert raw == data and content_type == "image/png"
            return image_module.ImageAnalysis(visible_text="RAG -> 草稿", description="流程图")

    class FakeEmbedding:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            assert "RAG -> 草稿" in texts[0]
            return [[0.1] * 768]

    monkeypatch.setattr(service, "get_source_storage", lambda: FakeStorage())
    monkeypatch.setattr(service, "VisionClient", FakeVision)
    monkeypatch.setattr(service, "EmbeddingClient", FakeEmbedding)
    monkeypatch.setattr(service.settings, "vision_model", "vision-test")
    await service.index_source(source_id, db)
    indexed = db.add.call_args.args[0]
    assert source.status == "ready"
    assert indexed.origin == "image_analysis"
    assert indexed.extraction_model == "vision-test"
    assert indexed.content.startswith("图片可见文字：")


@pytest.mark.asyncio
async def test_indexing_does_not_revive_a_deleting_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = b"reliable source"
    source_id = uuid4()
    source = Source(
        id=source_id,
        user_id="user-a",
        title="资料",
        filename="source.txt",
        content_type="text/plain",
        kind="fact",
        status="pending",
        version=1,
        object_key=f"sources/{source_id}",
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
    )
    db = SimpleNamespace(
        scalar=AsyncMock(side_effect=[source, source]),
        execute=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        add=Mock(),
    )

    class FakeStorage:
        def get(self, key: str) -> bytes:
            return data

    class FakeEmbedding:
        async def embed(self, texts: list[str]) -> list[list[float]]:
            source.status = "deleting"
            return [[0.1] * 768]

    monkeypatch.setattr(service, "get_source_storage", lambda: FakeStorage())
    monkeypatch.setattr(service, "EmbeddingClient", FakeEmbedding)
    await service.index_source(source_id, db)
    assert source.status == "deleting"
    db.add.assert_not_called()
    db.rollback.assert_awaited_once()


def test_minio_storage_round_trip_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    objects: dict[str, bytes] = {}

    class FakeResponse:
        def __init__(self, data: bytes) -> None:
            self.data = data

        def read(self, size: int) -> bytes:
            return self.data[:size]

        def close(self) -> None:
            pass

        def release_conn(self) -> None:
            pass

    class FakeMinio:
        bucket_created = False

        def __init__(self, endpoint: str, **kwargs: object) -> None:
            assert endpoint == "localhost:19000"

        def bucket_exists(self, bucket: str) -> bool:
            return self.bucket_created

        def make_bucket(self, bucket: str) -> None:
            self.bucket_created = True

        def put_object(
            self, bucket: str, key: str, stream: object, length: int, **kwargs: object
        ) -> None:
            objects[key] = stream.read(length)

        def get_object(self, bucket: str, key: str) -> FakeResponse:
            return FakeResponse(objects[key])

        def remove_object(self, bucket: str, key: str) -> None:
            del objects[key]

    monkeypatch.setattr(storage_module, "Minio", FakeMinio)
    store = storage_module.SourceStorage()
    store.put("sources/123", b"hello", "text/plain")
    assert store.get("sources/123") == b"hello"
    store.delete("sources/123")
    assert objects == {}


@pytest.mark.asyncio
async def test_embedding_client_orders_and_validates_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, object]:
            return {
                "data": [
                    {"index": 1, "embedding": [0.2] * 768},
                    {"index": 0, "embedding": [0.1] * 768},
                ]
            }

    class FakeHttpClient:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["base_url"].endswith("/v1/")

        async def __aenter__(self) -> "FakeHttpClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, path: str, **kwargs: object) -> FakeResponse:
            assert path == "embeddings"
            assert kwargs["json"]["input"] == ["第一段", "第二段"]
            return FakeResponse()

    monkeypatch.setattr(embedding_module.httpx, "AsyncClient", FakeHttpClient)
    vectors = await embedding_module.EmbeddingClient().embed(["第一段", "第二段"])
    assert vectors[0][0] == 0.1
    assert vectors[1][0] == 0.2
