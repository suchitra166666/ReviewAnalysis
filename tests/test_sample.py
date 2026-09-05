from __future__ import annotations

import datetime as dt
import random
from types import SimpleNamespace

from rap.llm.sample import star_balanced_sample


def _row(rid: int, company_id: int, stars: int, day: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=rid,
        company_id=company_id,
        star_rating=stars,
        review_date=dt.datetime(2026, 6, day, tzinfo=dt.timezone.utc),
    )


def test_equal_share_per_star_and_company() -> None:
    rows = []
    n = 1
    for company in (1, 2):
        for star in (1, 2, 3, 4, 5):
            for day in range(1, 11):
                rows.append(_row(n, company, star, day))
                n += 1
    picked = star_balanced_sample(rows, sample_per_star=4, already_ids=set(), rng=random.Random(0))
    assert len(picked) == 40
    by = {}
    for row in picked:
        by.setdefault(row.company_id, {}).setdefault(row.star_rating, 0)
        by[row.company_id][row.star_rating] += 1
    assert by[1] == {1: 4, 2: 4, 3: 4, 4: 4, 5: 4}
    assert by[2] == {1: 4, 2: 4, 3: 4, 4: 4, 5: 4}


def test_keeps_already_sampled_and_adds() -> None:
    rows = [_row(i, 1, 5, i) for i in range(1, 8)]
    first = star_balanced_sample(rows, sample_per_star=2, already_ids=set(), rng=random.Random(1))
    assert len(first) == 2
    kept = {row.id for row in first}
    second = star_balanced_sample(rows, sample_per_star=4, already_ids=kept, rng=random.Random(2))
    assert kept <= {row.id for row in second}
    assert len(second) == 4


def test_short_bucket_uses_most_recent() -> None:
    rows = [_row(1, 1, 1, 1), _row(2, 1, 1, 10), _row(3, 1, 1, 5)]
    picked = star_balanced_sample(rows, sample_per_star=10, already_ids=set(), rng=random.Random(0))
    assert [row.id for row in picked] == [2, 3, 1]
