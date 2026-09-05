from __future__ import annotations

from functools import lru_cache
from typing import Any

from rap.paths import CONFIG_DIR
from rap.seed import load_yaml


@lru_cache
def theme_catalog() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "themes.yaml")


def theme_meta(theme: str) -> dict[str, Any]:
    return (theme_catalog().get("themes") or {}).get(theme) or {
        "label": theme.replace("_", " "),
        "journey_stage": None,
        "kano": None,
        "sub_themes": [],
    }


def journey_for(theme: str, sub_theme: str | None = None) -> str | None:
    meta = theme_meta(theme)
    overrides = meta.get("stage_overrides") or {}
    if sub_theme and sub_theme in overrides:
        return overrides[sub_theme]
    return meta.get("journey_stage")


def kano_for(theme: str) -> str | None:
    return theme_meta(theme).get("kano")


@lru_cache
def metrics_catalog() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "metrics.yaml").get("metrics") or {}
