from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from rap.db.models import ReviewEmbedding, ReviewFinal, ReviewRaw
from rap.db.scope import apply_review_scope
from rap.db.session import session_scope
from rap.llm.client import embed_texts_async
from rap.settings import role_config

ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]


def run_embeddings(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    with session_scope() as session:
        q = apply_review_scope(
            select(ReviewRaw)
            .join(ReviewFinal, ReviewFinal.review_id == ReviewRaw.id)
            .where(ReviewRaw.id.not_in(select(ReviewEmbedding.review_id))),
            session,
            params,
        )
        rows = list(session.scalars(q).all())
        for row in rows:
            session.expunge(row)
    if progress:
        progress(0, len(rows), f"{len(rows)} reviews to embed")
    if dry_run:
        return {"pending": len(rows)}
    written = asyncio.run(
        _embed_batches(rows, progress=progress, should_cancel=should_cancel)
    )
    return {"pending": len(rows), "written": written}


async def run_embeddings_async(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    with session_scope() as session:
        q = apply_review_scope(
            select(ReviewRaw)
            .join(ReviewFinal, ReviewFinal.review_id == ReviewRaw.id)
            .where(ReviewRaw.id.not_in(select(ReviewEmbedding.review_id))),
            session,
            params,
        )
        rows = list(session.scalars(q).all())
        for row in rows:
            session.expunge(row)
    if progress:
        progress(0, len(rows), f"{len(rows)} reviews to embed")
    if dry_run:
        return {"pending": len(rows)}
    written = await _embed_batches(rows, progress=progress, should_cancel=should_cancel)
    return {"pending": len(rows), "written": written}


async def _embed_batches(
    rows: list,
    *,
    progress: ProgressFn | None,
    should_cancel: CancelFn | None,
) -> int:
    model_id = role_config("embed")["model"]
    batches = [rows[i : i + 100] for i in range(0, len(rows), 100)]
    written = 0
    lock = asyncio.Lock()

    async def one(batch) -> None:
        nonlocal written
        if should_cancel and should_cancel():
            return
        texts = [f"{r.title or ''} {r.body}".strip() for r in batch]
        vectors = await embed_texts_async(texts)
        with session_scope() as session:
            for review, vector in zip(batch, vectors, strict=False):
                session.merge(
                    ReviewEmbedding(review_id=review.id, model_id=model_id, embedding=vector)
                )
        async with lock:
            written += len(batch)
            if progress:
                progress(written, len(rows), f"embedded {written}")

    if not batches:
        return 0
    await asyncio.gather(*(one(batch) for batch in batches))
    return written
