from __future__ import annotations

import datetime as dt
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from rap.agg.themes import journey_for
from rap.agg.weights import WeightResult, counts_from, star_weights
from rap.db.models import Company, ReviewFinal, ReviewFlag, ReviewRaw, ReviewTranslation
from rap.db.session import session_scope
from rap.settings import get_setting


@dataclass
class Filters:
    exclude_flagged: bool = True
    food_related_only: bool = True
    languages: list[str] | None = None
    stars: list[int] | None = None
    weighted: bool = True


@dataclass
class LoadedReview:
    raw: ReviewRaw
    final: ReviewFinal | None
    flag: ReviewFlag | None
    translation: ReviewTranslation | None
    used: bool
    weight: float


@dataclass
class CompanySlice:
    company: Company
    date_from: dt.date
    date_to: dt.date
    filters: Filters
    raw: list[ReviewRaw]
    loaded: list[LoadedReview]
    weights: WeightResult
    n_raw: int
    n_used: int
    data_as_of: dt.datetime
    low_confidence: bool


def parse_filters(raw: dict[str, Any] | None) -> Filters:
    raw = raw or {}
    return Filters(
        exclude_flagged=bool(raw.get("exclude_flagged", True)),
        food_related_only=bool(raw.get("food_related_only", True)),
        languages=raw.get("languages"),
        stars=raw.get("stars"),
        weighted=bool(raw.get("weighted", True)),
    )


def resolve_company(session: Session, ident: str | int) -> Company:
    if isinstance(ident, int) or (isinstance(ident, str) and ident.isdigit()):
        company = session.get(Company, int(ident))
    else:
        company = session.scalar(select(Company).where(Company.slug == ident))
    if company is None:
        raise KeyError(f"Unknown company: {ident}")
    return company


def resolve_range(
    a: Company,
    b: Company | None,
    date_from: dt.date | str | None,
    date_to: dt.date | str | None,
    since_launch: bool,
) -> tuple[dt.date, dt.date]:
    today = dt.datetime.now(dt.timezone.utc).date()
    end = _as_date(date_to) or today
    start = _as_date(date_from)
    if since_launch:
        dates = [c.launch_date_ae for c in (a, b) if c and c.launch_date_ae]
        if dates:
            start = max(dates)
    if start is None:
        start = end - dt.timedelta(days=90)
    return start, end


def _as_date(value: dt.date | str | None) -> dt.date | None:
    if value is None:
        return None
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


_SLICE_TTL_SECONDS = 30.0
_slice_cache: dict[tuple, tuple[float, CompanySlice]] = {}


def clear_slice_cache() -> None:
    _slice_cache.clear()


def _slice_key(ident, date_from, date_to, filt: Filters, since_launch: bool, other) -> tuple:
    return (
        str(ident),
        str(date_from),
        str(date_to),
        filt.exclude_flagged,
        filt.food_related_only,
        tuple(filt.languages or ()),
        tuple(filt.stars or ()),
        filt.weighted,
        bool(since_launch),
        str(other),
    )


def load_slice(
    ident: str | int,
    date_from: dt.date | str | None,
    date_to: dt.date | str | None,
    filters: Filters | dict | None = None,
    since_launch: bool = False,
    other: str | int | None = None,
) -> CompanySlice:
    filt = filters if isinstance(filters, Filters) else parse_filters(filters)
    key = _slice_key(ident, date_from, date_to, filt, since_launch, other)
    now = time.monotonic()
    hit = _slice_cache.get(key)
    if hit and now - hit[0] < _SLICE_TTL_SECONDS:
        return hit[1]
    result = _load_slice_uncached(ident, date_from, date_to, filt, since_launch, other)
    if len(_slice_cache) > 64:
        stale = [k for k, (ts, _) in _slice_cache.items() if now - ts >= _SLICE_TTL_SECONDS]
        for k in stale:
            _slice_cache.pop(k, None)
        if len(_slice_cache) > 64:
            _slice_cache.clear()
    _slice_cache[key] = (now, result)
    return result


