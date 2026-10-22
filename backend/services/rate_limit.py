"""Keep upload-time vision calls under the free per-minute limit of each key."""
from __future__ import annotations

import hashlib
import threading
import time

from config import settings


class RateLimiter:
    def __init__(self, per_minute: int):
        self.interval = 60.0 / max(1, per_minute)
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, key: str) -> float:
        """Block until this key may make another call. Returns the seconds waited.

        Keys are tracked by a short hash, so raw keys are never kept around.
        """
        bucket = hashlib.sha256(key.encode()).hexdigest()[:16]
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next.get(bucket, 0.0))
            self._next[bucket] = slot + self.interval
        delay = slot - now
        if delay > 0:
            time.sleep(delay)
        return max(0.0, delay)


vision_limiter = RateLimiter(per_minute=settings.vision_rpm)
