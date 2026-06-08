from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Dict


class RateLimiter:
    """Token bucket style limiter for requests per minute per provider."""

    def __init__(self, rpm: int = 60, window_seconds: float = 60.0) -> None:
        self.rpm = max(1, rpm)
        self.window_seconds = max(0.1, window_seconds)
        self.events: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def set_rpm(self, rpm: int) -> None:
        self.rpm = max(1, rpm)

    def acquire(self, key: str, cost: int = 1) -> None:
        """Block until allowed to spend quota units for a given key."""
        cost = max(1, cost)
        while True:
            with self.lock:
                now = time.time()
                window = self.events[key]
                # drop old events
                while window and now - window[0] > self.window_seconds:
                    window.popleft()
                if len(window) + cost <= self.rpm:
                    for _ in range(cost):
                        window.append(now)
                    return
                sleep_for = self.window_seconds - (now - window[0]) + 0.01
            time.sleep(sleep_for)
