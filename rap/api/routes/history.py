from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rap.agg.frameworks import importance_performance, journey_map, kano_view
from rap.agg.history import (
    delete_comparison,
    get_comparison,
    list_comparisons,
    record_comparison,
    update_comparison,
)
from rap.agg.load import Filters
from rap.agg.queries import compare
from rap.llm.summarize import cache_key, get_cached

router = APIRouter()


class HistoryPatch(BaseModel):
    title: str | None = None
    pinned: bool | None = None


class SaveRequest(BaseModel):
    a: str
    b: str
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    since_launch: bool = False
    exclude_flagged: bool = True
    food_related_only: bool = True
    weighted: bool = True
    title: str | None = None
    pinned: bool = True


@router.post("/history/save")
def save_report(body: SaveRequest) -> dict[str, Any]:
    """Save the report the user is looking at, under a name.

    Uses the narrative already in the cache; never starts a new LLM call.
    """
    filters = Filters(
        exclude_flagged=body.exclude_flagged,
        food_related_only=body.food_related_only,
        weighted=body.weighted,
    )
    common = {
        "date_from": body.date_from,
        "date_to": body.date_to,
        "since_launch": body.since_launch,
        "filters": filters,
    }
    payload = compare(body.a, body.b, **common).model_dump()
    summary = get_cached(cache_key({"kind": "summary", "compare": payload}))
    saved_id = record_comparison(
        body.a,
        body.b,
        compare_payload=payload,
        summary=summary,
        frameworks={
            "journey": journey_map(body.a, body.b, **common),
            "kano": kano_view(body.a, body.b, **common),
            "ipa": importance_performance(body.a, body.b, **common),
        },
        filters=filters,
    )
    if saved_id is None:
        raise HTTPException(
            status_code=409,
            detail="Nothing to save yet: both companies need analysed reviews in this range.",
        )
    row = update_comparison(saved_id, title=body.title, pinned=body.pinned)
    assert row is not None
    row["has_summary"] = bool(summary)
    return row


@router.get("/history")
def get_history() -> list[dict[str, Any]]:
    return list_comparisons()


@router.get("/history/{saved_id}")
def get_history_item(saved_id: int) -> dict[str, Any]:
    row = get_comparison(saved_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Saved comparison not found.")
    return row


@router.patch("/history/{saved_id}")
def patch_history_item(saved_id: int, body: HistoryPatch) -> dict[str, Any]:
    row = update_comparison(saved_id, title=body.title, pinned=body.pinned)
    if row is None:
        raise HTTPException(status_code=404, detail="Saved comparison not found.")
    return row


@router.delete("/history/{saved_id}")
def delete_history_item(saved_id: int) -> dict[str, Any]:
    if not delete_comparison(saved_id):
        raise HTTPException(status_code=404, detail="Saved comparison not found.")
    return {"ok": True}
