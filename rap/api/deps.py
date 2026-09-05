from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import Query

from rap.agg.load import Filters


def common_filters(
    exclude_flagged: bool = Query(True),
    food_related_only: bool = Query(True),
    weighted: bool = Query(True),
    languages: str | None = Query(None),
    stars: str | None = Query(None),
    date_from: dt.date | None = Query(None),
    date_to: dt.date | None = Query(None),
    since_launch: bool = Query(False),
) -> dict[str, Any]:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "since_launch": since_launch,
        "filters": Filters(
            exclude_flagged=exclude_flagged,
            food_related_only=food_related_only,
            weighted=weighted,
            languages=languages.split(",") if languages else None,
            stars=[int(x) for x in stars.split(",")] if stars else None,
        ),
    }
