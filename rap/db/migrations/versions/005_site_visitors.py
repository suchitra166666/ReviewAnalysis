"""Anonymous visitors: traffic counts and per-browser keys.

Revision ID: 005_visitors
Revises: 004_saved_cmp
Create Date: 2026-09-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_visitors"
down_revision: str | None = "004_saved_cmp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_visitors",
        sa.Column("visitor_id", sa.String(length=36), primary_key=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "site_visitor_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("visitor_id", sa.String(length=36), sa.ForeignKey("site_visitors.visitor_id"), nullable=False),
        sa.Column("provider_slug", sa.String(length=80), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("key_last4", sa.String(length=8), nullable=False),
        sa.Column("last_verify_status", sa.String(length=40)),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("visitor_id", "provider_slug", name="uq_visitor_provider"),
    )


def downgrade() -> None:
    op.drop_table("site_visitor_keys")
    op.drop_table("site_visitors")
