from __future__ import annotations

import datetime as dt
import logging
import socket
import threading
import time
import traceback

from sqlalchemy import select

from rap.db.models import Job, JobStatus, WorkerHeartbeat
from rap.db.session import session_scope
from rap.jobs.handlers import handle_job
from rap.jobs.queue import append_log, claim_next
from rap.logging_util import configure_logging
from rap.settings import bootstrap, stored_key_fragments

logger = logging.getLogger(__name__)
WORKER_ID = socket.gethostname()


def beat() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    with session_scope() as session:
        row = session.scalar(select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == WORKER_ID))
        if row is None:
            session.add(WorkerHeartbeat(worker_id=WORKER_ID, last_seen_at=now))
        else:
            row.last_seen_at = now


def last_heartbeat() -> dt.datetime | None:
    with session_scope() as session:
        row = session.scalar(select(WorkerHeartbeat).order_by(WorkerHeartbeat.last_seen_at.desc()))
        return row.last_seen_at if row else None


def run_once() -> bool:
    with session_scope() as session:
        job = claim_next(session)
        if job is None:
            return False
        job_id = job.id
        append_log(session, job, f"Worker {WORKER_ID} started {job.kind.value}.")
    try:
        handle_job(job_id)
        with session_scope() as session:
            job = session.get(Job, job_id)
            if job is None:
                return True
            if job.cancel_requested:
                job.status = JobStatus.cancelled
                job.finished_at = dt.datetime.now(dt.timezone.utc)
                append_log(session, job, "Cancelled.")
            elif job.status == JobStatus.running:
                job.status = JobStatus.ok
                job.finished_at = dt.datetime.now(dt.timezone.utc)
                job.progress = {**(job.progress or {}), "stage": "done"}
                append_log(session, job, "Finished.")
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        with session_scope() as session:
            job = session.get(Job, job_id)
            if job is not None:
                job.status = JobStatus.failed
                job.finished_at = dt.datetime.now(dt.timezone.utc)
                append_log(session, job, f"Failed: {exc}")
                append_log(session, job, traceback.format_exc())
    return True


def run_forever(poll_seconds: float = 2.0) -> None:
    from rap.db.migrate import upgrade_head

    upgrade_head()
    formatter = configure_logging()
    bootstrap()
    formatter.set_secrets(stored_key_fragments())
    logger.info("Worker %s listening", WORKER_ID)
    stop = threading.Event()

    def _keep_alive() -> None:
        while not stop.wait(10):
            try:
                beat()
            except Exception:
                logger.exception("Heartbeat failed")

    threading.Thread(target=_keep_alive, name="rap-heartbeat", daemon=True).start()
    try:
        while True:
            beat()
            did = run_once()
            if not did:
                time.sleep(poll_seconds)
    finally:
        stop.set()
