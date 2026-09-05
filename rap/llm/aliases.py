from __future__ import annotations

from sqlalchemy import select

from rap.db.models import Company
from rap.db.session import session_scope


def alias_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with session_scope() as session:
        for company in session.scalars(select(Company).where(Company.hidden.is_(False))):
            mapping[company.slug.lower()] = company.slug
            mapping[company.display_name.lower()] = company.slug
            for alias in company.aliases or []:
                mapping[alias.lower()] = company.slug
    return mapping


def resolve_competitor(raw: str, mapping: dict[str, str] | None = None) -> str:
    mapping = mapping or alias_map()
    key = raw.strip().lower()
    if key in mapping:
        return mapping[key]
    for alias, slug in mapping.items():
        if alias and alias in key:
            return slug
    return "unknown"


def attach_slugs(mentions: list[dict], mapping: dict[str, str] | None = None) -> list[dict]:
    mapping = mapping or alias_map()
    out = []
    for item in mentions:
        row = dict(item)
        row["competitor_slug"] = resolve_competitor(str(row.get("competitor_raw") or ""), mapping)
        out.append(row)
    return out
