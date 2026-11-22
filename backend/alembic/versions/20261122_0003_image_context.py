"""Record image provenance and bounded neighboring context on chunks.

Revision ID: 20261122_0003
Revises: 20261121_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261122_0003"
down_revision: str | Sequence[str] | None = "20261121_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "source_chunks", sa.Column("context_before", sa.Text(), nullable=False, server_default="")
    )
    op.add_column(
        "source_chunks", sa.Column("context_after", sa.Text(), nullable=False, server_default="")
    )
    op.add_column(
        "source_chunks",
        sa.Column("origin", sa.String(16), nullable=False, server_default="document"),
    )
    op.add_column("source_chunks", sa.Column("extraction_model", sa.String(128)))


def downgrade() -> None:
    op.drop_column("source_chunks", "extraction_model")
    op.drop_column("source_chunks", "origin")
    op.drop_column("source_chunks", "context_after")
    op.drop_column("source_chunks", "context_before")
