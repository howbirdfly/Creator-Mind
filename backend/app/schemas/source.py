from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceKind = Literal["fact", "style"]
SourceStatus = Literal["pending", "processing", "ready", "failed", "deleting", "deleted"]


class SourceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    title: str
    filename: str
    content_type: str
    kind: SourceKind
    status: SourceStatus
    version: int
    size_bytes: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=1000)
    context: str | None = Field(default=None, max_length=1000)
    kind: SourceKind = "fact"
    mode: Literal["semantic", "keyword"] = "semantic"
    source_ids: list[UUID] | None = None
    limit: int = Field(default=8, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("检索问题至少需要两个非空字符")
        return value

    @field_validator("context")
    @classmethod
    def normalize_context(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class EvidenceItem(BaseModel):
    evidence_id: str
    source_id: UUID
    chunk_id: UUID
    source_version: int
    source_kind: SourceKind
    title: str
    excerpt: str
    page_number: int | None
    section: str | None
    context_before: str = ""
    context_after: str = ""
    origin: Literal["document", "image_analysis"] = "document"
    extraction_model: str | None = None
    start_offset: int
    end_offset: int
    similarity: float
    method: Literal["semantic", "keyword"]


class SearchResponse(BaseModel):
    evidence: list[EvidenceItem]
    gap: str | None = None


class CitationResponse(BaseModel):
    source_id: UUID
    chunk_id: UUID
    status: Literal["valid", "deleted", "missing"]
    title: str
    source_version: int
    excerpt: str | None = None
    page_number: int | None = None
    section: str | None = None
    context_before: str = ""
    context_after: str = ""
    origin: Literal["document", "image_analysis"] | None = None
    extraction_model: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
