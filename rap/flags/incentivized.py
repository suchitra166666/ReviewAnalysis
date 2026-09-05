from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from rap.db.models import ReviewEmbedding, ReviewFinal, ReviewFlag, ReviewRaw
from rap.db.scope import apply_review_scope
from rap.db.session import session_scope
from rap.settings import get_setting

ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def burst_days(dates: list[dt.date], window: int = 30, min_n: int = 20) -> set[dt.date]:
    if len(dates) < min_n:
        return set()
    counts: dict[dt.date, int] = defaultdict(int)
    for day in dates:
        counts[day] += 1
    flagged: set[dt.date] = set()
    ordered = sorted(counts)
    for day in ordered:
        prior = [counts[d] for d in ordered if (day - d).days <= window and d < day]
        if len(prior) < 7:
            continue
        mean = sum(prior) / len(prior)
        var = sum((x - mean) ** 2 for x in prior) / len(prior)
        std = math.sqrt(var)
        if counts[day] > mean + 3 * std and sum(prior) + counts[day] >= min_n:
            flagged.add(day)
    return flagged


def run_flags(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
) -> dict[str, Any]:
    threshold = float(get_setting("aggregation.duplicate_similarity_threshold", 0.92) or 0.92)
    excl_thresh = float(get_setting("aggregation.incentivized_exclusion_threshold", 0.6) or 0.6)
    weights = get_setting("aggregation.incentivized_weights") or {
        "mentions_incentive": 0.5,
        "near_duplicate": 0.3,
        "burst": 0.1,
        "five_star_low_info": 0.1,
    }
    with session_scope() as session:
        q = apply_review_scope(
            select(ReviewRaw, ReviewFinal, ReviewEmbedding)
            .join(ReviewFinal, ReviewFinal.review_id == ReviewRaw.id)
            .outerjoin(ReviewEmbedding, ReviewEmbedding.review_id == ReviewRaw.id),
            session,
            params,
        )
        rows = list(session.execute(q).all())
        for raw, final, emb in rows:
            session.expunge(raw)
            session.expunge(final)
            if emb is not None:
                session.expunge(emb)

    by_company: dict[int, list[tuple]] = defaultdict(list)
    for raw, final, emb in rows:
        by_company[raw.company_id].append((raw, final, emb))

    written = 0
    total = len(rows)
    for company_id, group in by_company.items():
        if should_cancel and should_cancel():
            break
        dates = [r.review_date.date() for r, _, _ in group]
        bursts = burst_days(dates)
        # near-duplicates: compare embeddings within company, earlier date wins
        candidates = [
            (raw, emb.embedding)
            for raw, _final, emb in group
            if emb is not None and len((raw.body or "")) >= 25
        ]
        dup_of: dict[int, tuple[int, float]] = {}
        for i, (raw_i, vec_i) in enumerate(candidates):
            best: tuple[int, float] | None = None
            for raw_j, vec_j in candidates[:i]:
                if raw_j.review_date >= raw_i.review_date:
                    continue
                sim = cosine(list(vec_i), list(vec_j))
                if sim >= threshold and (best is None or sim > best[1]):
                    best = (raw_j.id, sim)
            if best:
                dup_of[raw_i.id] = best

        with session_scope() as session:
            for raw, final, _emb in group:
                near = dup_of.get(raw.id)
                is_dup = near is not None
                is_burst = raw.review_date.date() in bursts
                five_low = raw.star_rating == 5 and bool(final.low_information)
                score = (
                    float(weights.get("mentions_incentive", 0.5)) * (1.0 if final.mentions_incentive else 0.0)
                    + float(weights.get("near_duplicate", 0.3)) * (1.0 if is_dup else 0.0)
                    + float(weights.get("burst", 0.1)) * (1.0 if is_burst else 0.0)
                    + float(weights.get("five_star_low_info", 0.1)) * (1.0 if five_low else 0.0)
                )
                reasons: list[str] = []
                if final.low_information:
                    reasons.append("low_information")
                if final.rating_text_mismatch:
                    reasons.append("rating_text_mismatch")
                if not final.schema_valid:
                    reasons.append("schema_invalid")
                if score >= excl_thresh:
                    reasons.append("incentivized")
                session.merge(
                    ReviewFlag(
                        review_id=raw.id,
                        near_duplicate_of=near[0] if near else None,
                        dup_similarity=near[1] if near else None,
                        burst_flag=is_burst,
                        incentivized_score=score,
                        excluded_from_aggregates=bool(reasons),
                        exclusion_reasons=reasons,
                    )
                )
                written += 1
        if progress:
            progress(written, total, f"flags company {company_id}")
    return {"written": written}
