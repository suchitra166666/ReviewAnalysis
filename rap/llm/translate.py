from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from rap.db.models import LlmPurpose, ReviewFinal, ReviewRaw, ReviewTranslation
from rap.db.scope import apply_review_scope
from rap.db.session import session_scope
from rap.llm.client import call_llm_async, load_prompt, parse_json_content

ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]


def pending_translations(params: dict[str, Any] | None, company_ids: list[int] | None = None) -> list[ReviewRaw]:
    scoped = dict(params or {})
    if company_ids:
        scoped["company_ids"] = company_ids
    with session_scope() as session:
        q = apply_review_scope(
            select(ReviewRaw)
            .join(ReviewFinal, ReviewFinal.review_id == ReviewRaw.id)
            .where(ReviewFinal.language.in_(["ar", "mixed", "other"]))
            .where(ReviewRaw.id.not_in(select(ReviewTranslation.review_id))),
            session,
            scoped,
        )
        rows = list(session.scalars(q).all())
        for row in rows:
            session.expunge(row)
        return rows


def run_translate(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    rows = pending_translations(params, params.get("company_ids"))
    if progress:
        progress(0, len(rows), f"{len(rows)} reviews to translate")
    if dry_run:
        return {"pending": len(rows), "written": 0}
    written = asyncio.run(
        _translate_batches(rows, progress=progress, should_cancel=should_cancel)
    )
    return {"pending": len(rows), "written": written}


async def run_translate_async(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    rows = pending_translations(params, params.get("company_ids"))
    if progress:
        progress(0, len(rows), f"{len(rows)} reviews to translate")
    if dry_run:
        return {"pending": len(rows), "written": 0}
    written = await _translate_batches(rows, progress=progress, should_cancel=should_cancel)
    return {"pending": len(rows), "written": written}


async def _translate_batches(
    rows: list[ReviewRaw],
    *,
    progress: ProgressFn | None,
    should_cancel: CancelFn | None,
) -> int:
    batches = [rows[i : i + 20] for i in range(0, len(rows), 20)]
    written = 0
    completed = 0
    started = time.monotonic()
    lock = asyncio.Lock()

    async def one(batch: list[ReviewRaw]) -> None:
        nonlocal written, completed
        if should_cancel and should_cancel():
            return
        payload = "\n".join(f"[{r.id}] TITLE: {r.title or ''}\nBODY: {r.body}" for r in batch)
        result = await call_llm_async(
            purpose=LlmPurpose.translate,
            role="translate",
            messages=[
                {"role": "system", "content": load_prompt("translate_v3.md")},
                {"role": "user", "content": payload},
            ],
            json_object=True,
            n_items=len(batch),
        )
        parsed = parse_json_content(result["content"])
        items = parsed.get("items", parsed if isinstance(parsed, list) else [])
        added = 0
        with session_scope() as session:
            for item in items:
                rid = int(item["review_id"])
                if session.get(ReviewTranslation, rid):
                    continue
                session.add(
                    ReviewTranslation(
                        review_id=rid,
                        title_en=item.get("title_en") or None,
                        body_en=item.get("body_en") or "",
                        model_id=result["model_id"],
                    )
                )
                added += 1
        async with lock:
            written += added
            completed += 1
            if progress:
                progress(written, len(rows), f"translated {written}")
            if completed % 10 == 0:
                elapsed_min = max((time.monotonic() - started) / 60.0, 1 / 60)
                if progress:
                    progress(
                        written,
                        len(rows),
                        f"{written / elapsed_min:.1f} rows/min after {completed} batches",
                    )

    if not batches:
        return 0
    await asyncio.gather(*(one(batch) for batch in batches))
    return written
