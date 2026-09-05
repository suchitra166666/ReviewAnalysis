from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field


class IntervalOut(BaseModel):
    low: float
    high: float
    n_eff: float


class MetaOut(BaseModel):
    n_raw: int
    n_used: int
    low_confidence: bool
    data_as_of: dt.datetime
    company_slug: str
    company_name: str
    date_from: dt.date
    date_to: dt.date


class SnippetOut(BaseModel):
    text: str
    text_en: str | None = None
    language: str
    review_id: int
    stars: int
    date: str


class MetricValue(BaseModel):
    value: float | None
    ci: IntervalOut | None = None
    n: int = 0
    unit: str = ""


class OverviewOut(BaseModel):
    meta: MetaOut
    reviews_analysed: int
    reviews_scraped: int
    reviews_excluded: int
    exclusion_reasons: dict[str, int]
    analysed_average_rating: MetricValue
    store_headline_rating: MetricValue
    rating_gap: float | None
    positive_pct: MetricValue
    negative_pct: MetricValue
    neutral_mixed_pct: MetricValue
    net_sentiment: MetricValue
    promo_dependence: MetricValue
    churn_signal: MetricValue
    developer_response_rate: MetricValue
    developer_reply_hours: float | None
    agreement_rate: MetricValue
    sparkline_net: list[float] = Field(default_factory=list)
    sparkline_neg: list[float] = Field(default_factory=list)
    sparkline_rating: list[float] = Field(default_factory=list)


class StarBucket(BaseModel):
    stars: int
    share_weighted: float
    share_raw: float
    n: int
    top_themes: list[str]


class StarScenarioOut(BaseModel):
    meta: MetaOut
    buckets: list[StarBucket]
    five_star_promo_share: float | None
    five_star_low_info_share: float | None
    one_star_recover_share: float | None
    one_star_receive_wait_share: float | None
    one_star_top_theme: str | None
    lines: list[str]


class ThemeRow(BaseModel):
    theme: str
    label: str
    # how the theme reads when it is a strength ("Deliveries arrive on time")
    positive_label: str | None = None
    journey_stage: str | None
    kano: str | None
    mention_share: float
    # distinct reviews that mention the theme (unweighted)
    n_mentions: int = 0
    negative_rate: float
    positive_rate: float
    negative_ci: IntervalOut | None = None
    star_drag: float | None = None
    severity: float | None = None
    trend: float | None = None
    top_sub_themes: list[str] = Field(default_factory=list)
    snippets: list[SnippetOut] = Field(default_factory=list)
    explanation: str | None = None
    sparkline: list[float] = Field(default_factory=list)


class CompareMetric(BaseModel):
    key: str
    a: float | None
    b: float | None
    delta: float | None
    ci: IntervalOut | None = None
    better: str | None = None


class CompareOut(BaseModel):
    a: dict[str, Any]
    b: dict[str, Any]
    deltas: list[CompareMetric]
    since_launch: bool
    date_from: dt.date
    date_to: dt.date
    launch_note: str | None = None
    sample: dict[str, Any] | None = None
