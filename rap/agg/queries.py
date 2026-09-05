from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Any

from rap.agg.load import (
    CompanySlice,
    Filters,
    LoadedReview,
    journey_of,
    load_slice,
    mention_rows,
    snippet_obj,
    used,
)
from rap.agg.models import (
    CompareMetric,
    CompareOut,
    IntervalOut,
    MetaOut,
    MetricValue,
    OverviewOut,
    StarBucket,
    StarScenarioOut,
    ThemeRow,
)
from rap.agg.stats import difference_ci, momentum, pareto_shares, weighted_share
from rap.agg.themes import kano_for, theme_meta
from rap.llm.summarize import pain_explanation


def _meta(s: CompanySlice) -> MetaOut:
    return MetaOut(
        n_raw=s.n_raw,
        n_used=s.n_used,
        low_confidence=s.low_confidence,
        data_as_of=s.data_as_of,
        company_slug=s.company.slug,
        company_name=s.company.display_name,
        date_from=s.date_from,
        date_to=s.date_to,
    )


def _interval(ci) -> IntervalOut:
    return IntervalOut(low=ci.low, high=ci.high, n_eff=ci.n_eff)


def _metric(value: float | None, n: int, unit: str = "", ci=None) -> MetricValue:
    return MetricValue(value=value, n=n, unit=unit, ci=_interval(ci) if ci else None)


def _weekly_buckets(items: list[LoadedReview]) -> dict[dt.date, list[LoadedReview]]:
    buckets: dict[dt.date, list[LoadedReview]] = defaultdict(list)
    for item in items:
        day = item.raw.review_date.date()
        week = day - dt.timedelta(days=day.weekday())
        buckets[week].append(item)
    return dict(sorted(buckets.items()))


def _share(items: list[LoadedReview], pred) -> tuple[float, Any]:
    flags = [bool(pred(x)) for x in items]
    weights = [x.weight for x in items]
    return weighted_share(flags, weights)


