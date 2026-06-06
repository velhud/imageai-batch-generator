from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Dict


class RateLimiter:
    """Token bucket style limiter for requests per minute per provider."""

    def __init__(self, rpm: int = 60) -> None:
        self.rpm = max(1, rpm)
        self.events: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def set_rpm(self, rpm: int) -> None:
        self.rpm = max(1, rpm)

    def acquire(self, key: str) -> None:
        """Block until allowed to proceed for a given key (provider/model)."""
        while True:
            with self.lock:
                now = time.time()
                window = self.events[key]
                # drop old events
                while window and now - window[0] > 60:
                    window.popleft()
                if len(window) < self.rpm:
                    window.append(now)
                    return
                sleep_for = 60 - (now - window[0]) + 0.01
            time.sleep(sleep_for)
