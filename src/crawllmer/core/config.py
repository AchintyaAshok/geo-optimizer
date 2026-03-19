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

    # ── UI ─────────────────────────────────────────────────────────────
    ui_refresh_seconds: int = 2

    # ── Spider (fallback crawler) ────────────────────────────────────
    spider_max_depth: int = 3
    spider_max_scan_pages: int = 100
    spider_max_index_pages: int = 50
    spider_include_extensions: str = ".html,.htm,.txt,.md,"
    spider_timeout_per_page: int = 5

    @property
    def spider_extensions_set(self) -> set[str]:
        """Parse include_extensions CSV into a set.

        Trailing comma means extensionless paths (empty string) are included.
        """
        return {ext.strip() for ext in self.spider_include_extensions.split(",")}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()