def overview(ident: str | int, date_from=None, date_to=None, filters=None, **kwargs) -> OverviewOut:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    u = used(s)
    reasons: Counter[str] = Counter()
    excluded = 0
    for item in s.loaded:
        if item.flag and item.flag.excluded_from_aggregates:
            excluded += 1
            for reason in item.flag.exclusion_reasons or []:
                reasons[reason] += 1
    if not u:
        empty = _metric(None, 0)
        return OverviewOut(
            meta=_meta(s),
            reviews_analysed=0,
            reviews_scraped=s.n_raw,
            reviews_excluded=excluded,
            exclusion_reasons=dict(reasons),
            analysed_average_rating=empty,
            store_headline_rating=_metric(
                (sum(r.star_rating for r in s.raw) / len(s.raw)) if s.raw else None,
                len(s.raw),
                "★",
            ),
            rating_gap=None,
            positive_pct=empty,
            negative_pct=empty,
            neutral_mixed_pct=empty,
            net_sentiment=empty,
            promo_dependence=empty,
            churn_signal=empty,
            developer_response_rate=empty,
            developer_reply_hours=None,
            agreement_rate=empty,
        )
    wsum = sum(x.weight for x in u) or 1
    analysed = sum(x.raw.star_rating * x.weight for x in u) / wsum
    store = sum(r.star_rating for r in s.raw) / len(s.raw) if s.raw else None
    pos, pos_ci = _share(u, lambda x: x.final and x.final.overall_sentiment == "positive")
    neg, neg_ci = _share(u, lambda x: x.final and x.final.overall_sentiment == "negative")
    neu, neu_ci = _share(
        u, lambda x: x.final and x.final.overall_sentiment in {"neutral", "mixed"}
    )
    positives = [x for x in u if x.final and x.final.overall_sentiment == "positive"]
    promo, promo_ci = _share(positives, lambda x: x.final and x.final.mentions_incentive) if positives else (None, None)
    negatives = [x for x in u if x.final and x.final.overall_sentiment == "negative"]
    churn, churn_ci = _share(negatives, lambda x: x.final and x.final.churn_intent) if negatives else (None, None)
    low_star = [x for x in s.loaded if x.raw.star_rating <= 2]
    replied = [x for x in low_star if x.raw.reply_body]
    reply_rate = (len(replied) / len(low_star)) if low_star else None
    hours: list[float] = []
    for item in replied:
        if item.raw.reply_date:
            hours.append((item.raw.reply_date - item.raw.review_date).total_seconds() / 3600)
    hours.sort()
    median_h = hours[len(hours) // 2] if hours else None
    agreed, agreed_ci = _share(u, lambda x: x.final and x.final.confidence_tier == "agreed")
    weeks = _weekly_buckets(u)
    spark_neg = []
    spark_net = []
    spark_rating = []
    for _week, group in list(weeks.items())[-12:]:
        nshare, _ = _share(group, lambda x: x.final and x.final.overall_sentiment == "negative")
        pshare, _ = _share(group, lambda x: x.final and x.final.overall_sentiment == "positive")
        gw = sum(x.weight for x in group) or 1
        spark_neg.append(nshare)
        spark_net.append(pshare - nshare)
        spark_rating.append(sum(x.raw.star_rating * x.weight for x in group) / gw)
    return OverviewOut(
        meta=_meta(s),
        reviews_analysed=s.n_used,
        reviews_scraped=s.n_raw,
        reviews_excluded=excluded,
        exclusion_reasons=dict(reasons),
        analysed_average_rating=_metric(analysed, s.n_used, "★"),
        store_headline_rating=_metric(store, s.n_raw, "★"),
        rating_gap=(analysed - store) if store is not None else None,
        positive_pct=_metric(pos, s.n_used, "%", pos_ci),
        negative_pct=_metric(neg, s.n_used, "%", neg_ci),
        neutral_mixed_pct=_metric(neu, s.n_used, "%", neu_ci),
        net_sentiment=_metric(pos - neg, s.n_used, "pts", None),
        promo_dependence=_metric(promo, len(positives), "%", promo_ci),
        churn_signal=_metric(churn, len(negatives), "%", churn_ci),
        developer_response_rate=_metric(reply_rate, len(low_star), "%"),
        developer_reply_hours=median_h,
        agreement_rate=_metric(agreed, s.n_used, "%", agreed_ci),
        sparkline_net=spark_net,
        sparkline_neg=spark_neg,
        sparkline_rating=spark_rating,
    )


def star_scenario(ident, date_from=None, date_to=None, filters=None, **kwargs) -> StarScenarioOut:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    u = used(s)
    raw_n = len(s.raw) or 1
    used_n = sum(x.weight for x in u) or 1
    buckets: list[StarBucket] = []
    for star in (5, 4, 3, 2, 1):
        raw_c = sum(1 for r in s.raw if r.star_rating == star)
        used_c = [x for x in u if x.raw.star_rating == star]
        themes = Counter()
        for item in used_c:
            for mention in (item.final.mentions if item.final else []) or []:
                themes[mention.get("theme")] += item.weight
        buckets.append(
            StarBucket(
                stars=star,
                share_weighted=sum(x.weight for x in used_c) / used_n,
                share_raw=raw_c / raw_n,
                n=len(used_c),
                top_themes=[t for t, _ in themes.most_common(3) if t],
            )
        )
    five = [x for x in u if x.raw.star_rating == 5]
    one = [x for x in u if x.raw.star_rating == 1]
    promo = (sum(1 for x in five if x.final and x.final.mentions_incentive) / len(five)) if five else None
    lowinfo = (sum(1 for x in five if x.final and x.final.low_information) / len(five)) if five else None
    recover = receive_wait = 0
    one_themes: Counter[str] = Counter()
    for item in one:
        for mention in (item.final.mentions if item.final else []) or []:
            stage = journey_of(mention)
            if stage == "recover_support":
                recover += 1
            if stage in {"receive", "wait_track"}:
                receive_wait += 1
            if mention.get("sentiment") == "negative":
                one_themes[mention.get("theme") or "other"] += 1
    one_n = max(len(one), 1)
    five_bucket = next(b for b in buckets if b.stars == 5)
    one_top = one_themes.most_common(1)[0][0] if one_themes else None
    lines = [
        f"{{A}}'s 5★ share is {five_bucket.share_weighted:.1%} but {promo or 0:.1%} of those are promo-driven",
        f"{{A}}'s 1★ reviews are mostly about {one_top or 'no dominant theme'}",
        f"{{A}}'s 5★ low-information share is {lowinfo or 0:.1%}",
    ]
    return StarScenarioOut(
        meta=_meta(s),
        buckets=buckets,
        five_star_promo_share=promo,
        five_star_low_info_share=lowinfo,
        one_star_recover_share=recover / one_n if one else None,
        one_star_receive_wait_share=receive_wait / one_n if one else None,
        one_star_top_theme=one_top,
        lines=lines,
    )


def _theme_rows(s: CompanySlice, sentiment: str) -> list[ThemeRow]:
    u = used(s)
    if not u:
        return []
    total_w = sum(x.weight for x in u) or 1
    overall_rating = sum(x.raw.star_rating * x.weight for x in u) / total_w
    grouped: dict[str, list[tuple[LoadedReview, dict]]] = defaultdict(list)
    for item, mention in mention_rows(s):
        grouped[mention.get("theme") or "other"].append((item, mention))
    prior = load_slice(
        s.company.slug,
        s.date_from - (s.date_to - s.date_from),
        s.date_from - dt.timedelta(days=1),
        s.filters,
    )
    prior_neg = _neg_rates(prior)
    rows: list[ThemeRow] = []
    sevs: list[float] = []
    for theme, pairs in grouped.items():
        mentioning = {id(p[0]): p[0] for p in pairs}
        items = list(mentioning.values())
        mention_share = sum(x.weight for x in items) / total_w
        neg_flags = []
        neg_w = []
        pos_w = 0.0
        sub: Counter[str] = Counter()
        snippets = []
        for item, mention in pairs:
            if mention.get("sentiment") == "negative":
                neg_flags.append(True)
                neg_w.append(item.weight)
            else:
                neg_flags.append(False)
                neg_w.append(item.weight)
            if mention.get("sentiment") == "positive":
                pos_w += item.weight
            if mention.get("sub_theme"):
                sub[mention["sub_theme"]] += item.weight
            snippets.append(snippet_obj(item, mention))
        rate, ci = weighted_share(
            [m.get("sentiment") == sentiment for _, m in pairs],
            [i.weight for i, _ in pairs],
        )
        theme_rating = sum(x.raw.star_rating * x.weight for x in items) / (sum(x.weight for x in items) or 1)
        drag = theme_rating - overall_rating
        neg_rate, neg_ci = weighted_share(
            [m.get("sentiment") == "negative" for _, m in pairs],
            [i.weight for i, _ in pairs],
        )
        pos_rate = pos_w / (sum(i.weight for i, _ in pairs) or 1)
        # only a downward pull on the rating counts as cost; a theme rated above average is not a fix
        sev = neg_rate * max(0.0, -drag)
        sevs.append(sev)
        ar_snips = [sn for sn in snippets if sn["language"] in {"ar", "mixed"}]
        chosen = []
        if ar_snips:
            chosen.append(ar_snips[0])
        for sn in snippets:
            if sn not in chosen:
                chosen.append(sn)
            if len(chosen) >= 3:
                break
        meta = theme_meta(theme)
        rows.append(
            ThemeRow(
                theme=theme,
                label=meta.get("label") or theme,
                positive_label=meta.get("positive_label"),
                journey_stage=meta.get("journey_stage"),
                kano=meta.get("kano"),
                mention_share=mention_share,
                n_mentions=len(items),
                negative_rate=neg_rate,
                positive_rate=pos_rate,
                negative_ci=_interval(neg_ci),
                star_drag=drag,
                severity=sev,
                trend=momentum(neg_rate, prior_neg.get(theme, 0.0)),
                top_sub_themes=[k for k, _ in sub.most_common(2)],
                snippets=chosen,
                sparkline=_theme_spark(s, theme),
            )
        )
    max_sev = max(sevs) if sevs else 1.0
    for row in rows:
        if row.severity is not None and max_sev:
            row.severity = row.severity / max_sev
    if sentiment == "negative":
        # ranked by what to fix first: how often it is a complaint x how much it costs in stars
        rows.sort(key=lambda r: (r.severity or 0.0, r.negative_rate), reverse=True)
    else:
        rows.sort(key=lambda r: r.positive_rate, reverse=True)
    for row in rows[:5]:
        row.explanation = pain_explanation(
            row.theme, {"a_rate": row.negative_rate, "b_rate": None}
        )
    return rows


def _neg_rates(s: CompanySlice) -> dict[str, float]:
    grouped: dict[str, list] = defaultdict(list)
    for item, mention in mention_rows(s):
        grouped[mention.get("theme") or "other"].append((item, mention))
    out = {}
    for theme, pairs in grouped.items():
        rate, _ = weighted_share(
            [m.get("sentiment") == "negative" for _, m in pairs],
            [i.weight for i, _ in pairs],
        )
        out[theme] = rate
    return out


def _theme_spark(s: CompanySlice, theme: str) -> list[float]:
    weeks = _weekly_buckets(used(s))
    values = []
    for _week, group in list(weeks.items())[-12:]:
        pairs = []
        for item in group:
            for mention in (item.final.mentions if item.final else []) or []:
                if mention.get("theme") == theme:
                    pairs.append((item, mention))
        if not pairs:
            values.append(0.0)
            continue
        rate, _ = weighted_share(
            [m.get("sentiment") == "negative" for _, m in pairs],
            [i.weight for i, _ in pairs],
        )
        values.append(rate)
    return values


def pain_points(ident, date_from=None, date_to=None, filters=None, **kwargs) -> list[ThemeRow]:
    rows = _theme_rows(load_slice(ident, date_from, date_to, filters, **kwargs), "negative")
    # "other" is the catch-all bucket; nobody can act on it, so it never ranks as a fix
    return [r for r in rows if r.theme != "other"]


STRENGTH_MIN_POSITIVE = 0.5


def strengths(ident, date_from=None, date_to=None, filters=None, **kwargs) -> list[ThemeRow]:
    rows = _theme_rows(load_slice(ident, date_from, date_to, filters, **kwargs), "positive")
    # a theme is only a strength when praise outweighs complaints; "other" is not actionable
    return [r for r in rows if r.theme != "other" and r.positive_rate >= STRENGTH_MIN_POSITIVE]


def theme_matrix(ident, date_from=None, date_to=None, filters=None, **kwargs) -> list[ThemeRow]:
    return _theme_rows(load_slice(ident, date_from, date_to, filters, **kwargs), "negative")


def theme_detail(ident, theme: str, date_from=None, date_to=None, filters=None, page: int = 1, **kwargs) -> dict[str, Any]:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    pairs = [(i, m) for i, m in mention_rows(s) if m.get("theme") == theme]
    sub: Counter[str] = Counter()
    stars: Counter[int] = Counter()
    langs: Counter[str] = Counter()
    snippets = []
    for item, mention in pairs:
        if mention.get("sub_theme"):
            sub[mention["sub_theme"]] += item.weight
        stars[item.raw.star_rating] += 1
        langs[(item.final.language if item.final else "en") or "en"] += 1
        snippets.append(snippet_obj(item, mention))
    start = (page - 1) * 20
    return {
        "meta": _meta(s).model_dump(),
        "theme": theme,
        "label": theme_meta(theme).get("label"),
        "trend": _theme_spark(s, theme),
        "sub_themes": [{"name": k, "weight": v} for k, v in sub.most_common()],
        "stars": dict(stars),
        "languages": dict(langs),
        "snippets": snippets[start : start + 20],
        "n": len(snippets),
        "page": page,
    }


def trends(ident, date_from=None, date_to=None, filters=None, **kwargs) -> dict[str, Any]:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    u = used(s)
    weeks = _weekly_buckets(u)
    series = []
    for week, group in weeks.items():
        neg, _ = _share(group, lambda x: x.final and x.final.overall_sentiment == "negative")
        pos, _ = _share(group, lambda x: x.final and x.final.overall_sentiment == "positive")
        gw = sum(x.weight for x in group) or 1
        series.append(
            {
                "week": week.isoformat(),
                "negative_pct": neg,
                "positive_pct": pos,
                "rating": sum(x.raw.star_rating * x.weight for x in group) / gw,
                "volume": len(group),
            }
        )
    window = int(__import__("rap.settings", fromlist=["get_setting"]).get_setting("aggregation.momentum_window_days", 30) or 30)
    last_start = s.date_to - dt.timedelta(days=window - 1)
    prior_start = last_start - dt.timedelta(days=window)
    last = [x for x in u if x.raw.review_date.date() >= last_start]
    prior = [x for x in u if prior_start <= x.raw.review_date.date() < last_start]
    def pack(items):
        if not items:
            return {"neg": 0.0, "net": 0.0, "vol": 0}
        neg, _ = _share(items, lambda x: x.final and x.final.overall_sentiment == "negative")
        pos, _ = _share(items, lambda x: x.final and x.final.overall_sentiment == "positive")
        return {"neg": neg, "net": pos - neg, "vol": len(items)}
    last_p, prior_p = pack(last), pack(prior)
    bursts = sorted({x.raw.review_date.date().isoformat() for x in s.loaded if x.flag and x.flag.burst_flag})
    return {
        "meta": _meta(s).model_dump(),
        "series": series,
        "momentum": {
            "negative_pct": last_p["neg"] - prior_p["neg"],
            "net_sentiment": last_p["net"] - prior_p["net"],
            "volume": last_p["vol"] - prior_p["vol"],
        },
        "launch_date": s.company.launch_date_ae.isoformat() if s.company.launch_date_ae else None,
        "burst_days": bursts,
    }


def share_of_voice(a, b, date_from=None, date_to=None, filters=None, **kwargs) -> dict[str, Any]:
    sa = load_slice(a, date_from, date_to, filters, other=b, **kwargs)
    sb = load_slice(b, sa.date_from, sa.date_to, filters, **kwargs)
    def weekly(s: CompanySlice) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for item in s.loaded:
            day = item.raw.review_date.date()
            week = (day - dt.timedelta(days=day.weekday())).isoformat()
            counts[week] += 1
        return dict(counts)
    wa, wb = weekly(sa), weekly(sb)
    weeks = sorted(set(wa) | set(wb))
    mean_a = (sum(wa.values()) / len(weeks)) if weeks else 1
    mean_b = (sum(wb.values()) / len(weeks)) if weeks else 1
    return {
        "weeks": [
            {
                "week": w,
                "a_raw": wa.get(w, 0),
                "b_raw": wb.get(w, 0),
                "a_norm": (wa.get(w, 0) / mean_a) if mean_a else 0,
                "b_norm": (wb.get(w, 0) / mean_b) if mean_b else 0,
            }
            for w in weeks
        ]
    }


def complaint_concentration(ident, date_from=None, date_to=None, filters=None, **kwargs) -> dict[str, Any]:
    rows = pain_points(ident, date_from, date_to, filters, **kwargs)
    values = [r.negative_rate * r.mention_share for r in rows]
    shares = pareto_shares(values)
    return {
        "top_1": shares.get(1),
        "top_3": shares.get(3),
        "top_5": shares.get(5),
        "themes": [r.theme for r in rows[:5]],
    }


def language_gap(ident, date_from=None, date_to=None, filters=None, **kwargs) -> dict[str, Any]:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    out = {}
    for lang in ("en", "ar"):
        items = [x for x in used(s) if x.final and x.final.language == lang]
        if not items:
            out[lang] = {"n": 0}
            continue
        pos, _ = _share(items, lambda x: x.final and x.final.overall_sentiment == "positive")
        neg, _ = _share(items, lambda x: x.final and x.final.overall_sentiment == "negative")
        themes: Counter[str] = Counter()
        for item, mention in mention_rows(s, "negative"):
            if item.final and item.final.language == lang:
                themes[mention.get("theme") or "other"] += item.weight
        out[lang] = {
            "n": len(items),
            "positive_pct": pos,
            "negative_pct": neg,
            "top_negative_themes": [t for t, _ in themes.most_common(3)],
        }
    return out


def feedback_types(ident, date_from=None, date_to=None, filters=None, **kwargs) -> dict[str, Any]:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    dist: Counter[str] = Counter()
    backlog: dict[str, list] = defaultdict(list)
    for item in used(s):
        if not item.final:
            continue
        dist[item.final.feedback_type or "other"] += 1
        if item.final.feedback_type in {"feature_request", "bug_report"}:
            themes = [m.get("theme") or "other" for m in item.final.mentions or []] or ["other"]
            for theme in themes:
                backlog[theme].append(
                    {
                        **snippet_obj(item),
                        "feedback_type": item.final.feedback_type,
                        "store": item.raw.store.value,
                    }
                )
    return {"distribution": dict(dist), "backlog": backlog}


def competitor_pull(ident, date_from=None, date_to=None, filters=None, **kwargs) -> dict[str, Any]:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    outbound: dict[str, Counter] = defaultdict(lambda: Counter())
    snippets: dict[str, list] = defaultdict(list)
    for item in used(s):
        if not item.final:
            continue
        for mention in item.final.competitor_mentions or []:
            slug = mention.get("competitor_slug") or "unknown"
            outbound[slug][mention.get("comparison") or "neutral"] += 1
            if len(snippets[slug]) < 3:
                snippets[slug].append(snippet_obj(item))
    # reverse: other companies naming this slug
    inbound: dict[str, Counter] = defaultdict(lambda: Counter())
    inbound_snips: dict[str, list] = defaultdict(list)
    from rap.db.models import Company, ReviewFinal, ReviewRaw
    from rap.db.session import session_scope
    from sqlalchemy import select

    with session_scope() as session:
        others = session.scalars(select(Company).where(Company.slug != s.company.slug, Company.hidden.is_(False))).all()
        for other in others:
            oslice = load_slice(other.slug, s.date_from, s.date_to, s.filters)
            for item in used(oslice):
                if not item.final:
                    continue
                for mention in item.final.competitor_mentions or []:
                    if mention.get("competitor_slug") == s.company.slug:
                        inbound[other.slug][mention.get("comparison") or "neutral"] += 1
                        if len(inbound_snips[other.slug]) < 3:
                            inbound_snips[other.slug].append(snippet_obj(item))
    return {
        "outbound": {k: dict(v) for k, v in outbound.items()},
        "outbound_snippets": {k: v for k, v in snippets.items()},
        "inbound": {k: dict(v) for k, v in inbound.items()},
        "inbound_snippets": {k: v for k, v in inbound_snips.items()},
        "churn_signal": overview(s.company.slug, s.date_from, s.date_to, s.filters).churn_signal.model_dump(),
    }


def review_explorer(
    ident,
    date_from=None,
    date_to=None,
    filters=None,
    theme=None,
    sub_theme=None,
    sentiment=None,
    language=None,
    feedback_type=None,
    churn_intent=None,
    competitor=None,
    flagged=None,
    page: int = 1,
    page_size: int = 25,
    **kwargs,
) -> dict[str, Any]:
    s = load_slice(ident, date_from, date_to, filters, **kwargs)
    rows = []
    for item in s.loaded:
        if item.final is None:
            # explorer lists used or excluded reviews; rows never labelled are neither
            continue
        if flagged is True and not (item.flag and item.flag.excluded_from_aggregates):
            continue
        if flagged is False and item.flag and item.flag.excluded_from_aggregates:
            continue
        if language and item.final and item.final.language != language:
            continue
        if feedback_type and item.final and item.final.feedback_type != feedback_type:
            continue
        if churn_intent is not None and item.final and bool(item.final.churn_intent) != bool(churn_intent):
            continue
        mentions = (item.final.mentions if item.final else []) or []
        if theme and not any(m.get("theme") == theme for m in mentions):
            continue
        if sub_theme and not any(m.get("sub_theme") == sub_theme for m in mentions):
            continue
        if sentiment and item.final and item.final.overall_sentiment != sentiment:
            continue
        if competitor and item.final:
            if not any(
                (m.get("competitor_slug") == competitor) or (m.get("competitor_raw") == competitor)
                for m in item.final.competitor_mentions or []
            ):
                continue
        rows.append(item)
    rows.sort(key=lambda item: item.raw.review_date, reverse=True)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {
        "n": len(rows),
        "page": page,
        "items": [
            {
                "id": item.raw.id,
                "store": item.raw.store.value,
                "date": item.raw.review_date.isoformat(),
                "stars": item.raw.star_rating,
                "title": item.raw.title,
                "body": item.raw.body,
                "title_en": item.translation.title_en if item.translation else None,
                "body_en": item.translation.body_en if item.translation else None,
                "language": item.final.language if item.final else item.raw.language_hint,
                "overall_sentiment": item.final.overall_sentiment if item.final else None,
                "feedback_type": item.final.feedback_type if item.final else None,
                "churn_intent": item.final.churn_intent if item.final else None,
                "mentions": item.final.mentions if item.final else [],
                "excluded": bool(item.flag and item.flag.excluded_from_aggregates),
                "exclusion_reasons": item.flag.exclusion_reasons if item.flag else [],
                "used": item.used,
            }
            for item in page_rows
        ],
    }


def watch_list(ident, date_from=None, date_to=None, filters=None, **kwargs) -> list[str]:
    rows = pain_points(ident, date_from, date_to, filters, **kwargs)
    ranked = sorted(rows, key=lambda r: r.trend or 0, reverse=True)
    return [r.theme for r in ranked[:3]]


def _sample_caption(a: str, b: str, usable_a: int, usable_b: int, used_a: int, used_b: int) -> dict[str, Any] | None:
    from rap.db.models import Job
    from rap.db.session import session_scope
    from sqlalchemy import select

    extract_kinds = {"extract_a", "extract_b", "full_pipeline"}
    with session_scope() as session:
        for job in session.scalars(select(Job).order_by(Job.id.desc()).limit(50)):
            params = job.params or {}
            slugs = list(params.get("slugs") or [params.get("a"), params.get("b")])
            if a not in slugs or b not in slugs:
                continue
            kind = job.kind.value if hasattr(job.kind, "value") else str(job.kind)
            stages = params.get("stages") or []
            touches_extract = kind in extract_kinds and (
                not stages or any(s in ("extract_a", "extract_b") for s in stages)
            )
            if not touches_extract:
                continue
            n = params.get("sample_n")
            per_star = params.get("sample_per_star")
            if not n and not per_star:
                return None
            per_company = int(n or int(per_star) * 5)
            return {
                "used": True,
                "n_a": min(per_company, usable_a or per_company),
                "n_b": min(per_company, usable_b or per_company),
                "usable_a": usable_a,
                "usable_b": usable_b,
            }
    if used_a and usable_a and used_a < usable_a:
        return {
            "used": True,
            "n_a": used_a,
            "n_b": used_b,
            "usable_a": usable_a,
            "usable_b": usable_b,
        }
    return None


def compare(a, b, date_from=None, date_to=None, filters=None, since_launch: bool = False, **kwargs) -> CompareOut:
    sa = load_slice(a, date_from, date_to, filters, since_launch=since_launch, other=b)
    sb = load_slice(b, sa.date_from, sa.date_to, filters)
    oa, ob = overview(a, sa.date_from, sa.date_to, filters), overview(b, sa.date_from, sa.date_to, filters)
    launch_note = None
    if since_launch and (not sa.company.launch_date_ae or not sb.company.launch_date_ae):
        launch_note = "Since the later launch is unavailable because one company has no launch date."
        if not since_launch:
            pass
    if since_launch and (sa.company.launch_date_ae is None or sb.company.launch_date_ae is None):
        launch_note = "Since the later launch is hidden because one company has no launch_date_ae."

    def pair(key, av, bv, unit, lower_is_better=False, ci_a=None, ci_b=None):
        delta = None if av is None or bv is None else av - bv
        better = None
        if delta is not None:
            if abs(delta) < 1e-12:
                better = None
            elif lower_is_better:
                better = "a" if av < bv else "b"
            else:
                better = "a" if av > bv else "b"
        ci = None
        if ci_a and ci_b and av is not None and bv is not None:
            from rap.agg.stats import Interval

            ci = difference_ci(av, Interval(ci_a.low, ci_a.high, ci_a.n_eff), bv, Interval(ci_b.low, ci_b.high, ci_b.n_eff))
            ci = _interval(ci)
        return CompareMetric(key=key, a=av, b=bv, delta=delta, ci=ci, better=better)

    deltas = [
        pair("reviews_analysed", oa.reviews_analysed, ob.reviews_analysed, "n"),
        pair(
            "analysed_average_rating",
            oa.analysed_average_rating.value,
            ob.analysed_average_rating.value,
            "★",
        ),
        pair("positive_pct", oa.positive_pct.value, ob.positive_pct.value, "%", ci_a=oa.positive_pct.ci, ci_b=ob.positive_pct.ci),
        pair(
            "negative_pct",
            oa.negative_pct.value,
            ob.negative_pct.value,
            "%",
            lower_is_better=True,
            ci_a=oa.negative_pct.ci,
            ci_b=ob.negative_pct.ci,
        ),
        pair("net_sentiment", oa.net_sentiment.value, ob.net_sentiment.value, "pts"),
        pair(
            "promo_dependence",
            oa.promo_dependence.value,
            ob.promo_dependence.value,
            "%",
            lower_is_better=True,
        ),
    ]
    return CompareOut(
        a={
            "overview": oa.model_dump(),
            "star_scenario": star_scenario(a, sa.date_from, sa.date_to, filters).model_dump(),
            "pain_points": [r.model_dump() for r in pain_points(a, sa.date_from, sa.date_to, filters)[:5]],
            "strengths": [r.model_dump() for r in strengths(a, sa.date_from, sa.date_to, filters)[:3]],
            "theme_matrix": [r.model_dump() for r in theme_matrix(a, sa.date_from, sa.date_to, filters)],
            "trends": trends(a, sa.date_from, sa.date_to, filters),
            "language_gap": language_gap(a, sa.date_from, sa.date_to, filters),
            "feedback_types": feedback_types(a, sa.date_from, sa.date_to, filters),
            "competitor_pull": competitor_pull(a, sa.date_from, sa.date_to, filters),
            "complaint_concentration": complaint_concentration(a, sa.date_from, sa.date_to, filters),
            "watch_list": watch_list(a, sa.date_from, sa.date_to, filters),
        },
        b={
            "overview": ob.model_dump(),
            "star_scenario": star_scenario(b, sa.date_from, sa.date_to, filters).model_dump(),
            "pain_points": [r.model_dump() for r in pain_points(b, sa.date_from, sa.date_to, filters)[:5]],
            "strengths": [r.model_dump() for r in strengths(b, sa.date_from, sa.date_to, filters)[:3]],
            "theme_matrix": [r.model_dump() for r in theme_matrix(b, sa.date_from, sa.date_to, filters)],
            "trends": trends(b, sa.date_from, sa.date_to, filters),
            "language_gap": language_gap(b, sa.date_from, sa.date_to, filters),
            "feedback_types": feedback_types(b, sa.date_from, sa.date_to, filters),
            "competitor_pull": competitor_pull(b, sa.date_from, sa.date_to, filters),
            "complaint_concentration": complaint_concentration(b, sa.date_from, sa.date_to, filters),
            "watch_list": watch_list(b, sa.date_from, sa.date_to, filters),
        },
        deltas=deltas,
        since_launch=since_launch,
        date_from=sa.date_from,
        date_to=sa.date_to,
        launch_note=launch_note,
        sample=_sample_caption(a, b, sa.n_raw, sb.n_raw, oa.meta.n_used, ob.meta.n_used),
    )
