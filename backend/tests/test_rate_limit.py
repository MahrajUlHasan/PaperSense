from services.rate_limit import RateLimiter


def test_second_call_waits(monkeypatch):
    """At 6 calls/minute the second call of a key waits ~10 s; other keys are independent."""
    waited = []
    monkeypatch.setattr("services.rate_limit.time.sleep", lambda s: waited.append(s))
    limiter = RateLimiter(per_minute=6)
    limiter.wait("key-a")
    limiter.wait("key-a")
    limiter.wait("key-b")
    assert len(waited) == 1 and 9.0 < waited[0] <= 10.0
