import time

from app.scheduler import RateLimiter


def test_rate_limiter_blocks_after_rpm():
    limiter = RateLimiter(rpm=2, window_seconds=1)
    start = time.time()
    limiter.acquire("p1")
    limiter.acquire("p1")
    limiter.acquire("p1")
    assert time.time() - start >= 0.9


def test_rate_limiter_uses_weighted_cost():
    limiter = RateLimiter(rpm=3, window_seconds=1)
    start = time.time()
    limiter.acquire("p1", cost=2)
    limiter.acquire("p1", cost=1)
    limiter.acquire("p1", cost=1)
    assert time.time() - start >= 0.9
