from __future__ import annotations

from rap.agg.frameworks import importance_performance


def test_quadrant_assignment(monkeypatch) -> None:
    class Row:
        def __init__(self, theme, mention_share, positive_rate, negative_rate):
            self.theme = theme
            self.label = theme
            self.mention_share = mention_share
            self.positive_rate = positive_rate
            self.negative_rate = negative_rate
            self.negative_ci = None

    rows_a = [
        Row("late_delivery", 0.4, 0.1, 0.8),
        Row("promotions", 0.4, 0.8, 0.1),
        Row("app_bugs", 0.05, 0.1, 0.7),
        Row("rider_behaviour", 0.05, 0.9, 0.05),
    ]

    def fake_load(*args, **kwargs):
        class S:
            date_from = __import__("datetime").date(2026, 1, 1)
            date_to = __import__("datetime").date(2026, 3, 1)

        return S()

    monkeypatch.setattr("rap.agg.frameworks.load_slice", fake_load)
    monkeypatch.setattr("rap.agg.frameworks.theme_matrix", lambda ident, *a, **k: rows_a)
    monkeypatch.setattr("rap.agg.frameworks.get_setting", lambda key, default=None: default)
    out = importance_performance("a", "b")
    by_theme = {p["theme"]: p["quadrant"] for p in out["a"]}
    assert by_theme["late_delivery"] == "fix_now"
    assert by_theme["promotions"] == "protect"
    assert by_theme["app_bugs"] == "monitor"
    assert by_theme["rider_behaviour"] == "nice_to_have"
