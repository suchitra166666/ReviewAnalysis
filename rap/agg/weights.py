from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass
class WeightResult:
    weights: dict[int, float]
    warnings: list[str]


def star_weights(true_counts: dict[int, int], sample_counts: dict[int, int]) -> WeightResult:
    """Post-stratification by star bucket: weight = true_share / sample_share."""
    true_n = sum(true_counts.values()) or 1
    sample_n = sum(sample_counts.values()) or 1
    weights: dict[int, float] = {}
    warnings: list[str] = []
    for star in (1, 2, 3, 4, 5):
        true_share = true_counts.get(star, 0) / true_n
        sample_share = sample_counts.get(star, 0) / sample_n
        if sample_share == 0:
            weights[star] = 0.0
            if true_share > 0:
                warnings.append(f"star {star} present in raw but absent from used sample")
        else:
            weights[star] = true_share / sample_share
    return WeightResult(weights=weights, warnings=warnings)


def apply_weight(star: int, weights: dict[int, float], weighted: bool) -> float:
    if not weighted:
        return 1.0
    return float(weights.get(star, 1.0))


def counts_from(stars: list[int]) -> dict[int, int]:
    c = Counter(stars)
    return {k: c.get(k, 0) for k in (1, 2, 3, 4, 5)}
