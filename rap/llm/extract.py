from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rap.db.models import ExtractRole, LlmPurpose, ReviewExtracted, ReviewRaw
from rap.db.scope import apply_review_scope
from rap.db.session import session_scope
from rap.llm.aliases import alias_map, attach_slugs
from rap.llm.client import call_llm, call_llm_async, load_prompt, parse_json_content
from rap.llm.context import current_job_id
from rap.llm.sample import star_balanced_sample
from rap.llm.schemas import ExtractionBatch, ReviewExtraction
from rap.settings import get_setting

ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]


def extract_system_prompt() -> str:
    return load_prompt("extract_v3.md")


def format_user_message(reviews: list[ReviewRaw]) -> str:
    max_chars = int(get_setting("extraction.max_review_chars", 2000) or 2000)
    lines = []
    for review in reviews:
        body = (review.body or "")[:max_chars]
        title = review.title or ""
        date = review.review_date.date().isoformat()
        lines.append(f"[{review.id}] (stars={review.star_rating}, date={date}) {title} — {body}")
    return "\n".join(lines)


def batch_reviews(rows: list[ReviewRaw], size: int) -> list[list[ReviewRaw]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def pending_reviews(
    session: Session,
    role: ExtractRole,
    prompt_version: str,
    company_ids: list[int] | None,
    limit: int | None,
    sample_per_star: int | None,
    params: dict[str, Any] | None = None,
) -> list[ReviewRaw]:
    extracted_ids = select(ReviewExtracted.review_id).where(
        ReviewExtracted.role == role,
        ReviewExtracted.prompt_version == prompt_version,
    )
    q = select(ReviewRaw).where(ReviewRaw.id.not_in(extracted_ids))
    scoped = dict(params or {})
    if company_ids:
        scoped["company_ids"] = company_ids
    q = apply_review_scope(q, session, scoped)
    q = q.order_by(ReviewRaw.review_date.desc())
    rows = list(session.scalars(q).all())
    if limit:
        rows = rows[:limit]
    return rows


def _sampled_ids(session: Session, role: ExtractRole, prompt_version: str, params: dict[str, Any]) -> set[int]:
    del role  # membership is shared across A and B so a later role adds to the same reviews
    q = (
        select(ReviewExtracted.review_id)
        .join(ReviewRaw, ReviewRaw.id == ReviewExtracted.review_id)
        .where(
            ReviewExtracted.prompt_version == prompt_version,
            ReviewExtracted.job_id.is_not(None),
        )
    )
    q = apply_review_scope(q, session, params)
    return set(session.scalars(q))


def _sample_pending(
    session: Session,
    role: ExtractRole,
    prompt_version: str,
    params: dict[str, Any],
    sample_per_star: int,
) -> tuple[list[ReviewRaw], int]:
    scoped = apply_review_scope(select(ReviewRaw), session, params).order_by(ReviewRaw.review_date.desc())
    universe = list(session.scalars(scoped).all())
    already_ids = _sampled_ids(session, role, prompt_version, params)
    sample = star_balanced_sample(universe, sample_per_star=sample_per_star, already_ids=already_ids)
    job_id = current_job_id.get()
    extracted = {
        row.review_id: row
        for row in session.scalars(
            select(ReviewExtracted).where(
                ReviewExtracted.role == role,
                ReviewExtracted.prompt_version == prompt_version,
                ReviewExtracted.review_id.in_([r.id for r in sample] or [0]),
            )
        )
    }
    pending: list[ReviewRaw] = []
    for raw in sample:
        row = extracted.get(raw.id)
        if row is None:
            pending.append(raw)
            continue
        if job_id and row.job_id is None:
            row.job_id = job_id
    return pending, len(sample) - len(pending)


def _queue_for_extract(
    session: Session,
    role: ExtractRole,
    prompt_version: str,
    params: dict[str, Any],
    sample_per_star: int | None,
) -> tuple[int, list[ReviewRaw]]:
    scoped = dict(params or {})
    if params.get("company_ids"):
        scoped["company_ids"] = params["company_ids"]
    if sample_per_star:
        rows, already = _sample_pending(session, role, prompt_version, scoped, sample_per_star)
        return already, rows
    already = already_extracted_count(session, role, prompt_version, scoped)
    rows = pending_reviews(
        session,
        role,
        prompt_version,
        params.get("company_ids"),
        None,
        None,
        scoped,
    )
    return already, rows


def already_extracted_count(
    session: Session,
    role: ExtractRole,
    prompt_version: str,
    params: dict[str, Any] | None = None,
) -> int:
    q = (
        select(func.count())
        .select_from(ReviewExtracted)
        .join(ReviewRaw, ReviewRaw.id == ReviewExtracted.review_id)
        .where(
            ReviewExtracted.role == role,
            ReviewExtracted.prompt_version == prompt_version,
        )
    )
    q = apply_review_scope(q, session, dict(params or {}))
    return int(session.scalar(q) or 0)


def _coerce_item(item: dict[str, Any]) -> dict[str, Any]:
    row = dict(item)
    if "language" not in row:
        row["language"] = "other"
    if "overall_sentiment" not in row and row.get("sentiment"):
        row["overall_sentiment"] = row["sentiment"]
    if "mentions" not in row and row.get("theme"):
        row["mentions"] = [
            {
                "theme": row.get("theme") or "other",
                "sub_theme": row.get("sub_theme"),
                "sentiment": row.get("sentiment") or row.get("overall_sentiment") or "neutral",
                "confidence": row.get("confidence", 0.7),
                "snippet": row.get("snippet") or "",
                "snippet_en": row.get("snippet_en"),
            }
        ]
    return row


def validate_batch(payload: Any, expected_ids: set[int]) -> tuple[list[ReviewExtraction], list[int]]:
    valid: list[ReviewExtraction] = []
    invalid: list[int] = []
    if isinstance(payload, dict) and "review_id" in payload and "items" not in payload:
        payload = {"items": [payload]}
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        payload = {**payload, "items": [_coerce_item(i) if isinstance(i, dict) else i for i in payload["items"]]}
    elif isinstance(payload, list):
        payload = {"items": [_coerce_item(i) if isinstance(i, dict) else i for i in payload]}
    try:
        batch = ExtractionBatch.model_validate(payload)
        items = batch.items
    except ValidationError:
        if isinstance(payload, dict) and "items" in payload:
            items = payload["items"]
        elif isinstance(payload, list):
            items = payload
        else:
            return [], list(expected_ids)
    seen: set[int] = set()
    for item in items:
        try:
            parsed = ReviewExtraction.model_validate(item)
            if parsed.review_id not in expected_ids:
                continue
            valid.append(parsed)
            seen.add(parsed.review_id)
        except ValidationError:
            rid = item.get("review_id") if isinstance(item, dict) else None
            if isinstance(rid, int):
                invalid.append(rid)
    for rid in expected_ids - seen:
        invalid.append(rid)
    return valid, invalid


def persist_extractions(
    session: Session,
    items: list[ReviewExtraction],
    *,
    role: ExtractRole,
    model_id: str,
    prompt_version: str,
    schema_valid: bool,
) -> None:
    mapping = alias_map()
    seen: set[int] = set()
    for item in items:
        if item.review_id in seen:
            continue
        seen.add(item.review_id)
        mentions = attach_slugs([m.model_dump() for m in item.competitor_mentions], mapping)
        values = {
            "model_id": model_id,
            "language": item.language,
            "overall_sentiment": item.overall_sentiment,
            "is_food_related": item.is_food_related,
            "feedback_type": item.feedback_type,
            "churn_intent": item.churn_intent,
            "competitor_mentions": mentions,
            "mentions": [m.model_dump() for m in item.mentions],
            "mentions_incentive": item.mentions_incentive,
            "low_information": item.low_information,
            "rating_text_mismatch": item.rating_text_mismatch,
            "schema_valid": schema_valid,
        }
        job_id = current_job_id.get()
        if job_id is not None:
            values["job_id"] = job_id
        row = session.scalar(
            select(ReviewExtracted).where(
                ReviewExtracted.review_id == item.review_id,
                ReviewExtracted.role == role,
                ReviewExtracted.prompt_version == prompt_version,
            )
        )
        if row is None:
            try:
                with session.begin_nested():
                    session.add(
                        ReviewExtracted(
                            review_id=item.review_id,
                            role=role,
                            prompt_version=prompt_version,
                            **values,
                        )
                    )
                    session.flush()
            except IntegrityError:
                row = session.scalar(
                    select(ReviewExtracted).where(
                        ReviewExtracted.review_id == item.review_id,
                        ReviewExtracted.role == role,
                        ReviewExtracted.prompt_version == prompt_version,
                    )
                )
                if row is not None:
                    for key, value in values.items():
                        setattr(row, key, value)
        else:
            for key, value in values.items():
                setattr(row, key, value)


def _purpose(role: str) -> LlmPurpose:
    return LlmPurpose.extract_a if role == "a" else LlmPurpose.extract_b


def _extraction_schema() -> dict[str, Any]:
    from openai.lib._pydantic import to_strict_json_schema

    return to_strict_json_schema(ExtractionBatch)


def _call_and_parse(
    role: str,
    reviews: list[ReviewRaw],
    json_object: bool,
) -> tuple[list[ReviewExtraction], list[int], str]:
    messages = [
        {"role": "system", "content": extract_system_prompt()},
        {"role": "user", "content": format_user_message(reviews)},
    ]
    result = call_llm(
        purpose=_purpose(role),
        role=f"extract_{role}",
        messages=messages,
        schema=None if json_object else _extraction_schema(),
        json_object=json_object,
        n_items=len(reviews),
    )
    payload = parse_json_content(result["content"])
    valid, invalid = validate_batch(payload, {r.id for r in reviews})
    return valid, invalid, result["model_id"]


async def _call_and_parse_async(
    role: str,
    reviews: list[ReviewRaw],
    json_object: bool,
) -> tuple[list[ReviewExtraction], list[int], str]:
    messages = [
        {"role": "system", "content": extract_system_prompt()},
        {"role": "user", "content": format_user_message(reviews)},
    ]
    result = await call_llm_async(
        purpose=_purpose(role),
        role=f"extract_{role}",
        messages=messages,
        schema=None if json_object else _extraction_schema(),
        json_object=json_object,
        n_items=len(reviews),
    )
    payload = parse_json_content(result["content"])
    valid, invalid = validate_batch(payload, {r.id for r in reviews})
    return valid, invalid, result["model_id"]


def _is_fatal_llm_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        needle in text
        for needle in (
            "unsupported value",
            "invalid_api_key",
            "incorrect api key",
            "insufficient_quota",
            "authentication",
        )
    )


