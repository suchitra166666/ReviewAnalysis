from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar

current_job_id: ContextVar[int | None] = ContextVar("current_job_id", default=None)
job_log: ContextVar[Callable[[str], None] | None] = ContextVar("job_log", default=None)
