from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from rap.db.models import Company, ReviewRaw


def company_ids_from_params(session: Session, params: dict[str, Any]) -> list[int] | None:
    if params.get("company_ids"):
        return [int(x) for x in params["company_ids"]]
    if params.get("company_id"):
        return [int(params["company_id"])]
    slugs = params.get("slugs")
    if slugs:
        return list(session.scalars(select(Company.id).where(Company.slug.in_(list(slugs)))))
    if params.get("company"):
        row = session.scalar(select(Company.id).where(Company.slug == params["company"]))
        return [row] if row is not None else []
    return None


def review_date_filters(params: dict[str, Any]) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if params.get("date_from"):
        start = dt.date.fromisoformat(str(params["date_from"]))
        filters.append(
            ReviewRaw.review_date
            >= dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc)
        )
    if params.get("date_to"):
        end = dt.date.fromisoformat(str(params["date_to"]))
        filters.append(
            ReviewRaw.review_date
            < dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
        )
    return filters


def apply_review_scope(query: Select, session: Session, params: dict[str, Any]) -> Select:
    ids = company_ids_from_params(session, params)
    if ids is not None:
        query = query.where(ReviewRaw.company_id.in_(ids))
    for clause in review_date_filters(params):
        query = query.where(clause)
    return query
