from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from rap.db.models import AnalysisCache, LlmPurpose
from rap.db.session import session_scope
from rap.llm.client import call_llm, load_prompt, parse_json_content
from rap.llm.schemas import NarrativeSummary
from rap.settings import role_config

ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]


def cache_key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def get_cached(key: str) -> dict[str, Any] | None:
    with session_scope() as session:
        row = session.scalar(
            select(AnalysisCache).where(
                AnalysisCache.cache_key == key, AnalysisCache.invalidated_at.is_(None)
            )
        )
        return row.payload if row else None


def store_cache(key: str, payload: dict[str, Any], model_id: str) -> None:
    with session_scope() as session:
        existing = session.scalar(select(AnalysisCache).where(AnalysisCache.cache_key == key))
        if existing:
            existing.payload = payload
            existing.model_id = model_id
            existing.invalidated_at = None
        else:
            session.add(AnalysisCache(cache_key=key, payload=payload, model_id=model_id))


def invalidate_range() -> None:
    with session_scope() as session:
        now = dt.datetime.now(dt.timezone.utc)
        for row in session.scalars(select(AnalysisCache).where(AnalysisCache.invalidated_at.is_(None))):
            row.invalidated_at = now


def summarize_compare(compare_payload: dict[str, Any], *, regenerate: bool = False) -> dict[str, Any]:
    key = cache_key({"kind": "summary", "compare": compare_payload})
    if not regenerate:
        cached = get_cached(key)
        if cached:
            return cached
    result = call_llm(
        purpose=LlmPurpose.summarize,
        role="summarize",
        messages=[
            {"role": "system", "content": load_prompt("summarize_v3.md")},
            {"role": "user", "content": json.dumps(compare_payload, default=str)[:80_000]},
        ],
        json_object=True,
        n_items=1,
    )
    parsed = NarrativeSummary.model_validate(parse_json_content(result["content"]))
    payload = parsed.model_dump()
    payload["model_id"] = result["model_id"]
    payload["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    store_cache(key, payload, result["model_id"])
    return payload


def pain_explanation(theme: str, context: dict[str, Any]) -> str:
    key = cache_key({"kind": "pain", "theme": theme, "context": context})
    cached = get_cached(key)
    if cached and cached.get("text"):
        return str(cached["text"])
    # cheap template fallback so dashboards work without a call
    a = context.get("a_rate")
    b = context.get("b_rate")
    text = f"{theme.replace('_', ' ')} is a recurring complaint."
    if a is not None and b is not None:
        text = f"{theme.replace('_', ' ')}: {a:.1%} vs {b:.1%} negative-mention rate."
    store_cache(key, {"text": text}, role_config("summarize")["model"])
    return text


def run_summarize(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
) -> dict[str, Any]:
    from rap.agg.queries import compare

    if progress:
        progress(0, 1, "building compare payload")
    payload = compare(
        params["a"],
        params["b"],
        since_launch=bool(params.get("since_launch")),
        date_from=params.get("date_from"),
        date_to=params.get("date_to"),
    )
    if should_cancel and should_cancel():
        return {}
    summary = summarize_compare(payload.model_dump(), regenerate=bool(params.get("regenerate")))
    if progress:
        progress(1, 1, "summary stored")
    return summary
