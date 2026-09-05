from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from rap.db.models import Company, ReviewRaw, ScrapeRun, ScrapeStatusEnum, StoreEnum
from rap.db.session import session_scope
from rap.scrape.appstore import fetch_appstore_reviews
from rap.scrape.normalize import NormalizedReview, dedupe_reviews, to_jsonable
from rap.scrape.play import fetch_play_reviews
from rap.settings import get_setting


def seen_store_ids(session: Session, store: StoreEnum) -> set[str]:
    rows = session.scalars(
        select(ReviewRaw.store_review_id).where(ReviewRaw.store == store)
    ).all()
    return set(rows)


def persist_reviews(
    session: Session,
    company_id: int,
    run_id: int,
    reviews: list[NormalizedReview],
) -> int:
    if not reviews:
        return 0
    rows = [
        {
            "company_id": company_id,
            "store": StoreEnum(r.store),
            "store_review_id": r.store_review_id,
            "review_date": r.review_date,
            "star_rating": r.star_rating,
            "title": r.title,
            "body": r.body,
            "author_name": r.author_name,
            "app_version": r.app_version,
            "thumbs_up": r.thumbs_up,
            "reply_body": r.reply_body,
            "reply_date": r.reply_date,
            "language_hint": r.language_hint,
            "raw_json": to_jsonable(r.raw_json) if r.raw_json else {},
            "scrape_run_id": run_id,
        }
        for r in reviews
        if r.store_review_id
    ]
    if not rows:
        return 0
    stmt = (
        insert(ReviewRaw)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_reviews_raw_store_id")
        .returning(ReviewRaw.id)
    )
    result = session.execute(stmt)
    return len(result.all())


def _company_by_slug(session: Session, slug: str) -> Company:
    company = session.scalar(select(Company).where(Company.slug == slug, Company.hidden.is_(False)))
    if company is None:
        raise KeyError(f"Unknown company slug: {slug}")
    return company


def run_scrape(
    *,
    slugs: list[str],
    stores: list[str],
    full: bool = False,
    progress: Callable[[str], None] | None = None,
    play_fetch: Any | None = None,
    appstore_lib: Any | None = None,
    appstore_rss: Any | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> list[dict[str, Any]]:
    delay = float(get_setting("scraping.delay_seconds", 1.5) or 1.5)
    max_pages = int(get_setting("scraping.max_pages_per_run", 50) or 50)
    country = str(get_setting("scraping.country_code", "ae") or "ae")
    languages = list(get_setting("scraping.languages", ["en", "ar"]) or ["en", "ar"])
    results: list[dict[str, Any]] = []

    with session_scope() as session:
        companies = [_company_by_slug(session, slug) for slug in slugs]
        company_ids = [(c.id, c.slug, c.appstore_id, c.play_package) for c in companies]

    for company_id, slug, appstore_id, play_package in company_ids:
        for store in stores:
            if progress:
                progress(f"Scraping {slug} / {store}")
            summary = _run_one(
                company_id=company_id,
                slug=slug,
                store=store,
                appstore_id=appstore_id,
                play_package=play_package,
                country=country,
                languages=languages,
                delay=delay,
                max_pages=max_pages,
                full=full,
                play_fetch=play_fetch,
                appstore_lib=appstore_lib,
                appstore_rss=appstore_rss,
                sleep_fn=sleep_fn,
                progress=progress,
            )
            results.append(summary)
    return results


def _run_one(
    *,
    company_id: int,
    slug: str,
    store: str,
    appstore_id: str | None,
    play_package: str | None,
    country: str,
    languages: list[str],
    delay: float,
    max_pages: int,
    full: bool,
    play_fetch: Any | None,
    appstore_lib: Any | None,
    appstore_rss: Any | None,
    sleep_fn: Callable[[float], None] | None,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    store_enum = StoreEnum(store)
    started = dt.datetime.now(dt.timezone.utc)
    with session_scope() as session:
        run = ScrapeRun(
            company_id=company_id,
            store=store_enum,
            started_at=started,
            status=ScrapeStatusEnum.running,
        )
        session.add(run)
        session.flush()
        run_id = run.id
        seen = seen_store_ids(session, store_enum)

    new_count = 0
    pages = 0
    error: str | None = None
    status = ScrapeStatusEnum.ok
    try:
        if store_enum == StoreEnum.play:
            if not play_package:
                raise RuntimeError(f"{slug} has no Play package")
            def persist_page(batch: list[NormalizedReview]) -> None:
                nonlocal new_count
                with session_scope() as session:
                    added = persist_reviews(session, company_id, run_id, dedupe_reviews(batch))
                    new_count += added
                if progress and added:
                    progress(f"{slug}/{store}: +{added} ({new_count} new)")

            reviews, pages = fetch_play_reviews(
                play_package,
                country=country,
                languages=languages,
                delay_seconds=delay,
                max_pages=max_pages,
                seen_ids=seen,
                full=full,
                fetch_page=play_fetch,
                sleep_fn=sleep_fn,
                on_page=persist_page,
            )
        else:
            if not appstore_id:
                raise RuntimeError(f"{slug} has no App Store ID")
            reviews, pages = fetch_appstore_reviews(
                appstore_id,
                country=country,
                delay_seconds=delay,
                max_pages=max_pages,
                seen_ids=seen,
                full=full,
                lib_fetch=appstore_lib,
                rss_fetch=appstore_rss,
                sleep_fn=sleep_fn,
            )
            reviews = dedupe_reviews(reviews)
            chunk = 400
            with session_scope() as session:
                for i in range(0, len(reviews), chunk):
                    new_count += persist_reviews(
                        session, company_id, run_id, reviews[i : i + chunk]
                    )
        if progress:
            progress(f"{slug}/{store}: {new_count} new, {pages} pages")
    except Exception as exc:
        error = str(exc)
        status = ScrapeStatusEnum.failed
        if progress:
            progress(f"{slug}/{store} failed: {exc}")

    with session_scope() as session:
        run = session.get(ScrapeRun, run_id)
        if run:
            run.finished_at = dt.datetime.now(dt.timezone.utc)
            run.status = status
            run.new_reviews = new_count
            run.pages_fetched = pages
            run.error = error

    return {
        "company": slug,
        "store": store,
        "run_id": run_id,
        "new_reviews": new_count,
        "pages_fetched": pages,
        "status": status.value,
        "error": error,
    }
