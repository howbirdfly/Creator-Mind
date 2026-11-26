from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    source_url: Mapped[str | None] = mapped_column(Text)
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_sources_user_created_at_id", "user_id", "created_at", "id"),)
