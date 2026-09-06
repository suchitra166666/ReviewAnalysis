from __future__ import annotations

import datetime as dt
import enum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StoreEnum(str, enum.Enum):
    appstore = "appstore"
    play = "play"


class ScrapeStatusEnum(str, enum.Enum):
    running = "running"
    ok = "ok"
    failed = "failed"
    partial = "partial"


class SettingValueType(str, enum.Enum):
    string = "string"
    number = "number"
    bool = "bool"
    json = "json"
    secret_ref = "secret_ref"


class JobKind(str, enum.Enum):
    scrape = "scrape"
    extract_a = "extract_a"
    extract_b = "extract_b"
    reconcile = "reconcile"
    translate = "translate"
    flags = "flags"
    summarize = "summarize"
    full_pipeline = "full_pipeline"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    ok = "ok"
    failed = "failed"
    cancelled = "cancelled"


class LlmPurpose(str, enum.Enum):
    extract_a = "extract_a"
    extract_b = "extract_b"
    tiebreak = "tiebreak"
    translate = "translate"
    summarize = "summarize"
    embed = "embed"


class ExtractRole(str, enum.Enum):
    a = "a"
    b = "b"
    tiebreak = "tiebreak"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    appstore_id: Mapped[str | None] = mapped_column(String(40))
    play_package: Mapped[str | None] = mapped_column(String(200))
    launch_date_ae: Mapped[dt.date | None] = mapped_column(Date)
    is_super_app: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    scrape_runs: Mapped[list[ScrapeRun]] = relationship(back_populates="company")
    reviews: Mapped[list[ReviewRaw]] = relationship(back_populates="company")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    store: Mapped[StoreEnum] = mapped_column(Enum(StoreEnum, name="store_enum"), nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ScrapeStatusEnum] = mapped_column(
        Enum(ScrapeStatusEnum, name="scrape_status_enum"), nullable=False
    )
    new_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="scrape_runs")


