from __future__ import annotations

import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from rap.agg.frameworks import importance_performance, journey_map, kano_view
from rap.agg.history import record_comparison
from rap.agg.queries import (
    compare,
    competitor_pull,
    feedback_types,
    review_explorer,
    theme_detail,
)
from rap.agg.themes import metrics_catalog
from rap.api.deps import common_filters
from rap.llm.summarize import summarize_compare
from rap.stats_cli import quality_stats

router = APIRouter()
log = logging.getLogger(__name__)


def _remember(
    a: str, b: str, common: dict[str, Any], payload: dict[str, Any], summary: dict[str, Any] | None
) -> None:
    """Keep this result in History. Never lets a bookkeeping failure break the dashboard."""
    try:
        record_comparison(
            a,
            b,
            compare_payload=payload,
            summary=summary,
            frameworks={
                "journey": journey_map(a, b, **common),
                "kano": kano_view(a, b, **common),
                "ipa": importance_performance(a, b, **common),
            },
            filters=common.get("filters"),
        )
    except Exception:  # noqa: BLE001
        log.exception("could not record comparison %s vs %s", a, b)


@router.get("/compare")
def get_compare(
    a: str,
    b: str,
    common: dict[str, Any] = Depends(common_filters),
) -> dict[str, Any]:
    payload = compare(a, b, **common).model_dump()
    _remember(a, b, common, payload, None)
    return payload


@router.get("/summary")
def get_summary(
    a: str,
    b: str,
    regenerate: bool = False,
    common: dict[str, Any] = Depends(common_filters),
) -> dict[str, Any]:
    payload = compare(a, b, **common).model_dump()
    summary = summarize_compare(payload, regenerate=regenerate)
    _remember(a, b, common, payload, summary)
    return summary


@router.get("/theme/{theme}")
def get_theme(
    theme: str,
    a: str,
    b: str,
    page: int = 1,
    common: dict[str, Any] = Depends(common_filters),
) -> dict[str, Any]:
    return {
        "a": theme_detail(a, theme, page=page, **common),
        "b": theme_detail(b, theme, page=page, **common),
    }


@router.get("/frameworks/journey")
def get_journey(a: str, b: str, common: dict[str, Any] = Depends(common_filters)) -> dict[str, Any]:
    return journey_map(a, b, **common)


@router.get("/frameworks/kano")
def get_kano(a: str, b: str, common: dict[str, Any] = Depends(common_filters)) -> dict[str, Any]:
    return kano_view(a, b, **common)


@router.get("/frameworks/ipa")
def get_ipa(a: str, b: str, common: dict[str, Any] = Depends(common_filters)) -> dict[str, Any]:
    return importance_performance(a, b, **common)


@router.get("/competitors")
def get_competitors(
    a: str, b: str, common: dict[str, Any] = Depends(common_filters)
) -> dict[str, Any]:
    return {"a": competitor_pull(a, **common), "b": competitor_pull(b, **common)}


@router.get("/feedback-types")
def get_feedback(
    a: str, b: str, common: dict[str, Any] = Depends(common_filters)
) -> dict[str, Any]:
    return {"a": feedback_types(a, **common), "b": feedback_types(b, **common)}


@router.get("/reviews")
def get_reviews(
    company: str,
    theme: str | None = None,
    sub_theme: str | None = None,
    sentiment: str | None = None,
    language: str | None = None,
    feedback_type: str | None = None,
    churn_intent: bool | None = None,
    competitor: str | None = None,
    flagged: bool | None = None,
    page: int = 1,
    common: dict[str, Any] = Depends(common_filters),
) -> dict[str, Any]:
    return review_explorer(
        company,
        theme=theme,
        sub_theme=sub_theme,
        sentiment=sentiment,
        language=language,
        feedback_type=feedback_type,
        churn_intent=churn_intent,
        competitor=competitor,
        flagged=flagged,
        page=page,
        **common,
    )


@router.get("/quality")
def get_quality() -> list[dict[str, Any]]:
    return quality_stats()


@router.get("/metrics-glossary")
def get_glossary() -> dict[str, Any]:
    return metrics_catalog()


@router.get("/export.csv")
def export_csv(
    company: str,
    common: dict[str, Any] = Depends(common_filters),
) -> StreamingResponse:
    data = review_explorer(company, page=1, page_size=10_000, **common)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "id",
            "store",
            "date",
            "stars",
            "title",
            "body",
            "title_en",
            "body_en",
            "language",
            "overall_sentiment",
            "feedback_type",
            "churn_intent",
            "excluded",
        ],
    )
    writer.writeheader()
    for item in data["items"]:
        writer.writerow({k: item.get(k) for k in writer.fieldnames})
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reviews.csv"},
    )
