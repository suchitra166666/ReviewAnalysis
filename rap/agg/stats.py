from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Interval:
    low: float
    high: float
    n_eff: float


def effective_n(weights: list[float]) -> float:
    if not weights:
        return 0.0
    s = sum(weights)
    s2 = sum(w * w for w in weights)
    if s2 == 0:
        return 0.0
    return (s * s) / s2


def wilson_interval(successes: float, n: float, z: float = 1.96) -> Interval:
    """Wilson score interval. `successes` may be a weighted count; n is effective n."""
    if n <= 0:
        return Interval(0.0, 0.0, 0.0)
    p = max(0.0, min(1.0, successes / n))
    z2 = z * z
    denom = 1 + z2 / n
    centre = p + z2 / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n)
    return Interval(max(0.0, (centre - margin) / denom), min(1.0, (centre + margin) / denom), n)


def weighted_share(flags: list[bool], weights: list[float]) -> tuple[float, Interval]:
    if not flags:
        return 0.0, Interval(0.0, 0.0, 0.0)
    n_eff = effective_n(weights)
    successes = sum(w for flag, w in zip(flags, weights, strict=True) if flag)
    total = sum(weights) or 1.0
    share = successes / total
    # scale successes into effective-n units
    return share, wilson_interval(share * n_eff, n_eff)


def difference_ci(a: float, a_ci: Interval, b: float, b_ci: Interval) -> Interval:
    """Approximate difference CI using independent Wilson half-widths."""
    a_half = (a_ci.high - a_ci.low) / 2
    b_half = (b_ci.high - b_ci.low) / 2
    half = math.sqrt(a_half * a_half + b_half * b_half)
    delta = a - b
    return Interval(delta - half, delta + half, min(a_ci.n_eff, b_ci.n_eff))


def pareto_shares(values: list[float], ks: tuple[int, ...] = (1, 3, 5)) -> dict[int, float]:
    total = sum(values) or 1.0
    ordered = sorted(values, reverse=True)
    out: dict[int, float] = {}
    running = 0.0
    for i, value in enumerate(ordered, start=1):
        running += value
        if i in ks:
            out[i] = running / total
    for k in ks:
        out.setdefault(k, running / total)
    return out


def momentum(current: float, prior: float) -> float:
    return current - prior
