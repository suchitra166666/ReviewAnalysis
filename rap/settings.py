from __future__ import annotations

import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from rap.db.models import ApiCredential, AppSetting, SettingValueType
from rap.db.session import session_scope
from rap.env import settings_encryption_key
from rap.seed import seed_if_empty

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings_encryption_key()
        try:
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as exc:
            raise RuntimeError(
                "SETTINGS_ENCRYPTION_KEY is not a valid Fernet key. Run `make init`."
            ) from exc
    return _fernet


def encrypt_key(plain: str) -> bytes:
    return _get_fernet().encrypt(plain.encode("utf-8"))


def decrypt_key(blob: bytes) -> str:
    try:
        return _get_fernet().decrypt(blob).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Could not decrypt a stored API key. SETTINGS_ENCRYPTION_KEY may have changed."
        ) from exc


def _rename_concurrency_setting(session: Session) -> None:
    old = session.get(AppSetting, "extraction.concurrency")
    if old is None:
        return
    session.flush()
    new = session.get(AppSetting, "extraction.llm_concurrency")
    if new is None:
        session.add(
            AppSetting(
                key="extraction.llm_concurrency",
                value=old.value,
                value_type=old.value_type,
                group=old.group,
                label="LLM concurrency",
                description="Parallel LLM calls per provider. Applies to OpenAI and DeepSeek.",
            )
        )
    session.delete(old)


def invalidate_cache() -> None:
    _cache.clear()


def bootstrap(session: Session | None = None) -> None:
    from rap.seed import seed_settings

    if session is not None:
        seed_if_empty(session)
        seed_settings(session)
        session.flush()
        _rename_concurrency_setting(session)
        _reload_cache(session)
        return
    with session_scope() as scoped:
        seed_if_empty(scoped)
        seed_settings(scoped)
        scoped.flush()
        _rename_concurrency_setting(scoped)
        _reload_cache(scoped)


def _reload_cache(session: Session) -> None:
    _cache.clear()
    for row in session.scalars(select(AppSetting)).all():
        _cache[row.key] = row.value


def _load_yaml_defaults() -> None:
    from rap.seed import load_yaml
    from rap.paths import CONFIG_DIR

    data = load_yaml(CONFIG_DIR / "settings_defaults.yaml")
    for item in data.get("settings", []):
        _cache.setdefault(item["key"], item["value"])


def get_setting(key: str, default: Any = None) -> Any:
    if not _cache:
        try:
            bootstrap()
        except Exception:
            _load_yaml_defaults()
    return _cache.get(key, default)


def get_settings_group(group: str) -> dict[str, Any]:
    if not _cache:
        bootstrap()
    with session_scope() as session:
        rows = session.scalars(select(AppSetting).where(AppSetting.group == group)).all()
        return {
            row.key: {
                "key": row.key,
                "value": row.value,
                "value_type": row.value_type.value,
                "group": row.group,
                "label": row.label,
                "description": row.description,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        }


def list_settings() -> list[dict[str, Any]]:
    if not _cache:
        bootstrap()
    with session_scope() as session:
        rows = session.scalars(select(AppSetting).order_by(AppSetting.group, AppSetting.key)).all()
        defaults = _default_map()
        return [
            {
                "key": row.key,
                "value": row.value,
                "default": defaults.get(row.key),
                "value_type": row.value_type.value,
                "group": row.group,
                "label": row.label,
                "description": row.description,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]


def _default_map() -> dict[str, Any]:
    from rap.seed import load_yaml
    from rap.paths import CONFIG_DIR

    data = load_yaml(CONFIG_DIR / "settings_defaults.yaml")
    return {item["key"]: item["value"] for item in data.get("settings", [])}


def set_setting(key: str, value: Any) -> AppSetting:
    with session_scope() as session:
        row = session.get(AppSetting, key)
        if row is None:
            raise KeyError(f"Unknown setting: {key}")
        row.value = _coerce(value, row.value_type)
        session.flush()
        _cache[key] = row.value
        return row


def set_settings(updates: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    with session_scope() as session:
        for key, value in updates.items():
            row = session.get(AppSetting, key)
            if row is None:
                raise KeyError(f"Unknown setting: {key}")
            row.value = _coerce(value, row.value_type)
            _cache[key] = row.value
            changed.append(key)
    invalidate_cache()
    bootstrap()
    return changed


def _coerce(value: Any, value_type: SettingValueType) -> Any:
    if value_type == SettingValueType.number:
        return float(value) if value is not None else None
    if value_type == SettingValueType.bool:
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if value_type == SettingValueType.string:
        return None if value is None else str(value)
    return value


def get_credential(slug: str) -> ApiCredential | None:
    with session_scope() as session:
        return session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))


def decrypt_provider_key(slug: str) -> str | None:
    with session_scope() as session:
        row = session.scalar(select(ApiCredential).where(ApiCredential.provider_slug == slug))
        if row is None or row.api_key_encrypted is None:
            return None
        return decrypt_key(row.api_key_encrypted)


def stored_key_fragments() -> list[str]:
    fragments: list[str] = []
    with session_scope() as session:
        for row in session.scalars(select(ApiCredential)).all():
            if row.api_key_encrypted is None:
                continue
            try:
                fragments.append(decrypt_key(row.api_key_encrypted))
            except RuntimeError:
                continue
    return fragments


def role_config(role: str) -> dict[str, str]:
    roles = get_setting("models.roles") or {}
    if role not in roles:
        raise KeyError(f"Unknown model role: {role}")
    return roles[role]


def model_price(model_id: str) -> dict[str, float]:
    pricing = get_setting("models.pricing") or {}
    return pricing.get(model_id) or {"input": 0.0, "output": 0.0, "cached_input": 0.0}
