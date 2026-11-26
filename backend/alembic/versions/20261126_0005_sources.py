"""Create the source library.

Revision ID: 20261126_0005
Revises: 20261122_0004
"""

import sqlalchemy as sa

from alembic import op

revision = "20261126_0005"
down_revision = "20261122_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("object_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_sources_user_created_at_id", "sources", ["user_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_sources_user_created_at_id", table_name="sources")
    op.drop_table("sources")
