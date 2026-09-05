from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Theme = Literal[
    "late_delivery",
    "missing_wrong_items",
    "food_condition",
    "refund_compensation",
    "customer_support",
    "app_bugs",
    "payment_checkout",
    "fees_pricing",
    "promotions",
    "rider_behaviour",
    "restaurant_availability",
    "account_trust",
    "other",
]
Sentiment = Literal["positive", "negative", "neutral", "mixed"]
Language = Literal["en", "ar", "mixed", "other"]
FeedbackType = Literal["bug_report", "feature_request", "complaint", "praise", "question", "other"]


class Mention(BaseModel):
    theme: Theme
    sub_theme: str | None = None
    sentiment: Sentiment
    confidence: float = Field(ge=0, le=1)
    snippet: str = Field(max_length=200)
    snippet_en: str | None = None


class CompetitorMention(BaseModel):
    competitor_raw: str
    comparison: Literal["competitor_better", "competitor_worse", "neutral"]
    competitor_slug: str | None = None


class ReviewExtraction(BaseModel):
    review_id: int
    language: Language
    is_food_related: bool
    overall_sentiment: Sentiment
    feedback_type: FeedbackType
    churn_intent: bool
    competitor_mentions: list[CompetitorMention] = Field(default_factory=list)
    mentions: list[Mention] = Field(default_factory=list)
    mentions_incentive: bool
    low_information: bool
    rating_text_mismatch: bool


class ExtractionBatch(BaseModel):
    items: list[ReviewExtraction]


class NarrativeSummary(BaseModel):
    executive_summary: str
    key_differentiators: list[str]
    what_a_does_that_b_doesnt: list[str]
    what_b_does_that_a_doesnt: list[str]
    journey_read: dict[str, str]
    kano_read: str
    pain_point_explanations: dict[str, str]
    pm_actions_a: list[str]
    pm_actions_b: list[str]
    watch_list: list[str]
    competitor_pull_read: str
    caveats: list[str]

    @field_validator("kano_read", mode="before")
    @classmethod
    def _kano_as_string(cls, value: object) -> str:
        if isinstance(value, dict):
            return " ".join(str(part).strip() for part in value.values() if part)
        return str(value or "")

    @field_validator("pain_point_explanations", mode="before")
    @classmethod
    def _pains_as_dict(cls, value: object) -> dict[str, str]:
        if isinstance(value, list):
            out: dict[str, str] = {}
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    theme = str(item.get("theme") or item.get("key") or i)
                    out[theme] = str(item.get("text") or item.get("explanation") or item)
                else:
                    out[str(i)] = str(item)
            return out
        if isinstance(value, dict):
            return {str(k): str(v) for k, v in value.items()}
        return {}

    @field_validator("journey_read", mode="before")
    @classmethod
    def _journey_as_dict(cls, value: object) -> dict[str, str]:
        if isinstance(value, dict):
            return {str(k): str(v) if not isinstance(v, dict) else " ".join(str(x) for x in v.values()) for k, v in value.items()}
        if isinstance(value, list):
            return {str(i): str(item) for i, item in enumerate(value)}
        return {}

    @field_validator(
        "key_differentiators",
        "what_a_does_that_b_doesnt",
        "what_b_does_that_a_doesnt",
        "pm_actions_a",
        "pm_actions_b",
        "watch_list",
        "caveats",
        mode="before",
    )
    @classmethod
    def _as_str_list(cls, value: object) -> list[str]:
        if isinstance(value, list):
            out: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    out.append(str(item.get("theme") or item.get("text") or item.get("action") or item))
                else:
                    out.append(str(item))
            return out
        if isinstance(value, dict):
            out = []
            for key, item in value.items():
                if isinstance(item, list):
                    out.extend(str(x) for x in item)
                elif isinstance(item, dict):
                    out.append(str(item.get("theme") or item.get("text") or item))
                else:
                    out.append(f"{key}: {item}" if not str(item).startswith(str(key)) else str(item))
            return out
        if value is None:
            return []
        return [str(value)]
