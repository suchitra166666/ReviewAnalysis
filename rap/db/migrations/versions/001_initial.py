"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    store_enum = postgresql.ENUM("appstore", "play", name="store_enum", create_type=False)
    scrape_status_enum = postgresql.ENUM(
        "running", "ok", "failed", "partial", name="scrape_status_enum", create_type=False
    )
    setting_value_type = postgresql.ENUM(
        "string", "number", "bool", "json", "secret_ref", name="setting_value_type", create_type=False
    )
    job_kind_enum = postgresql.ENUM(
        "scrape",
        "extract_a",
        "extract_b",
        "reconcile",
        "translate",
        "flags",
        "summarize",
        "full_pipeline",
        name="job_kind_enum",
        create_type=False,
    )
    job_status_enum = postgresql.ENUM(
        "queued", "running", "ok", "failed", "cancelled", name="job_status_enum", create_type=False
    )
    llm_purpose_enum = postgresql.ENUM(
        "extract_a",
        "extract_b",
        "tiebreak",
        "translate",
        "summarize",
        "embed",
        name="llm_purpose_enum",
        create_type=False,
    )
    extract_role_enum = postgresql.ENUM("a", "b", "tiebreak", name="extract_role_enum", create_type=False)

    store_enum.create(op.get_bind(), checkfirst=True)
    scrape_status_enum.create(op.get_bind(), checkfirst=True)
    setting_value_type.create(op.get_bind(), checkfirst=True)
    job_kind_enum.create(op.get_bind(), checkfirst=True)
    job_status_enum.create(op.get_bind(), checkfirst=True)
    llm_purpose_enum.create(op.get_bind(), checkfirst=True)
    extract_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("appstore_id", sa.String(40)),
        sa.Column("play_package", sa.String(200)),
        sa.Column("launch_date_ae", sa.Date()),
        sa.Column("is_super_app", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text()),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("store", store_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", scrape_status_enum, nullable=False),
        sa.Column("new_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "reviews_raw",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("store", store_enum, nullable=False),
        sa.Column("store_review_id", sa.String(200), nullable=False),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("star_rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(300)),
        sa.Column("app_version", sa.String(80)),
        sa.Column("thumbs_up", sa.Integer()),
        sa.Column("reply_body", sa.Text()),
        sa.Column("reply_date", sa.DateTime(timezone=True)),
        sa.Column("language_hint", sa.String(16)),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("scrape_run_id", sa.Integer(), sa.ForeignKey("scrape_runs.id")),
        sa.UniqueConstraint("store", "store_review_id", name="uq_reviews_raw_store_id"),
    )
    op.create_index("ix_reviews_raw_company_date", "reviews_raw", ["company_id", "review_date"])
    op.create_index("ix_reviews_raw_company_stars", "reviews_raw", ["company_id", "star_rating"])

    op.create_table(
        "review_translations",
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews_raw.id"), primary_key=True),
        sa.Column("title_en", sa.Text()),
        sa.Column("body_en", sa.Text(), nullable=False),
        sa.Column("model_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purpose", llm_purpose_enum, nullable=False),
        sa.Column("model_id", sa.String(120), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("request_id", sa.String(200)),
        sa.Column("n_items", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("est_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "reviews_extracted",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews_raw.id"), nullable=False),
        sa.Column("role", extract_role_enum, nullable=False),
        sa.Column("model_id", sa.String(120), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("llm_call_id", sa.Integer(), sa.ForeignKey("llm_calls.id")),
        sa.Column("language", sa.String(16)),
        sa.Column("overall_sentiment", sa.String(16)),
        sa.Column("is_food_related", sa.Boolean()),
        sa.Column("feedback_type", sa.String(40)),
        sa.Column("churn_intent", sa.Boolean()),
        sa.Column("competitor_mentions", postgresql.JSONB()),
        sa.Column("mentions", postgresql.JSONB()),
        sa.Column("mentions_incentive", sa.Boolean()),
        sa.Column("low_information", sa.Boolean()),
        sa.Column("rating_text_mismatch", sa.Boolean()),
        sa.Column("schema_valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("review_id", "role", "prompt_version", name="uq_reviews_extracted_role_ver"),
    )

    op.create_table(
        "reviews_final",
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews_raw.id"), primary_key=True),
        sa.Column("source_role", sa.String(16), nullable=False),
        sa.Column("confidence_tier", sa.String(24), nullable=False),
        sa.Column("disagreement_themes", postgresql.ARRAY(sa.Text())),
        sa.Column("language", sa.String(16)),
        sa.Column("overall_sentiment", sa.String(16)),
        sa.Column("is_food_related", sa.Boolean()),
        sa.Column("feedback_type", sa.String(40)),
        sa.Column("churn_intent", sa.Boolean()),
        sa.Column("competitor_mentions", postgresql.JSONB()),
        sa.Column("mentions", postgresql.JSONB()),
        sa.Column("mentions_incentive", sa.Boolean()),
        sa.Column("low_information", sa.Boolean()),
        sa.Column("rating_text_mismatch", sa.Boolean()),
        sa.Column("schema_valid", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "review_embeddings",
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews_raw.id"), primary_key=True),
        sa.Column("model_id", sa.String(120), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "review_flags",
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("reviews_raw.id"), primary_key=True),
        sa.Column("near_duplicate_of", sa.Integer(), sa.ForeignKey("reviews_raw.id")),
        sa.Column("dup_similarity", sa.Float()),
        sa.Column("burst_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("incentivized_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("excluded_from_aggregates", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("exclusion_reasons", postgresql.ARRAY(sa.Text())),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "analysis_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cache_key", sa.String(400), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("model_id", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "api_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_slug", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("base_url", sa.String(400), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary()),
        sa.Column("key_last4", sa.String(8)),
        sa.Column("is_openai_compatible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_batch", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_structured_outputs", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("disable_thinking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("last_verify_status", sa.String(40)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(200), primary_key=True),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("value_type", setting_value_type, nullable=False),
        sa.Column("group", sa.String(40), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", job_kind_enum, nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", job_status_enum, nullable=False, server_default="queued"),
        sa.Column("progress", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("est_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("log", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "worker_heartbeat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("worker_id", sa.String(80), nullable=False, unique=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeat")
    op.drop_table("jobs")
    op.drop_table("app_settings")
    op.drop_table("api_credentials")
    op.drop_table("analysis_cache")
    op.drop_table("review_flags")
    op.drop_table("review_embeddings")
    op.drop_table("reviews_final")
    op.drop_table("reviews_extracted")
    op.drop_table("llm_calls")
    op.drop_table("review_translations")
    op.drop_index("ix_reviews_raw_company_stars", table_name="reviews_raw")
    op.drop_index("ix_reviews_raw_company_date", table_name="reviews_raw")
    op.drop_table("reviews_raw")
    op.drop_table("scrape_runs")
    op.drop_table("companies")
    op.execute("DROP TYPE IF EXISTS extract_role_enum")
    op.execute("DROP TYPE IF EXISTS llm_purpose_enum")
    op.execute("DROP TYPE IF EXISTS job_status_enum")
    op.execute("DROP TYPE IF EXISTS job_kind_enum")
    op.execute("DROP TYPE IF EXISTS setting_value_type")
    op.execute("DROP TYPE IF EXISTS scrape_status_enum")
    op.execute("DROP TYPE IF EXISTS store_enum")
