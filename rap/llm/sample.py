from __future__ import annotations

import random
from collections import defaultdict

from rap.db.models import ReviewRaw


def uses_sample(params: dict | None) -> bool:
    params = params or {}
    return bool(params.get("sample_per_star") or params.get("sample_n"))

STARS = (1, 2, 3, 4, 5)


def star_balanced_sample(
    rows: list[ReviewRaw],
    *,
    sample_per_star: int,
    already_ids: set[int],
    rng: random.Random | None = None,
) -> list[ReviewRaw]:
    """Per company, take up to sample_per_star reviews in each star bucket.

    Already-sampled ids are kept. New picks are random within a bucket, or the
    most recent reviews if the bucket is smaller than the remaining quota.
    """
    rng = rng or random.Random()
    by_company: dict[int, dict[int, list[ReviewRaw]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        star = int(row.star_rating or 0)
        if star in STARS:
            by_company[row.company_id][star].append(row)

    picked: list[ReviewRaw] = []
    for stars in by_company.values():
        for star in STARS:
            bucket = list(stars.get(star) or [])
            kept = [row for row in bucket if row.id in already_ids]
            need = max(int(sample_per_star) - len(kept), 0)
            pool = [row for row in bucket if row.id not in already_ids]
            pool.sort(key=lambda row: row.review_date, reverse=True)
            if len(pool) <= need:
                extra = pool
            else:
                extra = rng.sample(pool, need)
            picked.extend(kept + extra)
    return picked
