from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from rap.scrape.normalize import (
    NormalizedReview,
    guess_language,
    parse_datetime,
    should_stop_incremental,
)

RssPageFn = Callable[[str, str, int], list[dict[str, Any]]]
LibPageFn = Callable[[str, str, int], list[dict[str, Any]]]


def parse_appstore_review(raw: dict[str, Any]) -> NormalizedReview:
    review_id = str(
        raw.get("id")
        or raw.get("review_id")
        or (raw.get("id", {}) or {}).get("label")
        or ""
    )
    if isinstance(raw.get("id"), dict):
        review_id = str(raw["id"].get("label") or "")
    title = _label(raw.get("title"))
    body = _label(raw.get("content") or raw.get("review") or raw.get("body"))
    rating_raw = raw.get("rating") or _label(raw.get("im:rating")) or 0
    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        rating = 0
    author = raw.get("userName") or raw.get("author")
    if isinstance(author, dict):
        author = _label(author.get("name"))
    updated = parse_datetime(
        raw.get("date") or raw.get("updated") or _label(raw.get("updated"))
    )
    if updated is None:
        import datetime as dt

        updated = dt.datetime.now(dt.timezone.utc)
    version = raw.get("version") or _label(raw.get("im:version"))
    return NormalizedReview(
        store="appstore",
        store_review_id=review_id,
        review_date=updated,
        star_rating=rating,
        title=title,
        body=body or "",
        author_name=str(author) if author else None,
        app_version=str(version) if version else None,
        thumbs_up=None,
        reply_body=raw.get("developerResponse") or raw.get("reply_body"),
        reply_date=parse_datetime(raw.get("reply_date")),
        language_hint=guess_language(f"{title or ''} {body or ''}"),
        raw_json=raw,
    )


def _label(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("label")
    return str(value)


def default_lib_fetch(app_id: str, country: str, how_many: int) -> list[dict[str, Any]]:
    from app_store_scraper import AppStore

    app = AppStore(country=country, app_name="app", app_id=app_id)
    app.review(how_many=how_many)
    return list(app.reviews or [])


def default_rss_fetch(app_id: str, country: str, page: int) -> list[dict[str, Any]]:
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews/"
        f"page={page}/id={app_id}/sortby=mostrecent/json"
    )
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code in {400, 404}:
            return []
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            return []
    entries = payload.get("feed", {}).get("entry", [])
    if not entries:
        return []
    # First entry is often the app metadata
    reviews = []
    for entry in entries:
        if "im:rating" not in entry and "rating" not in entry:
            continue
        reviews.append(entry)
    return reviews


def fetch_appstore_reviews(
    app_id: str,
    *,
    country: str,
    delay_seconds: float,
    max_pages: int,
    seen_ids: set[str],
    full: bool = False,
    page_size: int = 50,
    lib_fetch: LibPageFn | None = None,
    rss_fetch: RssPageFn | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> tuple[list[NormalizedReview], int]:
    sleep_fn = sleep_fn or time.sleep
    pages = 0
    collected: list[NormalizedReview] = []

    lib_error: str | None = None
    try:
        raw_rows = (lib_fetch or default_lib_fetch)(app_id, country, max_pages * page_size)
        pages += 1
        page_ids: list[str] = []
        for raw in raw_rows:
            parsed = parse_appstore_review(raw)
            if not parsed.store_review_id:
                continue
            page_ids.append(parsed.store_review_id)
            collected.append(parsed)
        if collected and not should_stop_incremental(page_ids, seen_ids, full):
            return collected, pages
        if collected:
            return collected, pages
    except Exception as exc:
        lib_error = str(exc)

    rss_fetch = rss_fetch or default_rss_fetch
    for page in range(1, max_pages + 1):
        raw_page = rss_fetch(app_id, country, page)
        pages += 1
        page_ids = []
        for raw in raw_page:
            parsed = parse_appstore_review(raw)
            if not parsed.store_review_id:
                continue
            page_ids.append(parsed.store_review_id)
            collected.append(parsed)
        if should_stop_incremental(page_ids, seen_ids, full):
            break
        if not raw_page:
            break
        if delay_seconds > 0:
            sleep_fn(delay_seconds)
    if not collected and lib_error:
        raise RuntimeError(f"App Store scraper failed and RSS was empty: {lib_error}")
    return collected, pages
