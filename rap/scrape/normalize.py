from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedReview:
    store: str
    store_review_id: str
    review_date: dt.datetime
    star_rating: int
    title: str | None
    body: str
    author_name: str | None
    app_version: str | None
    thumbs_up: int | None
    reply_body: str | None
    reply_date: dt.datetime | None
    language_hint: str | None
    raw_json: dict[str, Any] = field(default_factory=dict)


def parse_datetime(value: Any) -> dt.datetime | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)
    if isinstance(value, (int, float)):
        # Play Store often returns milliseconds
        seconds = value / 1000 if value > 10_000_000_000 else value
        return dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = dt.datetime.strptime(text.replace("Z", "+0000") if "%z" in fmt else text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            continue
    try:
        from dateutil import parser as date_parser

        parsed = date_parser.parse(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def guess_language(text: str) -> str | None:
    if not text:
        return None
    arabic = sum(1 for ch in text if "\u0600" <= ch <= "\u06FF")
    latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    if arabic and latin:
        return "mixed"
    if arabic:
        return "ar"
    if latin:
        return "en"
    return "other"


def to_jsonable(value: Any) -> Any:
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def dedupe_reviews(rows: list[NormalizedReview]) -> list[NormalizedReview]:
    seen: set[tuple[str, str]] = set()
    out: list[NormalizedReview] = []
    for row in rows:
        key = (row.store, row.store_review_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def should_stop_incremental(page_ids: list[str], seen_ids: set[str], full: bool) -> bool:
    if full or not page_ids:
        return False
    return all(rid in seen_ids for rid in page_ids)
