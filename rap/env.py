"""The only module allowed to read os.environ.

Allowed keys: DATABASE_URL, SETTINGS_ENCRYPTION_KEY.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ALLOWED = frozenset({"DATABASE_URL", "SETTINGS_ENCRYPTION_KEY"})

_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    _loaded = True


def get_env(key: str) -> str:
    if key not in _ALLOWED:
        raise RuntimeError(
            f"Refusing to read {key!r} from the environment. "
            "Only DATABASE_URL and SETTINGS_ENCRYPTION_KEY are allowed; "
            "everything else lives in Settings."
        )
    _ensure_loaded()
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(
            f"{key} is missing. Run `make init` and check .env. "
            "The file must contain DATABASE_URL and SETTINGS_ENCRYPTION_KEY only."
        )
    return value


def database_url() -> str:
    return get_env("DATABASE_URL")


def settings_encryption_key() -> str:
    return get_env("SETTINGS_ENCRYPTION_KEY")
