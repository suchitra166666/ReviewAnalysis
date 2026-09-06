from rap.visitors import normalize_visitor_id


def test_normalize_visitor_id_accepts_uuid() -> None:
    assert normalize_visitor_id("550e8400-E29B-41d4-A716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"


def test_normalize_visitor_id_rejects_junk() -> None:
    assert normalize_visitor_id(None) is None
    assert normalize_visitor_id("not-a-uuid") is None
    assert normalize_visitor_id("sk-live-host-key") is None
