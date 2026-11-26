from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    source_url: str | None
    created_at: datetime


class SourceCount(BaseModel):
    total: int
