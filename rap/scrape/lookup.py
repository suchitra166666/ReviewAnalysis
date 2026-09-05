from __future__ import annotations

from typing import Any

import httpx

from rap.settings import get_setting


def lookup_company_ids(name: str, country: str | None = None) -> dict[str, list[dict[str, Any]]]:
    country = country or str(get_setting("scraping.country_code", "ae") or "ae")
    return {
        "appstore": _lookup_appstore(name, country),
        "play": _lookup_play(name, country),
    }


def _lookup_appstore(name: str, country: str) -> list[dict[str, Any]]:
    url = "https://itunes.apple.com/search"
    params = {"term": name, "country": country, "entity": "software", "limit": 8}
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for item in data.get("results", []):
        out.append(
            {
                "name": item.get("trackName"),
                "appstore_id": str(item.get("trackId") or ""),
                "publisher": item.get("sellerName"),
                "store_url": item.get("trackViewUrl"),
            }
        )
    return out


def _lookup_play(name: str, country: str) -> list[dict[str, Any]]:
    try:
        from google_play_scraper import search

        results = search(name, lang="en", country=country, n_hits=8)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for item in results or []:
        out.append(
            {
                "name": item.get("title"),
                "play_package": item.get("appId"),
                "publisher": item.get("developer"),
                "store_url": f"https://play.google.com/store/apps/details?id={item.get('appId')}&gl={country}",
            }
        )
    return out
