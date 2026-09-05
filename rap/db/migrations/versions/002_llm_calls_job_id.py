"""associate llm_calls with jobs

Revision ID: 002_llm_job
Revises: 001_initial
Create Date: 2026-09-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_llm_job"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("llm_calls", sa.Column("job_id", sa.Integer(), nullable=True))
    op.create_index("ix_llm_calls_job_id", "llm_calls", ["job_id"])
    op.create_foreign_key(
        "fk_llm_calls_job_id",
        "llm_calls",
        "jobs",
        ["job_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_llm_calls_job_id", "llm_calls", type_="foreignkey")
    op.drop_index("ix_llm_calls_job_id", table_name="llm_calls")
    op.drop_column("llm_calls", "job_id")
