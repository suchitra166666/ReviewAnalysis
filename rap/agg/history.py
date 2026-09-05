"""Saved comparisons: every dashboard result the user has seen, kept for reopening.

The dashboard is reproducible from (a, b, range, filters) as long as the analysed
data does not change. We still snapshot the payloads so an earlier result stays
readable exactly as it was, even after new reviews are scraped or analysed.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import logging
from typing import Any

from sqlalchemy import select

from rap.agg.load import Filters
from rap.db.models import Company, SavedComparison
from rap.db.session import session_scope
from rap.llm.summarize import cache_key

log = logging.getLogger(__name__)


def _jsonable(payload: Any) -> Any:
    return json.loads(json.dumps(payload, default=str))


def _filters_dict(filters: Filters | dict | None) -> dict[str, Any]:
    if filters is None:
        return dataclasses.asdict(Filters())
    if isinstance(filters, Filters):
        return dataclasses.asdict(filters)
    return dict(filters)


def _headline(summary: dict[str, Any] | None) -> str | None:
    if not summary:
        return None
    text = str(summary.get("executive_summary") or "").strip()
    if not text:
        diffs = summary.get("key_differentiators") or []
        text = str(diffs[0]) if diffs else ""
    return text[:400] or None


def record_comparison(
    a: str,
    b: str,
    *,
    compare_payload: dict[str, Any],
    summary: dict[str, Any] | None,
    frameworks: dict[str, Any],
    filters: Filters | dict | None,
) -> int | None:
    """Upsert a saved comparison for the payload just served. Returns the row id.

    A row is keyed by companies, range, filters and the compare hash, so
    revisiting the same unchanged comparison only bumps ``last_viewed_at``.
    """
    # only a real two-sided result is worth keeping; flipping through empty companies is not
    analysed_a = int(compare_payload["a"]["overview"].get("reviews_analysed") or 0)
    analysed_b = int(compare_payload["b"]["overview"].get("reviews_analysed") or 0)
    if analysed_a == 0 or analysed_b == 0:
        return None
    compare_json = _jsonable(compare_payload)
    filters_json = _jsonable(_filters_dict(filters))
    date_from = dt.date.fromisoformat(str(compare_json["date_from"]))
    date_to = dt.date.fromisoformat(str(compare_json["date_to"]))
    compare_hash = cache_key(compare_json)
    filters_key = cache_key(filters_json)
    snapshot = {
        "compare": compare_json,
        "summary": _jsonable(summary) if summary else None,
        **{k: _jsonable(v) for k, v in frameworks.items()},
    }
    now = dt.datetime.now(dt.UTC)
    with session_scope() as session:
        row = session.scalar(
            select(SavedComparison).where(
                SavedComparison.a_slug == a,
                SavedComparison.b_slug == b,
                SavedComparison.date_from == date_from,
                SavedComparison.date_to == date_to,
                SavedComparison.filters_key == filters_key,
                SavedComparison.compare_hash == compare_hash,
            )
        )
        if row is None:
            row = SavedComparison(
                a_slug=a,
                b_slug=b,
                date_from=date_from,
                date_to=date_to,
                filters=filters_json,
                filters_key=filters_key,
                compare_hash=compare_hash,
                snapshot=snapshot,
            )
            session.add(row)
        else:
            # same result seen again: refresh the narrative if regenerated, never drop one we have
            if snapshot["summary"] is None:
                snapshot["summary"] = (row.snapshot or {}).get("summary")
            row.snapshot = snapshot
        row.last_viewed_at = now
        row.n_a = int(compare_json["a"]["overview"].get("meta", {}).get("n_used") or 0)
        row.n_b = int(compare_json["b"]["overview"].get("meta", {}).get("n_used") or 0)
        row.sample = (
            compare_json.get("sample") if (compare_json.get("sample") or {}).get("used") else None
        )
        row.headline = _headline(snapshot["summary"]) or row.headline
        session.flush()
        return row.id


def _names(session, slugs: set[str]) -> dict[str, str]:
    rows = session.scalars(select(Company).where(Company.slug.in_(slugs))).all() if slugs else []
    return {c.slug: c.display_name for c in rows}


def _summary_row(row: SavedComparison, names: dict[str, str]) -> dict[str, Any]:
    compare = row.snapshot.get("compare") or {}
    data_as_of = compare.get("a", {}).get("overview", {}).get("meta", {}).get("data_as_of")
    return {
        "id": row.id,
        "a": row.a_slug,
        "b": row.b_slug,
        "a_name": names.get(row.a_slug, row.a_slug),
        "b_name": names.get(row.b_slug, row.b_slug),
        "date_from": row.date_from.isoformat(),
        "date_to": row.date_to.isoformat(),
        "title": row.title,
        "pinned": row.pinned,
        "n_a": row.n_a,
        "n_b": row.n_b,
        "sample": row.sample,
        "headline": row.headline,
        "has_summary": bool(row.snapshot.get("summary")),
        "data_as_of": data_as_of,
        "created_at": row.created_at.isoformat(),
        "last_viewed_at": row.last_viewed_at.isoformat(),
    }


def list_comparisons(limit: int = 200) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(
            select(SavedComparison)
            .order_by(SavedComparison.pinned.desc(), SavedComparison.last_viewed_at.desc())
            .limit(limit)
        ).all()
        names = _names(session, {r.a_slug for r in rows} | {r.b_slug for r in rows})
        return [_summary_row(r, names) for r in rows]


def get_comparison(saved_id: int, *, touch: bool = True) -> dict[str, Any] | None:
    with session_scope() as session:
        row = session.get(SavedComparison, saved_id)
        if row is None:
            return None
        if touch:
            row.last_viewed_at = dt.datetime.now(dt.UTC)
        names = _names(session, {row.a_slug, row.b_slug})
        out = _summary_row(row, names)
        out["filters"] = row.filters
        out["snapshot"] = row.snapshot
        return out


def update_comparison(
    saved_id: int, *, title: str | None = None, pinned: bool | None = None
) -> dict[str, Any] | None:
    with session_scope() as session:
        row = session.get(SavedComparison, saved_id)
        if row is None:
            return None
        if title is not None:
            row.title = title.strip()[:200] or None
        if pinned is not None:
            row.pinned = bool(pinned)
        names = _names(session, {row.a_slug, row.b_slug})
        session.flush()
        return _summary_row(row, names)


def delete_comparison(saved_id: int) -> bool:
    with session_scope() as session:
        row = session.get(SavedComparison, saved_id)
        if row is None:
            return False
        session.delete(row)
        return True
