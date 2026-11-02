"""HTTP authentication and start throttling for explicit public-demo mode."""

from __future__ import annotations

import ipaddress
import os
import secrets
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import Request
from starlette.responses import JSONResponse

from agent.demo_config import PublicDemoConfig, _positive_int


class DemoStartRateLimiter:
    def __init__(self):
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_id: str, *, limit: int, window_seconds: int) -> bool:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            attempts = self._attempts[client_id]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= limit:
                return False
            attempts.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


demo_start_rate_limiter = DemoStartRateLimiter()


def _trusted_proxy_ips() -> set[str]:
    trusted = set()
    for value in os.getenv("PUBLIC_DEMO_TRUSTED_PROXY_IPS", "").split(","):
        value = value.strip()
        if value:
            trusted.add(str(ipaddress.ip_address(value)))
    return trusted


def _client_id(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer = str(ipaddress.ip_address(peer))
    except ValueError:
        return "unknown"
    if peer not in _trusted_proxy_ips():
        return peer

    # Cloudflare supplies one canonical address. X-Forwarded-For is deliberately
    # ignored because an untrusted client can append or forge its entries.
    forwarded = request.headers.get("cf-connecting-ip", "").strip()
    try:
        return str(ipaddress.ip_address(forwarded))
    except ValueError:
        return peer


def _protected_request(request: Request) -> bool:
    if request.method == "OPTIONS":
        return False
    path = request.url.path.rstrip("/") or "/"
    if path in {"/start", "/api/offer"}:
        return request.method in {"POST", "PATCH"}
    return path.startswith("/sessions/") and path.endswith("/api/offer")


def install_demo_security(app) -> None:
    """Install security before Pipecat registers its runner routes."""

    @app.middleware("http")
    async def public_demo_security(request: Request, call_next):
        config = PublicDemoConfig.from_environment()
        if not config.enabled or not _protected_request(request):
            return await call_next(request)

        expected = os.getenv("PUBLIC_DEMO_ACCESS_TOKEN", "")
        if len(expected) < 32:
            return JSONResponse(
                status_code=503,
                content={"detail": "Public demo authentication is not configured"},
            )

        authorization = request.headers.get("authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        authenticated = (
            bool(separator)
            and scheme.lower() == "bearer"
            and secrets.compare_digest(supplied, expected)
        )
        if not authenticated:
            return JSONResponse(
                status_code=401,
                content={"detail": "Demo access denied"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if request.method == "POST" and request.url.path.rstrip("/") == "/start":
            limit = _positive_int("PUBLIC_DEMO_START_RATE_LIMIT", 5)
            window = _positive_int("PUBLIC_DEMO_START_RATE_WINDOW_SECONDS", 60)
            if not demo_start_rate_limiter.allow(
                _client_id(request), limit=limit, window_seconds=window
            ):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Demo start rate limit exceeded"},
                    headers={"Retry-After": str(window)},
                )

        return await call_next(request)
