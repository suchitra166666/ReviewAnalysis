from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from rap.db.models import ExtractRole, LlmPurpose, ReviewExtracted, ReviewFinal, ReviewRaw
from rap.db.scope import apply_review_scope
from rap.db.session import session_scope
from rap.llm.client import call_llm_async, load_prompt, parse_json_content
from rap.llm.sample import uses_sample
from rap.llm.schemas import ReviewExtraction
from rap.settings import get_setting

ProgressFn = Callable[[int, int, str], None]
CancelFn = Callable[[], bool]

AGREE_FIELDS = (
    "language",
    "overall_sentiment",
    "is_food_related",
    "feedback_type",
    "churn_intent",
    "mentions_incentive",
    "low_information",
    "rating_text_mismatch",
)


def _sentiments_agree(a: str | None, b: str | None) -> bool:
    if a == b:
        return True
    return {a, b} <= {"neutral", "mixed"}


def theme_set(mentions: list[dict] | None) -> set[str]:
    return {m.get("theme") for m in (mentions or []) if m.get("theme")}


def theme_sentiment(mentions: list[dict] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for mention in mentions or []:
        theme = mention.get("theme")
        if theme:
            out[theme] = mention.get("sentiment")
    return out


def disagreements(a: ReviewExtracted, b: ReviewExtracted) -> list[str]:
    diffs: list[str] = []
    for field in AGREE_FIELDS:
        av = getattr(a, field)
        bv = getattr(b, field)
        if field == "overall_sentiment":
            if not _sentiments_agree(av, bv):
                diffs.append(field)
        elif av != bv:
            diffs.append(field)
    a_themes = theme_set(a.mentions)
    b_themes = theme_set(b.mentions)
    if a_themes != b_themes:
        diffs.extend(sorted(a_themes.symmetric_difference(b_themes)))
    else:
        a_sent = theme_sentiment(a.mentions)
        b_sent = theme_sentiment(b.mentions)
        for theme in a_themes:
            if not _sentiments_agree(a_sent.get(theme), b_sent.get(theme)):
                diffs.append(theme)
    return diffs


def _row_to_final(row: ReviewExtracted, source_role: str, tier: str, diffs: list[str]) -> ReviewFinal:
    return ReviewFinal(
        review_id=row.review_id,
        source_role=source_role,
        confidence_tier=tier,
        disagreement_themes=diffs,
        language=row.language,
        overall_sentiment=row.overall_sentiment,
        is_food_related=row.is_food_related,
        feedback_type=row.feedback_type,
        churn_intent=row.churn_intent,
        competitor_mentions=row.competitor_mentions,
        mentions=row.mentions,
        mentions_incentive=row.mentions_incentive,
        low_information=row.low_information,
        rating_text_mismatch=row.rating_text_mismatch,
        schema_valid=row.schema_valid,
        prompt_version=row.prompt_version,
    )


def _extraction_to_final(item: ReviewExtraction, row_a: ReviewExtracted, diffs: list[str]) -> ReviewFinal:
    return ReviewFinal(
        review_id=item.review_id,
        source_role="tiebreak",
        confidence_tier="contested",
        disagreement_themes=diffs,
        language=item.language,
        overall_sentiment=item.overall_sentiment,
        is_food_related=item.is_food_related,
        feedback_type=item.feedback_type,
        churn_intent=item.churn_intent,
        competitor_mentions=[m.model_dump() for m in item.competitor_mentions],
        mentions=[m.model_dump() for m in item.mentions],
        mentions_incentive=item.mentions_incentive,
        low_information=item.low_information,
        rating_text_mismatch=item.rating_text_mismatch,
        schema_valid=True,
        prompt_version=row_a.prompt_version,
    )


def run_reconcile(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
) -> dict[str, Any]:
    prompt_version = str(get_setting("extraction.prompt_version", "v3") or "v3")
    single = bool(get_setting("models.use_single_model", False))
    with session_scope() as session:
        pairs = _pending_pairs(session, params, prompt_version)

    return asyncio.run(
        _reconcile_pairs(
            pairs,
            single=single or uses_sample(params),
            progress=progress,
            should_cancel=should_cancel,
        )
    )


async def run_reconcile_async(
    *,
    params: dict[str, Any],
    progress: ProgressFn | None = None,
    should_cancel: CancelFn | None = None,
) -> dict[str, Any]:
    prompt_version = str(get_setting("extraction.prompt_version", "v3") or "v3")
    single = bool(get_setting("models.use_single_model", False))
    with session_scope() as session:
        pairs = _pending_pairs(session, params, prompt_version)
    return await _reconcile_pairs(
        pairs,
        single=single or uses_sample(params),
        progress=progress,
        should_cancel=should_cancel,
    )


def _pending_pairs(session, params: dict[str, Any], prompt_version: str) -> list[tuple]:
    a_rows = session.scalars(
        select(ReviewExtracted).where(
            ReviewExtracted.role == ExtractRole.a,
            ReviewExtracted.prompt_version == prompt_version,
        )
    ).all()
    raw_ids = set(session.scalars(apply_review_scope(select(ReviewRaw.id), session, params)))
    a_rows = [r for r in a_rows if r.review_id in raw_ids]
    if uses_sample(params):
        a_rows = [r for r in a_rows if r.job_id is not None]
    b_by_id = {
        r.review_id: r
        for r in session.scalars(
            select(ReviewExtracted).where(
                ReviewExtracted.role == ExtractRole.b,
                ReviewExtracted.prompt_version == prompt_version,
            )
        )
    }
    already = set(session.scalars(select(ReviewFinal.review_id)))
    pairs = [(a, b_by_id.get(a.review_id)) for a in a_rows if a.review_id not in already]
    for a, b in pairs:
        session.expunge(a)
        if b is not None:
            session.expunge(b)
    return pairs


async def _reconcile_pairs(
    pairs: list[tuple],
    *,
    single: bool,
    progress: ProgressFn | None,
    should_cancel: CancelFn | None,
) -> dict[str, Any]:
    agreed = 0
    contested_pairs: list[tuple] = []
    for a, b in pairs:
        if b is None and not single:
            continue
        compare_b = b or a
        diffs = disagreements(a, compare_b)
        if not diffs:
            with session_scope() as session:
                session.merge(_row_to_final(a, "a", "agreed", []))
            agreed += 1
        else:
            contested_pairs.append((a, compare_b, diffs))
    if progress:
        progress(agreed, len(pairs), f"{agreed} agreed, {len(contested_pairs)} contested")

    contested = 0
    completed = 0
    started = time.monotonic()
    lock = asyncio.Lock()

    async def one(a, compare_b, diffs) -> None:
        nonlocal contested, completed
        if should_cancel and should_cancel():
            return
        raw = None
        with session_scope() as session:
            raw = session.get(ReviewRaw, a.review_id)
            if raw:
                session.expunge(raw)
        if raw is None:
            return
        messages = [
            {"role": "system", "content": load_prompt("tiebreak_v3.md")},
            {
                "role": "user",
                "content": (
                    f"stars={raw.star_rating}\n{(raw.title or '')} — {raw.body}\n\n"
                    f"A={_dump_extracted(a)}\nB={_dump_extracted(compare_b)}"
                ),
            },
        ]
        try:
            result = await call_llm_async(
                purpose=LlmPurpose.tiebreak,
                role="tiebreak",
                messages=messages,
                json_object=True,
                n_items=1,
            )
            item = ReviewExtraction.model_validate(parse_json_content(result["content"]))
            with session_scope() as session:
                session.merge(_extraction_to_final(item, a, diffs))
        except Exception:
            with session_scope() as session:
                session.merge(_row_to_final(a, "a", "contested", diffs))
        async with lock:
            contested += 1
            completed += 1
            done = agreed + contested
            if progress:
                progress(done, len(pairs), f"reconciled {done}/{len(pairs)}")
            if completed % 10 == 0:
                elapsed_min = max((time.monotonic() - started) / 60.0, 1 / 60)
                if progress:
                    progress(
                        done,
                        len(pairs),
                        f"{done / elapsed_min:.1f} rows/min after {completed} tiebreaks",
                    )

    if contested_pairs:
        await asyncio.gather(*(one(a, b, d) for a, b, d in contested_pairs))
    return {"agreed": agreed, "contested": contested, "pairs": len(pairs)}


def _dump_extracted(row: ReviewExtracted) -> str:
    return ReviewExtraction(
        review_id=row.review_id,
        language=row.language or "other",
        is_food_related=bool(row.is_food_related),
        overall_sentiment=row.overall_sentiment or "neutral",
        feedback_type=row.feedback_type or "other",
        churn_intent=bool(row.churn_intent),
        competitor_mentions=row.competitor_mentions or [],
        mentions=row.mentions or [],
        mentions_incentive=bool(row.mentions_incentive),
        low_information=bool(row.low_information),
        rating_text_mismatch=bool(row.rating_text_mismatch),
    ).model_dump_json()
