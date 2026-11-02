"""Explicit, environment-backed safeguards for the browser public demo."""

from __future__ import annotations

import os
from dataclasses import dataclass


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE_VALUES


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class PublicDemoConfig:
    enabled: bool
    max_concurrent_sessions: int
    max_session_seconds: int

    @classmethod
    def from_environment(cls) -> "PublicDemoConfig":
        enabled = _enabled("PUBLIC_DEMO_MODE")
        return cls(
            enabled=enabled,
            max_concurrent_sessions=(
                _positive_int("PUBLIC_DEMO_MAX_CONCURRENT_SESSIONS", 2)
                if enabled else 0
            ),
            max_session_seconds=(
                _positive_int("PUBLIC_DEMO_MAX_SESSION_SECONDS", 600)
                if enabled else 0
            ),
        )