class ReviewRaw(Base):
    __tablename__ = "reviews_raw"
    __table_args__ = (
        UniqueConstraint("store", "store_review_id", name="uq_reviews_raw_store_id"),
        Index("ix_reviews_raw_company_date", "company_id", "review_date"),
        Index("ix_reviews_raw_company_stars", "company_id", "star_rating"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    store: Mapped[StoreEnum] = mapped_column(Enum(StoreEnum, name="store_enum"), nullable=False)
    store_review_id: Mapped[str] = mapped_column(String(200), nullable=False)
    review_date: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    star_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(300))
    app_version: Mapped[str | None] = mapped_column(String(80))
    thumbs_up: Mapped[int | None] = mapped_column(Integer)
    reply_body: Mapped[str | None] = mapped_column(Text)
    reply_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    language_hint: Mapped[str | None] = mapped_column(String(16))
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scraped_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    scrape_run_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_runs.id"))

    company: Mapped[Company] = relationship(back_populates="reviews")


class ReviewTranslation(Base):
    __tablename__ = "review_translations"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews_raw.id"), primary_key=True)
    title_en: Mapped[str | None] = mapped_column(Text)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purpose: Mapped[LlmPurpose] = mapped_column(
        Enum(LlmPurpose, name="llm_purpose_enum"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(200))
    n_items: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReviewExtracted(Base):
    __tablename__ = "reviews_extracted"
    __table_args__ = (
        UniqueConstraint(
            "review_id", "role", "prompt_version", name="uq_reviews_extracted_role_ver"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews_raw.id"), nullable=False)
    role: Mapped[ExtractRole] = mapped_column(
        Enum(ExtractRole, name="extract_role_enum"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    llm_call_id: Mapped[int | None] = mapped_column(ForeignKey("llm_calls.id"))
    language: Mapped[str | None] = mapped_column(String(16))
    overall_sentiment: Mapped[str | None] = mapped_column(String(16))
    is_food_related: Mapped[bool | None] = mapped_column(Boolean)
    feedback_type: Mapped[str | None] = mapped_column(String(40))
    churn_intent: Mapped[bool | None] = mapped_column(Boolean)
    competitor_mentions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    mentions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    mentions_incentive: Mapped[bool | None] = mapped_column(Boolean)
    low_information: Mapped[bool | None] = mapped_column(Boolean)
    rating_text_mismatch: Mapped[bool | None] = mapped_column(Boolean)
    schema_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReviewFinal(Base):
    __tablename__ = "reviews_final"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews_raw.id"), primary_key=True)
    source_role: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence_tier: Mapped[str] = mapped_column(String(24), nullable=False)
    disagreement_themes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    language: Mapped[str | None] = mapped_column(String(16))
    overall_sentiment: Mapped[str | None] = mapped_column(String(16))
    is_food_related: Mapped[bool | None] = mapped_column(Boolean)
    feedback_type: Mapped[str | None] = mapped_column(String(40))
    churn_intent: Mapped[bool | None] = mapped_column(Boolean)
    competitor_mentions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    mentions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    mentions_incentive: Mapped[bool | None] = mapped_column(Boolean)
    low_information: Mapped[bool | None] = mapped_column(Boolean)
    rating_text_mismatch: Mapped[bool | None] = mapped_column(Boolean)
    schema_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    resolved_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReviewEmbedding(Base):
    __tablename__ = "review_embeddings"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews_raw.id"), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReviewFlag(Base):
    __tablename__ = "review_flags"

    review_id: Mapped[int] = mapped_column(ForeignKey("reviews_raw.id"), primary_key=True)
    near_duplicate_of: Mapped[int | None] = mapped_column(ForeignKey("reviews_raw.id"))
    dup_similarity: Mapped[float | None] = mapped_column(Float)
    burst_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    incentivized_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    excluded_from_aggregates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exclusion_reasons: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalysisCache(Base):
    __tablename__ = "analysis_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    invalidated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(400), nullable=False)
    api_key_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_last4: Mapped[str | None] = mapped_column(String(8))
    is_openai_compatible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_batch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_structured_outputs: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    disable_thinking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_verify_status: Mapped[str | None] = mapped_column(String(40))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[SettingValueType] = mapped_column(
        Enum(SettingValueType, name="setting_value_type"), nullable=False
    )
    group: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[JobKind] = mapped_column(Enum(JobKind, name="job_kind_enum"), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"), default=JobStatus.queued, nullable=False
    )
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    est_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    log: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SavedComparison(Base):
    """A dashboard result the user has seen, kept so it can be reopened later.

    One row per distinct result: the same companies, range and filters produce a
    new row only when the underlying compare payload changes (``compare_hash``).
    """

    __tablename__ = "saved_comparisons"
    __table_args__ = (
        UniqueConstraint(
            "a_slug",
            "b_slug",
            "date_from",
            "date_to",
            "filters_key",
            "compare_hash",
            name="uq_saved_comparison",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    a_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    b_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    date_from: Mapped[dt.date] = mapped_column(Date, nullable=False)
    date_to: Mapped[dt.date] = mapped_column(Date, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    filters_key: Mapped[str] = mapped_column(String(64), nullable=False)
    compare_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    n_a: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    n_b: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sample: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    headline: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_viewed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SiteVisitor(Base):
    """Anonymous browser session for traffic counts and visitor-owned keys."""

    __tablename__ = "site_visitors"

    visitor_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    keys: Mapped[list["SiteVisitorKey"]] = relationship(back_populates="visitor")


class SiteVisitorKey(Base):
    __tablename__ = "site_visitor_keys"
    __table_args__ = (UniqueConstraint("visitor_id", "provider_slug", name="uq_visitor_provider"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visitor_id: Mapped[str] = mapped_column(ForeignKey("site_visitors.visitor_id"), nullable=False)
    provider_slug: Mapped[str] = mapped_column(String(80), nullable=False)
    api_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_last4: Mapped[str] = mapped_column(String(8), nullable=False)
    last_verify_status: Mapped[str | None] = mapped_column(String(40))
    last_verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    visitor: Mapped[SiteVisitor] = relationship(back_populates="keys")
