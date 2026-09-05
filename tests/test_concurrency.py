from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

from rap.llm.concurrency import is_rate_limit_error, reset_semaphores, run_on_provider


class FakeRateLimit(Exception):
    def __init__(self, status_code: int = 429) -> None:
        super().__init__("Error code: 429 - rate limit exceeded")
        self.status_code = status_code


def test_rate_limit_detection() -> None:
    assert is_rate_limit_error(FakeRateLimit())
    assert is_rate_limit_error(RuntimeError("HTTP 429 Too Many Requests"))
    assert not is_rate_limit_error(RuntimeError("unsupported value: temperature"))


def test_backoff_retries_then_succeeds() -> None:
    reset_semaphores()
    hits = {"n": 0}

    def flaky() -> str:
        hits["n"] += 1
        if hits["n"] < 3:
            raise FakeRateLimit()
        return "ok"

    async def go() -> None:
        with patch("rap.llm.concurrency.asyncio.sleep", new_callable=AsyncMock):
            result = await run_on_provider("openai", flaky)
            assert result == "ok"

    asyncio.run(go())
    assert hits["n"] == 3


def test_semaphore_caps_in_flight() -> None:
    reset_semaphores()
    in_flight = 0
    peak = 0

    def work() -> None:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        time.sleep(0.05)
        in_flight -= 1

    async def go() -> None:
        await asyncio.gather(*(run_on_provider("deepseek", work) for _ in range(20)))

    asyncio.run(go())
    assert peak <= 8
