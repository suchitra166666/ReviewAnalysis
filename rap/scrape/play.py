from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from rap.scrape.normalize import (
    NormalizedReview,
    guess_language,
    parse_datetime,
    should_stop_incremental,
)

PlayPageFn = Callable[[str, str, str, Any | None, int], tuple[list[dict[str, Any]], Any | None]]


def parse_play_review(raw: dict[str, Any], language_hint: str | None = None) -> NormalizedReview:
    review_id = str(raw.get("reviewId") or raw.get("id") or "")
    body = str(raw.get("content") or raw.get("body") or "")
    title = raw.get("title") or None
    at = parse_datetime(raw.get("at") or raw.get("date") or raw.get("reviewDate"))
    if at is None:
        at = parse_datetime("1970-01-01") or __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )
    reply = raw.get("replyContent") or raw.get("reply_body")
    reply_at = parse_datetime(raw.get("repliedAt") or raw.get("replyDate"))
    score = int(raw.get("score") or raw.get("star_rating") or 0)
    return NormalizedReview(
        store="play",
        store_review_id=review_id,
        review_date=at,
        star_rating=score,
        title=title,
        body=body,
        author_name=raw.get("userName") or raw.get("author"),
        app_version=raw.get("reviewCreatedVersion") or raw.get("app_version"),
        thumbs_up=raw.get("thumbsUpCount") if raw.get("thumbsUpCount") is not None else raw.get("thumbs_up"),
        reply_body=reply,
        reply_date=reply_at,
        language_hint=language_hint or guess_language(f"{title or ''} {body}"),
        raw_json=raw,
    )


def default_play_fetch(
    package: str, country: str, lang: str, token: Any | None, count: int
) -> tuple[list[dict[str, Any]], Any | None]:
    from google_play_scraper import Sort, reviews

    result, continuation = reviews(
        package,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=count,
        continuation_token=token,
    )
    return list(result or []), continuation


def fetch_play_reviews(
    package: str,
    *,
    country: str,
    languages: list[str],
    delay_seconds: float,
    max_pages: int,
    seen_ids: set[str],
    full: bool = False,
    page_size: int = 200,
    fetch_page: PlayPageFn | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    on_page: Callable[[list[NormalizedReview]], None] | None = None,
) -> tuple[list[NormalizedReview], int]:
    fetch_page = fetch_page or default_play_fetch
    sleep_fn = sleep_fn or time.sleep
    collected: list[NormalizedReview] = []
    pages = 0
    for lang in languages:
        token: Any | None = None
        for _ in range(max_pages):
            raw_page, token = fetch_page(package, country, lang, token, page_size)
            pages += 1
            page_ids: list[str] = []
            page_parsed: list[NormalizedReview] = []
            for raw in raw_page:
                parsed = parse_play_review(raw, language_hint=lang)
                if not parsed.store_review_id:
                    continue
                page_ids.append(parsed.store_review_id)
                page_parsed.append(parsed)
                collected.append(parsed)
            if on_page and page_parsed:
                on_page(page_parsed)
            if should_stop_incremental(page_ids, seen_ids, full):
                break
            if not token or not raw_page:
                break
            if delay_seconds > 0:
                sleep_fn(delay_seconds)
    return collected, pages
