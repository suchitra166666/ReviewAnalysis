from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from rap.db.models import Job, JobKind, JobStatus, LlmCall
from rap.db.session import session_scope
from rap.settings import get_setting


class CostCapExceeded(Exception):
    def __init__(self, estimate: float, cap: float) -> None:
        self.estimate = estimate
        self.cap = cap
        super().__init__(
            f"Estimated cost ${estimate:.2f} exceeds the max run cap of ${cap:.2f}."
        )


class ConfirmationRequired(Exception):
    def __init__(self, estimate: float, threshold: float) -> None:
        self.estimate = estimate
        self.threshold = threshold
        super().__init__(
            f"Estimated cost ${estimate:.2f} is above the confirmation threshold of ${threshold:.2f}."
        )


def estimate_job(kind: JobKind | str, params: dict[str, Any]) -> float:
    from rap.jobs.estimators import estimate

    return estimate(JobKind(kind) if isinstance(kind, str) else kind, params)


def create_job(
    kind: JobKind | str,
    params: dict[str, Any] | None = None,
    *,
    created_by: str | None = None,
    confirm: bool = False,
    dry_run: bool = False,
) -> Job:
    kind_enum = JobKind(kind) if isinstance(kind, str) else kind
    params = params or {}
    estimate = estimate_job(kind_enum, params)
    cap = float(get_setting("costs.max_run_cost_usd", 25) or 25)
    threshold = float(get_setting("costs.require_confirmation_above_usd", 5) or 5)
    if estimate > cap:
        raise CostCapExceeded(estimate, cap)
    if estimate > threshold and not confirm and not dry_run:
        raise ConfirmationRequired(estimate, threshold)
    if dry_run:
        job = Job(
            kind=kind_enum,
            params=params,
            status=JobStatus.queued,
            progress={"done": 0, "total": 0, "stage": "dry_run"},
            est_cost_usd=estimate,
            actual_cost_usd=0.0,
            log=f"dry-run estimate ${estimate:.4f}\n",
            created_by=created_by,
        )
        return job
    with session_scope() as session:
        job = Job(
            kind=kind_enum,
            params=params,
            status=JobStatus.queued,
            progress={"done": 0, "total": 0, "stage": "queued"},
            est_cost_usd=estimate,
            actual_cost_usd=0.0,
            log="",
            created_by=created_by,
        )
        session.add(job)
        session.flush()
        session.refresh(job)
        session.expunge(job)
        return job


def get_job(job_id: int, session: Session | None = None) -> Job | None:
    if session is not None:
        return session.get(Job, job_id)
    with session_scope() as scoped:
        job = scoped.get(Job, job_id)
        if job is not None:
            scoped.expunge(job)
        return job


def list_jobs(limit: int = 50) -> list[Job]:
    with session_scope() as session:
        rows = session.scalars(select(Job).order_by(Job.id.desc()).limit(limit)).all()
        for row in rows:
            session.expunge(row)
        return list(rows)


def cancel_job(job_id: int) -> Job:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise KeyError(f"Job {job_id} not found")
        job.cancel_requested = True
        if job.status == JobStatus.queued:
            job.status = JobStatus.cancelled
            job.finished_at = dt.datetime.now(dt.timezone.utc)
            append_log(session, job, "Cancelled before start.")
        else:
            append_log(session, job, "Cancel requested.")
        session.flush()
        session.refresh(job)
        session.expunge(job)
        return job


def append_log(session: Session, job: Job, line: str) -> None:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    job.log = (job.log or "") + f"[{stamp}] {line.rstrip()}\n"
    session.add(job)


def job_llm_cost(session: Session, job: Job) -> float:
    q = select(func.coalesce(func.sum(LlmCall.est_cost_usd), 0)).where(LlmCall.job_id == job.id)
    if job.started_at is not None:
        q = select(func.coalesce(func.sum(LlmCall.est_cost_usd), 0)).where(
            or_(LlmCall.job_id == job.id, LlmCall.job_id.is_(None) & (LlmCall.created_at >= job.started_at))
        )
    return float(session.scalar(q) or 0)


def update_progress(session: Session, job: Job, done: int, total: int, stage: str) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    prev = dict(job.progress or {})
    started_raw = prev.get("stage_started_at") if prev.get("stage") == stage else None
    if started_raw:
        try:
            stage_started = dt.datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
        except ValueError:
            stage_started = now
    else:
        stage_started = now
    if stage_started.tzinfo is None:
        stage_started = stage_started.replace(tzinfo=dt.timezone.utc)
    elapsed_min = max((now - stage_started).total_seconds() / 60.0, 1 / 60)
    rows_per_minute = round(done / elapsed_min, 1) if done else 0.0
    job.actual_cost_usd = job_llm_cost(session, job)
    job.progress = {
        "done": done,
        "total": total,
        "stage": stage,
        "rows_per_minute": rows_per_minute,
        "stage_started_at": stage_started.isoformat(),
    }
    session.add(job)


def claim_next(session: Session) -> Job | None:
    job = session.scalar(
        select(Job)
        .where(Job.status == JobStatus.queued)
        .order_by(Job.id.asc())
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status = JobStatus.running
    if job.started_at is None:
        job.started_at = dt.datetime.now(dt.timezone.utc)
    job.progress = {**(job.progress or {}), "done": 0, "total": 0, "stage": "starting"}
    return job
