"""
Simple in-memory rate limiter for expensive endpoints.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._events.get(key)
            if bucket is None:
                bucket = deque()
                self._events[key] = bucket

            while bucket and bucket[0] < window_start:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(bucket[0] + window_seconds - now))
                return False, retry_after

            bucket.append(now)
            return True, 0


limiter = InMemoryRateLimiter()


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    user_key: str | None = None,
) -> None:
    actor = user_key or f"ip:{_client_ip(request)}"
    key = f"{scope}:{actor}"
    allowed, retry_after = limiter.allow(key, limit=limit, window_seconds=window_seconds)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please retry shortly.",
            headers={"Retry-After": str(retry_after)},
        )
