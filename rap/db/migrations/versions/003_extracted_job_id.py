"""track which job sampled an extracted review

Revision ID: 003_ext_job
Revises: 002_llm_job
Create Date: 2026-09-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_ext_job"
down_revision: Union[str, None] = "002_llm_job"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reviews_extracted", sa.Column("job_id", sa.Integer(), nullable=True))
    op.create_index("ix_reviews_extracted_job_id", "reviews_extracted", ["job_id"])
    op.create_foreign_key(
        "fk_reviews_extracted_job_id",
        "reviews_extracted",
        "jobs",
        ["job_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_reviews_extracted_job_id", "reviews_extracted", type_="foreignkey")
    op.drop_index("ix_reviews_extracted_job_id", table_name="reviews_extracted")
    op.drop_column("reviews_extracted", "job_id")