def _load_slice_uncached(
    ident: str | int,
    date_from: dt.date | str | None,
    date_to: dt.date | str | None,
    filt: Filters,
    since_launch: bool,
    other: str | int | None,
) -> CompanySlice:
    with session_scope() as session:
        company = resolve_company(session, ident)
        other_c = resolve_company(session, other) if other is not None else None
        start, end = resolve_range(company, other_c, date_from, date_to, since_launch)
        start_dt = dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc)
        end_dt = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
        raw_rows = list(
            session.scalars(
                select(ReviewRaw).where(
                    ReviewRaw.company_id == company.id,
                    ReviewRaw.review_date >= start_dt,
                    ReviewRaw.review_date < end_dt,
                )
            )
        )
        ids = [r.id for r in raw_rows]
        finals = {
            r.review_id: r
            for r in session.scalars(select(ReviewFinal).where(ReviewFinal.review_id.in_(ids)))
        } if ids else {}
        flags = {
            r.review_id: r
            for r in session.scalars(select(ReviewFlag).where(ReviewFlag.review_id.in_(ids)))
        } if ids else {}
        translations = {
            r.review_id: r
            for r in session.scalars(select(ReviewTranslation).where(ReviewTranslation.review_id.in_(ids)))
        } if ids else {}
        food_only = filt.food_related_only and company.is_super_app
        loaded: list[LoadedReview] = []
        used_stars: list[int] = []
        for raw in raw_rows:
            final = finals.get(raw.id)
            flag = flags.get(raw.id)
            used = final is not None
            if used and filt.exclude_flagged and flag and flag.excluded_from_aggregates:
                used = False
            if used and food_only and final and final.is_food_related is False:
                used = False
            if used and filt.languages and final and final.language not in filt.languages:
                used = False
            if used and filt.stars and raw.star_rating not in filt.stars:
                used = False
            if used:
                used_stars.append(raw.star_rating)
            loaded.append(
                LoadedReview(
                    raw=raw,
                    final=final,
                    flag=flag,
                    translation=translations.get(raw.id),
                    used=used,
                    weight=1.0,
                )
            )
        true_stars = counts_from([r.star_rating for r in raw_rows])
        sample_stars = counts_from(used_stars)
        weights = star_weights(true_stars, sample_stars)
        for item in loaded:
            if item.used:
                item.weight = weights.weights.get(item.raw.star_rating, 1.0) if filt.weighted else 1.0
        n_used = sum(1 for x in loaded if x.used)
        min_n = int(get_setting("aggregation.min_n", 50) or 50)
        for obj in (*raw_rows, *finals.values(), *flags.values(), *translations.values()):
            session.expunge(obj)
        session.expunge(company)
        data_as_of = max((r.scraped_at for r in raw_rows), default=dt.datetime.now(dt.timezone.utc))
        return CompanySlice(
            company=company,
            date_from=start,
            date_to=end,
            filters=filt,
            raw=raw_rows,
            loaded=loaded,
            weights=weights,
            n_raw=len(raw_rows),
            n_used=n_used,
            data_as_of=data_as_of,
            low_confidence=n_used < min_n,
        )


def used(slice_: CompanySlice) -> list[LoadedReview]:
    return [x for x in slice_.loaded if x.used]


def mention_rows(slice_: CompanySlice, sentiment: str | None = None) -> list[tuple[LoadedReview, dict]]:
    out: list[tuple[LoadedReview, dict]] = []
    for item in used(slice_):
        if not item.final:
            continue
        for mention in item.final.mentions or []:
            if sentiment and mention.get("sentiment") != sentiment:
                continue
            out.append((item, mention))
    return out


def snippet_obj(item: LoadedReview, mention: dict | None = None) -> dict[str, Any]:
    language = (item.final.language if item.final else item.raw.language_hint) or "en"
    if mention:
        text = mention.get("snippet") or item.raw.body
        text_en = mention.get("snippet_en")
    else:
        text = item.raw.body
        text_en = item.translation.body_en if item.translation else None
    if language == "en":
        text_en = None
    elif not text_en and item.translation:
        text_en = item.translation.body_en
    return {
        "text": text,
        "text_en": text_en,
        "language": language,
        "review_id": item.raw.id,
        "stars": item.raw.star_rating,
        "date": item.raw.review_date.date().isoformat(),
    }


def store_url(item: LoadedReview) -> str | None:
    company = None
    # built from raw store + company ids when available
    if item.raw.store.value == "play":
        return None
    return None


def journey_of(mention: dict) -> str | None:
    return journey_for(mention.get("theme") or "other", mention.get("sub_theme"))
