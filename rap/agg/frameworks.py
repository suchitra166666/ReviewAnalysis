from __future__ import annotations

from collections import defaultdict
from typing import Any

from rap.agg.load import journey_of, load_slice, mention_rows, snippet_obj, used
from rap.agg.queries import _share, theme_matrix
from rap.agg.stats import weighted_share
from rap.agg.themes import kano_for, theme_catalog
from rap.settings import get_setting


def journey_map(a, b, date_from=None, date_to=None, filters=None, since_launch=False, **kwargs) -> dict[str, Any]:
    sa = load_slice(a, date_from, date_to, filters, since_launch=since_launch, other=b)
    sb = load_slice(b, sa.date_from, sa.date_to, filters)
    stages = theme_catalog().get("journey_stages") or []
    return {
        "date_from": sa.date_from.isoformat(),
        "date_to": sa.date_to.isoformat(),
        "a": _journey_side(sa, stages),
        "b": _journey_side(sb, stages),
        "stages": stages,
    }


def _journey_side(s, stages: list[str]) -> dict[str, Any]:
    neg_pairs = mention_rows(s, "negative")
    total_neg_w = sum(item.weight for item, _ in neg_pairs) or 1
    by_stage: dict[str, list] = {st: [] for st in stages}
    for item, mention in neg_pairs:
        stage = journey_of(mention)
        if stage in by_stage:
            by_stage[stage].append((item, mention))
    cells = []
    peak = None
    peak_share = -1.0
    for stage in stages:
        pairs = by_stage[stage]
        share = sum(i.weight for i, _ in pairs) / total_neg_w
        u = used(s)
        stage_items = {id(i): i for i, _ in pairs}
        # negative rate among all used reviews that mention a theme in this stage
        mentioned = []
        for item in u:
            hit = False
            for mention in (item.final.mentions if item.final else []) or []:
                if journey_of(mention) == stage:
                    hit = True
                    break
            if hit:
                mentioned.append(item)
        if mentioned:
            rate, _ = _share(mentioned, lambda x: x.final and x.final.overall_sentiment == "negative")
            pos, _ = _share(mentioned, lambda x: x.final and x.final.overall_sentiment == "positive")
            net = pos - rate
        else:
            rate, net = 0.0, 0.0
        themes = defaultdict(float)
        for item, mention in pairs:
            themes[mention.get("theme") or "other"] += item.weight
        top_theme = max(themes, key=themes.get) if themes else None
        top_snip = snippet_obj(pairs[0][0], pairs[0][1]) if pairs else None
        if share > peak_share:
            peak_share = share
            peak = stage
        cells.append(
            {
                "stage": stage,
                "negative_rate": rate,
                "complaint_share": share,
                "net_sentiment": net,
                "top_theme": top_theme,
                "snippet": top_snip,
            }
        )
    return {"cells": cells, "peak_stage": peak}


def kano_view(a, b, date_from=None, date_to=None, filters=None, since_launch=False, **kwargs) -> dict[str, Any]:
    sa = load_slice(a, date_from, date_to, filters, since_launch=since_launch, other=b)
    sb = load_slice(b, sa.date_from, sa.date_to, filters)
    return {
        "a": _kano_side(sa),
        "b": _kano_side(sb),
        "promo_ended_rising": _promo_ended_rising(sa) or _promo_ended_rising(sb),
    }


def _kano_side(s) -> dict[str, Any]:
    classes = theme_catalog().get("kano_classes") or []
    neg_pairs = mention_rows(s, "negative")
    total_neg = sum(i.weight for i, _ in neg_pairs) or 1
    out = []
    for klass in classes:
        class_neg = [(i, m) for i, m in neg_pairs if kano_for(m.get("theme") or "") == klass]
        themes = sorted({m.get("theme") for _, m in class_neg if m.get("theme")})
        mentioned = []
        for item in used(s):
            if any(kano_for(m.get("theme") or "") == klass for m in (item.final.mentions if item.final else []) or []):
                mentioned.append(item)
        if mentioned:
            neg, _ = _share(mentioned, lambda x: x.final and x.final.overall_sentiment == "negative")
            pos, _ = _share(mentioned, lambda x: x.final and x.final.overall_sentiment == "positive")
        else:
            neg = pos = 0.0
        out.append(
            {
                "kano": klass,
                "negative_rate": neg,
                "positive_rate": pos,
                "complaint_share": sum(i.weight for i, _ in class_neg) / total_neg,
                "themes": themes,
            }
        )
    return {"classes": out}


def _promo_ended_rising(s) -> bool:
    current = 0.0
    prior = 0.0
    mid = s.date_from + (s.date_to - s.date_from) / 2
    for item, mention in mention_rows(s):
        if mention.get("theme") == "promotions" and mention.get("sub_theme") == "promo_ended_complaint":
            if item.raw.review_date.date() >= mid:
                current += item.weight
            else:
                prior += item.weight
    return current > prior and current > 0


def importance_performance(a, b, date_from=None, date_to=None, filters=None, since_launch=False, **kwargs) -> dict[str, Any]:
    sa = load_slice(a, date_from, date_to, filters, since_launch=since_launch, other=b)
    rows_a = theme_matrix(a, sa.date_from, sa.date_to, filters)
    rows_b = theme_matrix(b, sa.date_from, sa.date_to, filters)
    mentions = [r.mention_share for r in rows_a + rows_b]
    mentions_sorted = sorted(mentions)
    if get_setting("aggregation.ipa_mention_threshold", "median") == "median" and mentions_sorted:
        mid = mentions_sorted[len(mentions_sorted) // 2]
    else:
        mid = 0.0
    sent_t = float(get_setting("aggregation.ipa_sentiment_threshold", 0) or 0)

    def pack(rows):
        points = []
        for row in rows:
            net = row.positive_rate - row.negative_rate
            if row.mention_share >= mid and net <= sent_t:
                quad = "fix_now"
            elif row.mention_share >= mid and net > sent_t:
                quad = "protect"
            elif row.mention_share < mid and net <= sent_t:
                quad = "monitor"
            else:
                quad = "nice_to_have"
            points.append(
                {
                    "theme": row.theme,
                    "label": row.label,
                    "mention_share": row.mention_share,
                    "net_sentiment_within_mentions": net,
                    "quadrant": quad,
                    "n": row.negative_ci.n_eff if row.negative_ci else 0,
                }
            )
        return points

    return {
        "a": pack(rows_a),
        "b": pack(rows_b),
        "mention_threshold": mid,
        "sentiment_threshold": sent_t,
    }
