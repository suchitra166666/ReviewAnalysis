from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from rap.db.models import Job, JobKind, JobStatus, LlmCall
from rap.db.session import session_scope
from rap.jobs.estimators import estimate_breakdown
from rap.jobs.queue import (
    ConfirmationRequired,
    CostCapExceeded,
    cancel_job,
    create_job,
    estimate_job,
    get_job,
    list_jobs,
)

router = APIRouter()


class JobCreate(BaseModel):
    kind: JobKind
    params: dict[str, Any] = {}
    confirm: bool = False


class EstimateIn(BaseModel):
    kind: JobKind
    params: dict[str, Any] = {}


def _job_public(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind.value,
        "params": job.params,
        "status": job.status.value,
        "progress": job.progress,
        "est_cost_usd": job.est_cost_usd,
        "actual_cost_usd": job.actual_cost_usd,
        "log": job.log,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "cancel_requested": job.cancel_requested,
    }


@router.post("/jobs/estimate")
def post_estimate(body: EstimateIn) -> dict[str, Any]:
    estimate = estimate_job(body.kind, body.params)
    breakdown = estimate_breakdown(body.kind, body.params)
    from rap.settings import get_setting

    cap = float(get_setting("costs.max_run_cost_usd", 25) or 25)
    threshold = float(get_setting("costs.require_confirmation_above_usd", 5) or 5)
    return {
        "est_cost_usd": estimate,
        "breakdown": breakdown,
        "requires_confirmation": estimate > threshold,
        "refused": estimate > cap,
        "cap": cap,
        "threshold": threshold,
    }


@router.post("/jobs")
def post_job(body: JobCreate) -> dict[str, Any]:
    try:
        job = create_job(body.kind, body.params, confirm=body.confirm)
    except CostCapExceeded as exc:
        raise HTTPException(400, str(exc))
    except ConfirmationRequired as exc:
        raise HTTPException(
            409,
            {
                "code": "confirmation_required",
                "estimate": exc.estimate,
                "threshold": exc.threshold,
                "message": str(exc),
            },
        )
    return _job_public(job)


@router.get("/jobs")
def get_jobs() -> list[dict[str, Any]]:
    return [_job_public(j) for j in list_jobs()]


@router.get("/jobs/{job_id}")
def get_one_job(job_id: int) -> dict[str, Any]:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return _job_public(job)


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: int) -> StreamingResponse:
    async def events():
        last = ""
        while True:
            job = get_job(job_id)
            if job is None:
                yield "event: error\ndata: missing\n\n"
                return
            payload = _job_public(job)
            blob = json.dumps(payload)
            if blob != last:
                yield f"data: {blob}\n\n"
                last = blob
            if job.status in {JobStatus.ok, JobStatus.failed, JobStatus.cancelled}:
                return
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/jobs/{job_id}/cancel")
def post_cancel(job_id: int) -> dict[str, Any]:
    try:
        return _job_public(cancel_job(job_id))
    except KeyError:
        raise HTTPException(404, "Job not found")


@router.get("/spend")
def monthly_spend() -> dict[str, Any]:
    with session_scope() as session:
        total = session.scalar(select(LlmCall.est_cost_usd)) 
        # sum properly
        from sqlalchemy import func

        total = session.scalar(select(func.coalesce(func.sum(LlmCall.est_cost_usd), 0))) or 0
    return {"month_usd": float(total)}