def _dummy_extraction(review_id: int) -> ReviewExtraction:
    return ReviewExtraction(
        review_id=review_id,
        language="other",
        is_food_related=True,
        overall_sentiment="neutral",
        feedback_type="other",
        churn_intent=False,
        mentions_incentive=False,
        low_information=True,
        rating_text_mismatch=False,
    )


async def _process_batch_async(
    role: str,
    role_enum: ExtractRole,
    prompt_version: str,
    batch: list[ReviewRaw],
    json_object: bool,
) -> tuple[int, str | None]:
    try:
        valid, invalid, model_id = await _call_and_parse_async(role, batch, json_object)
    except Exception as exc:
        if _is_fatal_llm_error(exc):
            raise
        invalid = [r.id for r in batch]
        valid = []
        model_id = ""
        note = f"batch failed: {exc}"
    else:
        note = None
    if invalid:
        by_id = {r.id: r for r in batch}
        for rid in invalid:
            review = by_id.get(rid)
            if review is None:
                continue
            try:
                v2, inv2, model_id = await _call_and_parse_async(role, [review], json_object)
                valid.extend(v2)
                if inv2:
                    with session_scope() as session:
                        persist_extractions(
                            session,
                            [_dummy_extraction(rid)],
                            role=role_enum,
                            model_id=model_id or "unknown",
                            prompt_version=prompt_version,
                            schema_valid=False,
                        )
            except Exception:
                with session_scope() as session:
                    persist_extractions(
                        session,
                        [_dummy_extraction(rid)],
                        role=role_enum,
                        model_id=model_id or "unknown",
                        prompt_version=prompt_version,
                        schema_valid=False,
                    )
    written = 0
    if valid:
        with session_scope() as session:
            persist_extractions(
                session,
                valid,
                role=role_enum,
                model_id=model_id or "unknown",
                prompt_version=prompt_version,
                schema_valid=True,
            )
        written = len(valid)
    return written, note


