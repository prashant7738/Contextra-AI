"""Lightweight in-memory rate limiting for sensitive endpoints (login/register).

Fixed-window limiter, sufficient for a single-process deployment. If the app is
scaled to multiple instances, replace it with a shared store (e.g. Redis).

Two keys are limited independently:
- the client IP, which slows registration spam and broad credential stuffing;
- the target email (login only), which cannot be spoofed with headers and stops
  brute-forcing one account from many IPs.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, Request, status

# Hard cap on tracked keys so spoofed/rotating keys can't grow memory forever.
MAX_TRACKED_KEYS = 10_000


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, max_keys: int = MAX_TRACKED_KEYS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] < cutoff]
        for key in stale:
            del self._hits[key]

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self.max_keys:
                    self._prune(now)
                    if len(self._hits) >= self.max_keys:
                        # Still full of active keys: drop the oldest entry.
                        self._hits.pop(next(iter(self._hits)))
                hits = self._hits[key] = deque()
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Headers set by an edge proxy (Cloudflare fronts Render services); a client
# cannot override them when the request passes through that edge.
_EDGE_IP_HEADERS = ("cf-connecting-ip", "true-client-ip")


def client_ip(request: Request) -> str:
    for header in _EDGE_IP_HEADERS:
        value = request.headers.get(header)
        if value and value.strip():
            return value.strip()
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


# Generous but meaningful limits: slow down credential stuffing / registration
# spam without impacting normal usage.
_login_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60)
_login_email_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=300)
_register_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)


def rate_limit_login(request: Request) -> None:
    _login_limiter.check(client_ip(request))


def rate_limit_login_email(email: str) -> None:
    _login_email_limiter.check(normalize_email(email))


def rate_limit_register(request: Request) -> None:
    _register_limiter.check(client_ip(request))


def reset_all_limiters() -> None:
    """Test helper."""
    for limiter in (_login_limiter, _login_email_limiter, _register_limiter):
        limiter.reset()
