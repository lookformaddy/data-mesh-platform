"""Configuration from environment variables. All optional; the demo
and tests run with defaults and no .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    default_grant_days: int = 30


def load_settings() -> Settings:
    return Settings(
        host=os.environ.get("DM_HOST", "127.0.0.1"),
        port=int(os.environ.get("DM_PORT", "8000")),
        default_grant_days=int(os.environ.get("DM_GRANT_DAYS", "30")),
    )