def run_extract(
    *,
    role: str,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    prompt_version = str(get_setting("extraction.prompt_version", "v3") or "v3")
    batch_size = int(get_setting("extraction.batch_size", 15) or 15)
    sample = params.get("sample_per_star") or get_setting("extraction.sample_per_star")
    sample_per_star = int(sample) if sample else None
    role_enum = ExtractRole.a if role == "a" else ExtractRole.b
    with session_scope() as session:
        already, rows = _queue_for_extract(
            session, role_enum, prompt_version, params, sample_per_star
        )
        if params.get("limit"):
            rows = rows[: int(params["limit"])]
        for row in rows:
            session.expunge(row)
    total = already + len(rows)
    if progress:
        progress(
            already,
            total,
            f"{already}/{total} already extracted for role {role}; {len(rows)} pending",
        )
    if dry_run:
        return {"pending": len(rows), "written": 0}
    json_object = role == "b"
    batches = batch_reviews(rows, batch_size)
    written = asyncio.run(
        _run_batches(
            role=role,
            role_enum=role_enum,
            prompt_version=prompt_version,
            rows=rows,
            batches=batches,
            json_object=json_object,
            progress=progress,
            should_cancel=should_cancel,
            already=already,
            total=total,
        )
    )
    return {"pending": len(rows), "written": written}


async def run_extract_async(
    *,
    role: str,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    prompt_version = str(get_setting("extraction.prompt_version", "v3") or "v3")
    batch_size = int(get_setting("extraction.batch_size", 15) or 15)
    sample = params.get("sample_per_star") or get_setting("extraction.sample_per_star")
    sample_per_star = int(sample) if sample else None
    role_enum = ExtractRole.a if role == "a" else ExtractRole.b
    with session_scope() as session:
        already, rows = _queue_for_extract(
            session, role_enum, prompt_version, params, sample_per_star
        )
        if params.get("limit"):
            rows = rows[: int(params["limit"])]
        for row in rows:
            session.expunge(row)
    total = already + len(rows)
    if progress:
        progress(
            already,
            total,
            f"{already}/{total} already extracted for role {role}; {len(rows)} pending",
        )
    if dry_run:
        return {"pending": len(rows), "written": 0}
    written = await _run_batches(
        role=role,
        role_enum=role_enum,
        prompt_version=prompt_version,
        rows=rows,
        batches=batch_reviews(rows, batch_size),
        json_object=(role == "b"),
        progress=progress,
        should_cancel=should_cancel,
        already=already,
        total=total,
    )
    return {"pending": len(rows), "written": written}


async def _run_batches(
    *,
    role: str,
    role_enum: ExtractRole,
    prompt_version: str,
    rows: list[ReviewRaw],
    batches: list[list[ReviewRaw]],
    json_object: bool,
    progress: ProgressFn | None,
    should_cancel: CancelFn | None,
    already: int = 0,
    total: int | None = None,
) -> int:
    written = 0
    completed = 0
    started = time.monotonic()
    lock = asyncio.Lock()
    scope_total = total if total is not None else already + len(rows)

    async def one(batch: list[ReviewRaw]) -> None:
        nonlocal written, completed
        if should_cancel and should_cancel():
            return
        added, note = await _process_batch_async(
            role, role_enum, prompt_version, batch, json_object
        )
        async with lock:
            written += added
            completed += 1
            done = already + written
            if note and progress:
                progress(done, scope_total, note)
            if progress:
                progress(done, scope_total, f"batch {completed}/{len(batches)}")
            if completed % 10 == 0:
                elapsed_min = max((time.monotonic() - started) / 60.0, 1 / 60)
                rpm = written / elapsed_min
                if progress:
                    progress(
                        done,
                        scope_total,
                        f"{rpm:.1f} rows/min after {completed} batches",
                    )

    if not batches:
        return 0
    await asyncio.gather(*(one(batch) for batch in batches))
    return written
