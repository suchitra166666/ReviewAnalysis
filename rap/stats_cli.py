from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rap.db.models import Company, ReviewExtracted, ReviewFinal, ReviewFlag, ReviewRaw, ReviewTranslation
from rap.db.session import session_scope


def raw_stats(session: Session | None = None) -> list[dict[str, Any]]:
    def _run(s: Session) -> list[dict[str, Any]]:
        companies = s.scalars(select(Company).where(Company.hidden.is_(False)).order_by(Company.slug)).all()
        out: list[dict[str, Any]] = []
        for company in companies:
            reviews = s.scalars(select(ReviewRaw).where(ReviewRaw.company_id == company.id)).all()
            if not reviews:
                out.append(
                    {
                        "slug": company.slug,
                        "display_name": company.display_name,
                        "stores": {},
                        "n": 0,
                    }
                )
                continue
            by_store: dict[str, dict[str, Any]] = {}
            for store in ("appstore", "play"):
                subset = [r for r in reviews if r.store.value == store]
                if not subset:
                    continue
                stars = Counter(r.star_rating for r in subset)
                low = [r for r in subset if r.star_rating <= 2]
                replied = [r for r in low if r.reply_body]
                dates = [r.review_date for r in subset]
                by_store[store] = {
                    "n": len(subset),
                    "date_from": min(dates).date().isoformat(),
                    "date_to": max(dates).date().isoformat(),
                    "stars": {str(k): stars[k] for k in sorted(stars)},
                    "reply_rate_1_2": (len(replied) / len(low)) if low else None,
                }
            out.append(
                {
                    "slug": company.slug,
                    "display_name": company.display_name,
                    "n": len(reviews),
                    "stores": by_store,
                }
            )
        return out

    if session is not None:
        return _run(session)
    with session_scope() as scoped:
        return _run(scoped)


def quality_stats() -> list[dict[str, Any]]:
    with session_scope() as session:
        companies = session.scalars(select(Company).where(Company.hidden.is_(False))).all()
        out: list[dict[str, Any]] = []
        for company in companies:
            finals = session.scalars(
                select(ReviewFinal).join(ReviewRaw, ReviewFinal.review_id == ReviewRaw.id).where(
                    ReviewRaw.company_id == company.id
                )
            ).all()
            if not finals:
                continue
            extracted = session.scalars(
                select(ReviewExtracted).join(ReviewRaw, ReviewExtracted.review_id == ReviewRaw.id).where(
                    ReviewRaw.company_id == company.id
                )
            ).all()
            translations = session.scalar(
                select(func.count())
                .select_from(ReviewTranslation)
                .join(ReviewRaw, ReviewTranslation.review_id == ReviewRaw.id)
                .where(ReviewRaw.company_id == company.id)
            ) or 0
            need_tr = sum(1 for f in finals if f.language in {"ar", "mixed", "other"})
            agreed = sum(1 for f in finals if f.confidence_tier == "agreed")
            contested_themes: Counter[str] = Counter()
            for f in finals:
                for theme in f.disagreement_themes or []:
                    contested_themes[theme] += 1
            invalid = sum(1 for e in extracted if not e.schema_valid)
            low_info = sum(1 for f in finals if f.low_information)
            mismatch = sum(1 for f in finals if f.rating_text_mismatch)
            non_food = sum(1 for f in finals if f.is_food_related is False)
            out.append(
                {
                    "slug": company.slug,
                    "n": len(finals),
                    "agreement_rate": agreed / len(finals) if finals else None,
                    "contested_by_theme": dict(contested_themes),
                    "schema_invalid_rate": invalid / len(extracted) if extracted else None,
                    "low_information_rate": low_info / len(finals),
                    "mismatch_rate": mismatch / len(finals),
                    "non_food_rate": non_food / len(finals),
                    "translation_coverage": (translations / need_tr) if need_tr else 1.0,
                }
            )
        return out


def exclusion_stats() -> list[dict[str, Any]]:
    with session_scope() as session:
        companies = session.scalars(select(Company).where(Company.hidden.is_(False))).all()
        out: list[dict[str, Any]] = []
        for company in companies:
            flags = session.scalars(
                select(ReviewFlag).join(ReviewRaw, ReviewFlag.review_id == ReviewRaw.id).where(
                    ReviewRaw.company_id == company.id
                )
            ).all()
            if not flags:
                continue
            reasons: Counter[str] = Counter()
            excluded = 0
            for flag in flags:
                if flag.excluded_from_aggregates:
                    excluded += 1
                    for reason in flag.exclusion_reasons or []:
                        reasons[reason] += 1
            out.append(
                {
                    "slug": company.slug,
                    "n_flagged": len(flags),
                    "n_excluded": excluded,
                    "reasons": dict(reasons),
                }
            )
        return out
