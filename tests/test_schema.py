from __future__ import annotations

import pytest
from pydantic import ValidationError

from rap.llm.extract import batch_reviews, validate_batch
from rap.llm.schemas import ExtractionBatch, ReviewExtraction


def _item(rid: int) -> dict:
    return {
        "review_id": rid,
        "language": "en",
        "is_food_related": True,
        "overall_sentiment": "negative",
        "feedback_type": "complaint",
        "churn_intent": False,
        "competitor_mentions": [],
        "mentions": [
            {
                "theme": "late_delivery",
                "sub_theme": "eta_inaccurate",
                "sentiment": "negative",
                "confidence": 0.9,
                "snippet": "arrived an hour late",
                "snippet_en": None,
            }
        ],
        "mentions_incentive": False,
        "low_information": False,
        "rating_text_mismatch": False,
    }


def test_schema_valid() -> None:
    batch = ExtractionBatch.model_validate({"items": [_item(1), _item(2)]})
    assert len(batch.items) == 2
    assert batch.items[0].mentions[0].theme == "late_delivery"


def test_schema_rejects_bad_theme() -> None:
    payload = _item(1)
    payload["mentions"][0]["theme"] = "not_a_theme"
    with pytest.raises(ValidationError):
        ReviewExtraction.model_validate(payload)


def test_validate_batch_unknown_id() -> None:
    valid, invalid = validate_batch({"items": [_item(1), _item(99)]}, {1, 2})
    assert [v.review_id for v in valid] == [1]
    assert 2 in invalid
    assert 99 not in [v.review_id for v in valid]


def test_batching() -> None:
    class R:
        def __init__(self, i: int) -> None:
            self.id = i

    rows = [R(i) for i in range(10)]  # type: ignore[list-item]
    batches = batch_reviews(rows, 3)  # type: ignore[arg-type]
    assert len(batches) == 4
    assert len(batches[-1]) == 1
