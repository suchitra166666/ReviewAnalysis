from __future__ import annotations

from types import SimpleNamespace

from rap.llm.reconcile import disagreements


def _row(**kwargs):
    base = dict(
        language="en",
        overall_sentiment="negative",
        is_food_related=True,
        feedback_type="complaint",
        churn_intent=False,
        mentions_incentive=False,
        low_information=False,
        rating_text_mismatch=False,
        mentions=[{"theme": "late_delivery", "sentiment": "negative", "snippet": "late"}],
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_agreed_pair() -> None:
    a = _row()
    b = _row(mentions=[{"theme": "late_delivery", "sentiment": "negative", "snippet": "different"}])
    assert disagreements(a, b) == []


def test_neutral_mixed_agree() -> None:
    a = _row(overall_sentiment="neutral")
    b = _row(overall_sentiment="mixed")
    assert "overall_sentiment" not in disagreements(a, b)


def test_theme_disagreement() -> None:
    a = _row()
    b = _row(mentions=[{"theme": "fees_pricing", "sentiment": "negative"}])
    diffs = disagreements(a, b)
    assert "late_delivery" in diffs
    assert "fees_pricing" in diffs


def test_boolean_disagreement() -> None:
    a = _row(churn_intent=True)
    b = _row(churn_intent=False)
    assert "churn_intent" in disagreements(a, b)
