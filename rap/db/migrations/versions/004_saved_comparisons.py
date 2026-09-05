"""saved comparisons: reopen earlier dashboard results from the UI

Revision ID: 004_saved_cmp
Revises: 003_ext_job
Create Date: 2026-09-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_saved_cmp"
down_revision: str | None = "003_ext_job"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_comparisons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("a_slug", sa.String(length=80), nullable=False),
        sa.Column("b_slug", sa.String(length=80), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("filters_key", sa.String(length=64), nullable=False),
        sa.Column("compare_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("n_a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_b", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "a_slug",
            "b_slug",
            "date_from",
            "date_to",
            "filters_key",
            "compare_hash",
            name="uq_saved_comparison",
        ),
    )
    op.create_index("ix_saved_comparisons_last_viewed_at", "saved_comparisons", ["last_viewed_at"])


def downgrade() -> None:
    op.drop_index("ix_saved_comparisons_last_viewed_at", table_name="saved_comparisons")
    op.drop_table("saved_comparisons")
