from __future__ import annotations

import logging
import re
from typing import Iterable


class RedactingFormatter(logging.Formatter):
    """Redact any stored API key fragments from log output."""

    def __init__(self, *args, secrets: Iterable[str] | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._secrets = [s for s in (secrets or []) if s and len(s) >= 4]

    def set_secrets(self, secrets: Iterable[str]) -> None:
        self._secrets = [s for s in secrets if s and len(s) >= 4]

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        for secret in self._secrets:
            message = message.replace(secret, "••••")
            if len(secret) > 8:
                message = message.replace(secret[-8:], "••••")
        message = re.sub(r"(sk-[A-Za-z0-9_\-]{8,})", "••••", message)
        message = re.sub(r"(sk-proj-[A-Za-z0-9_\-]{8,})", "••••", message)
        return message


def configure_logging(secrets: Iterable[str] | None = None) -> RedactingFormatter:
    formatter = RedactingFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        secrets=secrets,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return formatter
