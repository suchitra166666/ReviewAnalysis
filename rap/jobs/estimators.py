from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from rap.db.models import JobKind, ReviewExtracted, ReviewRaw
from rap.db.scope import apply_review_scope
from rap.db.session import session_scope
from rap.settings import get_setting, model_price, role_config


def estimate(kind: JobKind, params: dict[str, Any]) -> float:
    return float(sum(estimate_breakdown(kind, params).values()))


def estimate_breakdown(kind: JobKind, params: dict[str, Any]) -> dict[str, float]:
    stages = params.get("stages") or []
    wanted = set(stages) if stages else None

    def include(name: str) -> bool:
        return wanted is None or name in wanted or (name == "summarise" and "summarize" in (wanted or []))

    out = {
        "extract_a": 0.0,
        "extract_b": 0.0,
        "tiebreak": 0.0,
        "translate": 0.0,
        "summarise": 0.0,
    }
    if kind == JobKind.scrape:
        return out
    if kind == JobKind.extract_a or kind == JobKind.full_pipeline:
        if kind == JobKind.extract_a or include("extract_a"):
            out["extract_a"] = _extract_estimate("extract_a", params)
    if kind == JobKind.extract_b or kind == JobKind.full_pipeline:
        if kind == JobKind.extract_b or include("extract_b"):
            out["extract_b"] = _extract_estimate("extract_b", params)
    if kind == JobKind.reconcile or kind == JobKind.full_pipeline:
        if kind == JobKind.reconcile or include("reconcile"):
            out["tiebreak"] = _reconcile_estimate(params)
    if kind == JobKind.translate or kind == JobKind.full_pipeline:
        if kind == JobKind.translate or include("translate"):
            out["translate"] = _translate_estimate(params)
    if kind == JobKind.summarize or kind == JobKind.full_pipeline:
        if kind == JobKind.summarize or include("summarize") or include("summarise"):
            out["summarise"] = _summarize_estimate(params)
    return out


def _pending_count(role: str | None, params: dict[str, Any]) -> int:
    if params.get("limit"):
        return int(params["limit"])
    sample = params.get("sample_per_star")
    slugs = list(params.get("slugs") or [])
    if sample:
        target = max(len(slugs), 1) * 5 * int(sample)
        with session_scope() as session:
            already_q = select(func.count()).select_from(ReviewExtracted)
            if role:
                already_q = already_q.where(ReviewExtracted.role == role)  # type: ignore[arg-type]
            already_q = already_q.where(ReviewExtracted.job_id.is_not(None))
            already = session.scalar(already_q) or 0
        return max(target - int(already), 0)
    with session_scope() as session:
        q = apply_review_scope(select(func.count()).select_from(ReviewRaw), session, params)
        total = session.scalar(q) or 0
        if role:
            extracted = select(func.count()).select_from(ReviewExtracted).where(
                ReviewExtracted.role == role  # type: ignore[arg-type]
            )
            already = session.scalar(extracted) or 0
            return max(total - already, 0)
        return total


def _role_cost(role: str, n_items: int, tokens_in: int, tokens_out: int) -> float:
    cfg = role_config(role)
    price = model_price(cfg["model"])
    input_rate = float(price.get("input") or 0)
    output_rate = float(price.get("output") or 0)
    return (n_items * tokens_in / 1_000_000) * input_rate + (
        n_items * tokens_out / 1_000_000
    ) * output_rate


def _extract_estimate(role: str, params: dict[str, Any]) -> float:
    n = max(_pending_count("a" if role == "extract_a" else "b", params), 0)
    batch = int(get_setting("extraction.batch_size", 15) or 15)
    # conservative: ~400 input tokens + 250 output tokens per review
    calls = max((n + batch - 1) // batch, 0)
    return _role_cost(role, calls, tokens_in=400 * batch, tokens_out=250 * batch)


def _reconcile_estimate(params: dict[str, Any]) -> float:
    n = max(_pending_count(None, params), 0)
    contested = max(int(n * 0.2), 0)
    return _role_cost("tiebreak", contested, tokens_in=800, tokens_out=250)


def _translate_estimate(params: dict[str, Any]) -> float:
    n = max(int(_pending_count(None, params) * 0.4), 0)
    return _role_cost("translate", max((n + 19) // 20, 0), tokens_in=800, tokens_out=800)


def _embed_estimate(params: dict[str, Any]) -> float:
    n = max(_pending_count(None, params), 0)
    return _role_cost("embed", max((n + 99) // 100, 0), tokens_in=120 * 100, tokens_out=0)


def _summarize_estimate(params: dict[str, Any]) -> float:
    return _role_cost("summarize", 1, tokens_in=4000, tokens_out=1200)
