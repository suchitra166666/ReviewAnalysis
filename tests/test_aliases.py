from __future__ import annotations

from rap.llm.aliases import attach_slugs, resolve_competitor


def test_resolve_alias_and_unknown() -> None:
    mapping = {"talabat": "talabat", "طلبات": "talabat", "keeta": "keeta", "كيتا": "keeta"}
    assert resolve_competitor("طلبات", mapping) == "talabat"
    assert resolve_competitor("Keeta", mapping) == "keeta"
    assert resolve_competitor("some other app", mapping) == "unknown"


def test_attach_slugs() -> None:
    mapping = {"keeta": "keeta"}
    out = attach_slugs(
        [{"competitor_raw": "keeta", "comparison": "competitor_better"}], mapping
    )
    assert out[0]["competitor_slug"] == "keeta"
