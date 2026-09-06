from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from rap.visitors import normalize_visitor_id, touch_visitor, traffic_counts, visitor_has_key

router = APIRouter()


@router.post("/presence")
def post_presence(x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id")) -> dict[str, int | bool]:
    visitor_id = normalize_visitor_id(x_visitor_id)
    if not visitor_id:
        raise HTTPException(400, "Missing visitor id")
    touch_visitor(visitor_id)
    counts = traffic_counts()
    return {**counts, "has_own_key": visitor_has_key(visitor_id)}


@router.get("/presence")
def get_presence() -> dict[str, int]:
    return traffic_counts()
