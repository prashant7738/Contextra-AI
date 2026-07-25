"""Lightweight in-memory rate limiting for sensitive endpoints (login/register).

This is a simple fixed-window limiter keyed by client IP. It is sufficient for
a single-process deployment; if the app is scaled to multiple instances, this
should be replaced with a shared store (e.g. Redis) so limits are enforced
across all processes.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.pop(0)
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Generous but meaningful limits: slow down credential stuffing / registration
# spam without impacting normal usage.
_login_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
_register_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)


def rate_limit_login(request: Request) -> None:
    _login_limiter.check(_client_key(request))


def rate_limit_register(request: Request) -> None:
    _register_limiter.check(_client_key(request))
