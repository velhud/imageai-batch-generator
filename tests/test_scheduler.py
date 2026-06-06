import time

from app.scheduler import RateLimiter


def test_rate_limiter_blocks_after_rpm():
    limiter = RateLimiter(rpm=2)
    start = time.time()
    limiter.acquire("p1")
    limiter.acquire("p1")
    limiter.acquire("p1")
    assert time.time() - start >= 0.9
