from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from rap.scrape.appstore import parse_appstore_review
from rap.scrape.normalize import dedupe_reviews, should_stop_incremental, to_jsonable
from rap.scrape.play import fetch_play_reviews, parse_play_review

FIX = Path(__file__).parent / "fixtures"


def test_play_parse_and_dedupe() -> None:
    raw = json.loads((FIX / "play_page.json").read_text())
    parsed = [parse_play_review(r, language_hint="en") for r in raw]
    assert parsed[0].store == "play"
    assert parsed[0].store_review_id == "gp-1"
    assert parsed[0].star_rating == 2
    assert parsed[0].reply_body == "Sorry about that"
    unique = dedupe_reviews(parsed)
    assert len(unique) == 2
    assert {r.store_review_id for r in unique} == {"gp-1", "gp-2"}


def test_appstore_rss_parse() -> None:
    raw = json.loads((FIX / "appstore_rss.json").read_text())
    first = parse_appstore_review(raw[0])
    assert first.store == "appstore"
    assert first.store_review_id == "as-1"
    assert first.star_rating == 1
    assert "متأخر" in first.body
    assert first.language_hint in {"ar", "mixed"}


def test_play_raw_json_is_serializable() -> None:
    payload = to_jsonable(
        {
            "at": dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc),
            "nested": {"repliedAt": dt.date(2026, 1, 2)},
        }
    )
    json.dumps(payload)
    assert payload["at"].startswith("2026-01-02")


def test_incremental_stop() -> None:
    page = ["a", "b", "c"]
    assert should_stop_incremental(page, {"a", "b", "c"}, full=False) is True
    assert should_stop_incremental(page, {"a", "b"}, full=False) is False
    assert should_stop_incremental(page, {"a", "b", "c"}, full=True) is False


def test_play_fetch_injects_and_stops() -> None:
    calls = {"n": 0}

    def fake(package, country, lang, token, count):
        calls["n"] += 1
        page = [{"reviewId": "seen-1", "content": "x", "score": 4, "at": "2026-01-01T00:00:00Z"}]
        return page, None

    rows, pages = fetch_play_reviews(
        "pkg",
        country="ae",
        languages=["en"],
        delay_seconds=0,
        max_pages=5,
        seen_ids={"seen-1"},
        full=False,
        fetch_page=fake,
        sleep_fn=lambda _s: None,
    )
    assert pages == 1
    assert rows[0].store_review_id == "seen-1"
    assert calls["n"] == 1
