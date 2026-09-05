from __future__ import annotations

from rap.agg.stats import difference_ci, effective_n, momentum, pareto_shares, wilson_interval
from rap.agg.weights import star_weights
from rap.flags.incentivized import cosine
from rap.llm.client import estimate_cost


def test_star_weights_round_trip() -> None:
    true = {1: 20, 2: 20, 3: 20, 4: 20, 5: 20}
    sample = {1: 10, 2: 10, 3: 10, 4: 10, 5: 10}
    result = star_weights(true, sample)
    assert result.weights[5] == 1.0
    assert not result.warnings


def test_zero_bucket_warning() -> None:
    true = {1: 10, 2: 10, 3: 0, 4: 0, 5: 80}
    sample = {1: 5, 2: 0, 3: 0, 4: 0, 5: 5}
    result = star_weights(true, sample)
    assert result.weights[2] == 0.0
    assert any("star 2" in w for w in result.warnings)


def test_wilson_and_diff() -> None:
    ci = wilson_interval(20, 100)
    assert 0 < ci.low < 0.2 < ci.high < 1
    other = wilson_interval(40, 100)
    diff = difference_ci(0.2, ci, 0.4, other)
    assert diff.high < 0
    assert effective_n([1, 1, 1, 1]) == 4


def test_pareto_and_momentum() -> None:
    shares = pareto_shares([50, 30, 10, 5, 5])
    assert shares[1] == 0.5
    assert abs(shares[3] - 0.9) < 1e-9
    assert momentum(0.22, 0.15) == 0.07


def test_cosine_and_cost() -> None:
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
    # 1M input tokens at $2 / 1M = $2 if pricing present; function must not crash
    cost = estimate_cost("unknown-model", 1_000_000, 0)
    assert cost == 0.0
