"""Add RAG sources and their indexed chunks.

Revision ID: 20261121_0002
Revises: 20261120_0002
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261121_0002"
down_revision: str | Sequence[str] | None = "20261120_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(512)),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(500)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_sources_user_id", "sources", ["user_id"])
    op.create_table(
        "source_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section", sa.String(255)),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.String(128), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(768), nullable=False),
    )
    op.create_index("ix_source_chunks_user_source", "source_chunks", ["user_id", "source_id"])
    op.create_index(
        "ix_source_chunks_source_ordinal", "source_chunks", ["source_id", "ordinal"], unique=True
    )


def downgrade() -> None:
    op.drop_table("source_chunks")
    op.drop_table("sources")
