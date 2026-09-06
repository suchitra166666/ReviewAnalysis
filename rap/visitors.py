from __future__ import annotations

import datetime as dt
import re
from typing import Any

from sqlalchemy import func, select

from rap.db.models import SiteVisitor, SiteVisitorKey
from rap.db.session import session_scope
from rap.settings import decrypt_key, encrypt_key

VISITOR_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)
ONLINE_SECONDS = 90


def normalize_visitor_id(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if not VISITOR_RE.match(value):
        return None
    return value


def touch_visitor(visitor_id: str) -> SiteVisitor:
    now = dt.datetime.now(dt.timezone.utc)
    with session_scope() as session:
        row = session.get(SiteVisitor, visitor_id)
        if row is None:
            row = SiteVisitor(visitor_id=visitor_id, first_seen=now, last_seen=now)
            session.add(row)
        else:
            row.last_seen = now
        session.flush()
        session.expunge(row)
        return row


def traffic_counts() -> dict[str, int]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=ONLINE_SECONDS)
    with session_scope() as session:
        visited = int(session.scalar(select(func.count()).select_from(SiteVisitor)) or 0)
        online = int(
            session.scalar(select(func.count()).select_from(SiteVisitor).where(SiteVisitor.last_seen >= cutoff)) or 0
        )
    return {"visited": visited, "online": online}


def visitor_key_public(visitor_id: str) -> dict[str, dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(select(SiteVisitorKey).where(SiteVisitorKey.visitor_id == visitor_id)).all()
        return {
            row.provider_slug: {
                "has_key": True,
                "key_last4": row.key_last4,
                "last_verify_status": row.last_verify_status,
                "last_verified_at": row.last_verified_at.isoformat() if row.last_verified_at else None,
            }
            for row in rows
        }


def visitor_has_key(visitor_id: str) -> bool:
    with session_scope() as session:
        n = session.scalar(
            select(func.count()).select_from(SiteVisitorKey).where(SiteVisitorKey.visitor_id == visitor_id)
        ) or 0
    return int(n) > 0


def save_visitor_key(visitor_id: str, slug: str, api_key: str) -> None:
    touch_visitor(visitor_id)
    with session_scope() as session:
        row = session.scalar(
            select(SiteVisitorKey).where(
                SiteVisitorKey.visitor_id == visitor_id,
                SiteVisitorKey.provider_slug == slug,
            )
        )
        if row is None:
            row = SiteVisitorKey(visitor_id=visitor_id, provider_slug=slug)
            session.add(row)
        row.api_key_encrypted = encrypt_key(api_key)
        row.key_last4 = api_key[-4:]
        row.last_verify_status = None
        row.last_verified_at = None


def mark_visitor_verify(visitor_id: str, slug: str, status: str) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    with session_scope() as session:
        row = session.scalar(
            select(SiteVisitorKey).where(
                SiteVisitorKey.visitor_id == visitor_id,
                SiteVisitorKey.provider_slug == slug,
            )
        )
        if row is None:
            return
        row.last_verify_status = status
        row.last_verified_at = now


def decrypt_visitor_key(visitor_id: str, slug: str) -> str | None:
    with session_scope() as session:
        row = session.scalar(
            select(SiteVisitorKey).where(
                SiteVisitorKey.visitor_id == visitor_id,
                SiteVisitorKey.provider_slug == slug,
            )
        )
        if row is None:
            return None
        return decrypt_key(row.api_key_encrypted)
