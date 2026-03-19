"""Centralised configuration for crawllmer.

All environment variables are read once via pydantic-settings.  Import the
singleton ``settings`` object wherever configuration values are needed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="CRAWLLMER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────
    db_url: str = "sqlite:///./crawllmer.db"

    # ── Celery ────────────────────────────────────────────────────────
    celery_broker_url: str = "sqla+sqlite:///./celery-broker.db"
    celery_result_backend: str = "db+sqlite:///./celery-results.db"

    # ── Logging ───────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    # ── Worker ────────────────────────────────────────────────────────
    worker_poll_seconds: int = 2


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
