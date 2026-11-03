"""Keep evaluation requests inside the free Gemini-API limits.

Every request waits for its turn under a per-minute pace. Busy periods (503) and short
per-minute limits (429 with a short retry delay) are waited out; a long retry delay means
the daily quota is used up, and the run stops so it can continue another day.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from loguru import logger

from services.llm import ProviderError
from services.rate_limit import RateLimiter

T = TypeVar("T")

BUSY_WAITS = (15, 45, 90)
SHORT_LIMIT_SECONDS = 90
MAX_SHORT_WAITS = 6


class QuotaExhausted(RuntimeError):
    """The daily free quota of a model is used up."""


def patient_call(fn: Callable[[], T], *, label: str, limiter: RateLimiter, key: str) -> T:
    """Run fn() at the limiter's pace, waiting out busy periods and per-minute limits.

    Raises QuotaExhausted when the provider asks to wait longer than SHORT_LIMIT_SECONDS
    (or keeps refusing), and re-raises every other ProviderError.
    """
    busy = list(BUSY_WAITS)
    short_waits = 0
    while True:
        limiter.wait(key)
        try:
            return fn()
        except ProviderError as err:
            retry_after = err.retry_after or 0
            if err.kind == "unavailable" and busy:
                wait = busy.pop(0)
            elif err.kind == "rate_limited" and retry_after <= SHORT_LIMIT_SECONDS and short_waits < MAX_SHORT_WAITS:
                short_waits += 1
                wait = (err.retry_after or 30) + 1
            elif err.kind == "rate_limited":
                raise QuotaExhausted(f"{label}: the free daily quota is used up") from None
            else:
                raise
            logger.warning(f"{label}: {err.kind}, waiting {wait:.0f}s")
            time.sleep(wait)
