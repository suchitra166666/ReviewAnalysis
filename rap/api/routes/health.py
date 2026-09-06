from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from sqlalchemy import func, select, text

from rap.db.models import ApiCredential, Job, JobStatus
from rap.db.session import session_scope
from rap.jobs.worker import last_heartbeat

router = APIRouter()


@router.get("/health")
def health() -> dict:
    db = "ok"
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
            providers = [{"slug": row.provider_slug} for row in session.scalars(select(ApiCredential))]
    except Exception as exc:
        db = f"error: {exc}"
        providers = []
    seen = last_heartbeat()
    worker = "missing"
    if seen:
        now = dt.datetime.now(dt.timezone.utc)
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=dt.timezone.utc)
        worker = "ok" if (now - seen).total_seconds() < 90 else "stale"
    if worker != "ok":
        try:
            with session_scope() as session:
                running = session.scalar(
                    select(func.count()).select_from(Job).where(Job.status == JobStatus.running)
                ) or 0
            if running:
                worker = "ok"
        except Exception:
            pass
    return {"db": db, "worker": worker, "providers": providers}
