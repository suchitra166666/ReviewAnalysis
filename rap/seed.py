from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from rap.db.models import ApiCredential, AppSetting, Company, SettingValueType
from rap.paths import CONFIG_DIR


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def seed_if_empty(session: Session) -> None:
    """Read config YAML once on first run. Later edits to YAML do nothing."""
    existing = session.scalar(select(AppSetting).limit(1))
    if existing is None:
        seed_settings(session)
        seed_providers(session)
    existing_company = session.scalar(select(Company).limit(1))
    if existing_company is None:
        seed_companies(session)


def seed_settings(session: Session, replace: bool = False) -> None:
    data = load_yaml(CONFIG_DIR / "settings_defaults.yaml")
    for item in data.get("settings", []):
        row = session.get(AppSetting, item["key"])
        if row is None:
            session.add(
                AppSetting(
                    key=item["key"],
                    value=item["value"],
                    value_type=SettingValueType(item["value_type"]),
                    group=item["group"],
                    label=item["label"],
                    description=item["description"],
                )
            )
        elif replace:
            row.value = item["value"]
            row.value_type = SettingValueType(item["value_type"])
            row.group = item["group"]
            row.label = item["label"]
            row.description = item["description"]


def seed_providers(session: Session) -> None:
    data = load_yaml(CONFIG_DIR / "models.yaml")
    for slug, spec in (data.get("providers") or {}).items():
        existing = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if existing:
            continue
        session.add(
            ApiCredential(
                provider_slug=slug,
                display_name=spec["display_name"],
                base_url=spec["base_url"],
                api_key_encrypted=None,
                key_last4=None,
                is_openai_compatible=spec.get("is_openai_compatible", True),
                supports_batch=spec.get("supports_batch", False),
                supports_structured_outputs=spec.get("supports_structured_outputs", False),
                disable_thinking=spec.get("disable_thinking", False),
            )
        )


def seed_companies(session: Session, replace: bool = False) -> None:
    data = load_yaml(CONFIG_DIR / "companies.yaml")
    for item in data.get("companies", []):
        launch = item.get("launch_date_ae")
        launch_date = dt.date.fromisoformat(launch) if launch else None
        existing = session.scalar(select(Company).where(Company.slug == item["slug"]))
        if existing is None:
            session.add(
                Company(
                    slug=item["slug"],
                    display_name=item["display_name"],
                    appstore_id=item.get("appstore_id"),
                    play_package=item.get("play_package"),
                    launch_date_ae=launch_date,
                    is_super_app=bool(item.get("is_super_app", False)),
                    aliases=list(item.get("aliases") or []),
                    notes=item.get("notes"),
                )
            )
        elif replace:
            existing.display_name = item["display_name"]
            existing.appstore_id = item.get("appstore_id")
            existing.play_package = item.get("play_package")
            existing.launch_date_ae = launch_date
            existing.is_super_app = bool(item.get("is_super_app", False))
            existing.aliases = list(item.get("aliases") or [])
            existing.notes = item.get("notes")
            existing.hidden = False
