from __future__ import annotations

import asyncio

from rap.db.models import Job, JobKind, JobStatus
from rap.db.session import session_scope
from rap.jobs.queue import append_log, update_progress
from rap.llm.context import current_job_id, job_log


def handle_job(job_id: int) -> None:
    token_job = current_job_id.set(job_id)
    token_log = job_log.set(lambda line, _id=job_id: _log(_id, line))
    try:
        with session_scope() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise KeyError(f"Job {job_id} not found")
            if job.cancel_requested:
                job.status = JobStatus.cancelled
                return
            kind = job.kind
            params = dict(job.params or {})

        if kind == JobKind.scrape:
            _handle_scrape(job_id, params)
        elif kind == JobKind.extract_a:
            _handle_extract(job_id, params, role="a")
        elif kind == JobKind.extract_b:
            _handle_extract(job_id, params, role="b")
        elif kind == JobKind.reconcile:
            _handle_reconcile(job_id, params)
        elif kind == JobKind.translate:
            _handle_translate(job_id, params)
        elif kind == JobKind.flags:
            _handle_flags(job_id, params)
        elif kind == JobKind.summarize:
            _handle_summarize(job_id, params)
        elif kind == JobKind.full_pipeline:
            _handle_full(job_id, params)
        else:
            raise RuntimeError(f"Unknown job kind: {kind}")
    finally:
        current_job_id.reset(token_job)
        job_log.reset(token_log)


def _log(job_id: int, line: str) -> None:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job:
            append_log(session, job, line)


def _progress(job_id: int, done: int, total: int, stage: str) -> None:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job:
            update_progress(session, job, done, total, stage)


def _cancelled(job_id: int) -> bool:
    with session_scope() as session:
        job = session.get(Job, job_id)
        return bool(job and job.cancel_requested)


def _handle_scrape(job_id: int, params: dict) -> None:
    from rap.scrape.runner import run_scrape

    slugs = params.get("slugs") or ([params["company"]] if params.get("company") else [])
    stores = params.get("stores") or ["appstore", "play"]
    if stores == ["all"] or params.get("store") == "all":
        stores = ["appstore", "play"]
    _progress(job_id, 0, len(slugs) * len(stores), "scrape")

    def progress(line: str) -> None:
        _log(job_id, line)

    results = run_scrape(slugs=slugs, stores=stores, full=bool(params.get("full")), progress=progress)
    _log(job_id, f"Scrape complete: {results}")
    _progress(job_id, len(results), len(results), "scrape")


def _handle_extract(job_id: int, params: dict, role: str) -> None:
    from rap.llm.extract import run_extract

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, f"extract_{role}")
        _log(job_id, line)

    run_extract(role=role, params=params, progress=progress, should_cancel=lambda: _cancelled(job_id))


async def _handle_extract_async(job_id: int, params: dict, role: str) -> None:
    from rap.llm.extract import run_extract_async

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, f"extract_{role}")
        _log(job_id, line)

    await run_extract_async(
        role=role, params=params, progress=progress, should_cancel=lambda: _cancelled(job_id)
    )


def _handle_reconcile(job_id: int, params: dict) -> None:
    from rap.llm.reconcile import run_reconcile

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "reconcile")
        _log(job_id, line)

    run_reconcile(params=params, progress=progress, should_cancel=lambda: _cancelled(job_id))


async def _handle_reconcile_async(job_id: int, params: dict) -> None:
    from rap.llm.reconcile import run_reconcile_async

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "reconcile")
        _log(job_id, line)

    await run_reconcile_async(
        params=params, progress=progress, should_cancel=lambda: _cancelled(job_id)
    )


def _handle_translate(job_id: int, params: dict) -> None:
    from rap.llm.translate import run_translate

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "translate")
        _log(job_id, line)

    run_translate(params=params, progress=progress, should_cancel=lambda: _cancelled(job_id))


async def _handle_translate_async(job_id: int, params: dict) -> None:
    from rap.llm.translate import run_translate_async

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "translate")
        _log(job_id, line)

    await run_translate_async(
        params=params, progress=progress, should_cancel=lambda: _cancelled(job_id)
    )


def _handle_flags(job_id: int, params: dict) -> None:
    from rap.flags.embeddings import run_embeddings
    from rap.flags.incentivized import run_flags

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "flags")
        _log(job_id, line)

    run_embeddings(params=params, progress=progress, should_cancel=lambda: _cancelled(job_id))
    run_flags(params=params, progress=progress, should_cancel=lambda: _cancelled(job_id))


async def _handle_flags_async(job_id: int, params: dict) -> None:
    from rap.flags.embeddings import run_embeddings_async
    from rap.flags.incentivized import run_flags

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "flags")
        _log(job_id, line)

    await run_embeddings_async(
        params=params, progress=progress, should_cancel=lambda: _cancelled(job_id)
    )
    await asyncio.to_thread(
        run_flags, params=params, progress=progress, should_cancel=lambda: _cancelled(job_id)
    )


def _handle_summarize(job_id: int, params: dict) -> None:
    from rap.llm.summarize import run_summarize

    def progress(done: int, total: int, line: str) -> None:
        _progress(job_id, done, total, "summarize")
        _log(job_id, line)

    run_summarize(params=params, progress=progress, should_cancel=lambda: _cancelled(job_id))


def _handle_full(job_id: int, params: dict) -> None:
    asyncio.run(_handle_full_async(job_id, params))


async def _handle_full_async(job_id: int, params: dict) -> None:
    stages = list(
        params.get("stages")
        or [
            "scrape",
            "extract_a",
            "extract_b",
            "reconcile",
            "translate",
            "flags",
            "summarize",
        ]
    )
    total = len(stages)
    i = 0
    while i < len(stages):
        if _cancelled(job_id):
            return
        stage = stages[i]
        nxt = stages[i + 1] if i + 1 < len(stages) else None
        if stage == "extract_a" and nxt == "extract_b":
            _progress(job_id, i, total, "extract")
            _log(job_id, "Stage extract_a + extract_b (concurrent)")
            await asyncio.gather(
                _handle_extract_async(job_id, params, "a"),
                _handle_extract_async(job_id, params, "b"),
            )
            i += 2
            continue
        if stage == "translate" and nxt == "flags":
            _progress(job_id, i, total, "translate_flags")
            _log(job_id, "Stage translate + flags (concurrent)")
            await asyncio.gather(
                _handle_translate_async(job_id, params),
                _handle_flags_async(job_id, params),
            )
            i += 2
            continue
        _progress(job_id, i, total, stage)
        _log(job_id, f"Stage {stage}")
        if stage == "scrape":
            await asyncio.to_thread(_handle_scrape, job_id, params)
        elif stage == "extract_a":
            await _handle_extract_async(job_id, params, "a")
        elif stage == "extract_b":
            await _handle_extract_async(job_id, params, "b")
        elif stage == "reconcile":
            await _handle_reconcile_async(job_id, params)
        elif stage == "translate":
            await _handle_translate_async(job_id, params)
        elif stage == "flags":
            await _handle_flags_async(job_id, params)
        elif stage == "summarize":
            await asyncio.to_thread(_handle_summarize, job_id, params)
        i += 1
    _progress(job_id, total, total, "done")
