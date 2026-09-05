from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

from rap.llm.context import job_log
from rap.settings import get_setting

logger = logging.getLogger(__name__)
T = TypeVar("T")

_semaphores: dict[str, asyncio.Semaphore] = {}
_sem_lock = asyncio.Lock()


def llm_concurrency() -> int:
    for key in (
        "extraction.llm_concurrency",
        "extraction.concurrency",
        "extraction.concurrency_deepseek",
    ):
        value = get_setting(key)
        if value is not None:
            return max(1, int(value))
    return 8


def is_rate_limit_error(exc: BaseException) -> bool:
    code = getattr(exc, "status_code", None)
    if code is None:
        response = getattr(exc, "response", None)
        code = getattr(response, "status_code", None)
    if code == 429:
        return True
    text = str(exc).lower()
    return any(
        needle in text
        for needle in (
            "429",
            "rate limit",
            "rate_limit",
            "too many requests",
            "rpm limit",
            "tokens per min",
        )
    )


async def _semaphore_for(provider: str) -> asyncio.Semaphore:
    async with _sem_lock:
        if provider not in _semaphores:
            _semaphores[provider] = asyncio.Semaphore(llm_concurrency())
        return _semaphores[provider]


def reset_semaphores() -> None:
    _semaphores.clear()


def _log_backoff(provider: str, wait: float, attempt: int) -> None:
    line = f"Rate limited on {provider}; backing off {wait:.0f}s (retry {attempt}/5)"
    sink = job_log.get()
    if sink:
        sink(line)
    else:
        logger.warning(line)


async def run_on_provider(provider: str, fn: Callable[[], T]) -> T:
    """Run a sync provider call under the per-provider semaphore with 429 backoff."""
    sem = await _semaphore_for(provider)
    async with sem:
        delay = 1.0
        for attempt in range(6):
            try:
                return await asyncio.to_thread(fn)
            except Exception as exc:
                if attempt >= 5 or not is_rate_limit_error(exc):
                    raise
                wait = min(delay, 30.0)
                _log_backoff(provider, wait, attempt + 1)
                await asyncio.sleep(wait)
                delay *= 2
        raise RuntimeError("rate-limit retries exhausted")
