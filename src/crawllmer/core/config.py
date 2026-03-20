"""Centralised configuration for crawllmer.

All environment variables are read once via pydantic-settings.  Import the
singleton ``settings`` object wherever configuration values are needed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="CRAWLLMER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Storage backend ────────────────────────────────────────────────
    storage_backend: Literal["sqlite", "pgsql"] = "sqlite"

    # ── SQLite (default) ───────────────────────────────────────────────
    db_url: str = "sqlite:///./crawllmer.db"

    # ── PostgreSQL (required when storage_backend == "pgsql") ──────────
    pg_host: str | None = None
    pg_port: int = 5432
    pg_user: str | None = None
    pg_password: str | None = None
    pg_database: str | None = None

    # ── Celery ─────────────────────────────────────────────────────────
    celery_broker_url: str = "sqla+sqlite:///./celery-broker.db"
    celery_result_backend: str = "db+sqlite:///./celery-results.db"

    # ── Logging ────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    # ── Worker ─────────────────────────────────────────────────────────
    worker_poll_seconds: int = 2
    celery_worker_concurrency: int = 4

    # ── UI ─────────────────────────────────────────────────────────────
    ui_refresh_seconds: int = 2

    # ── Spider (fallback crawler) ──────────────────────────────────────
    spider_max_depth: int = 3
    spider_max_scan_pages: int = 100
    spider_max_index_pages: int = 50
    spider_include_extensions: str = ".html,.htm,.txt,.md,"
    spider_timeout_per_page: int = 5

    @model_validator(mode="after")
    def _validate_storage_config(self) -> Settings:
        """Ensure Postgres credentials are provided when pgsql is selected."""
        if self.storage_backend == "pgsql":
            required = ("pg_host", "pg_user", "pg_password", "pg_database")
            missing = [f for f in required if getattr(self, f) is None]
            if missing:
                env_names = [f"CRAWLLMER_{f.upper()}" for f in missing]
                raise ValueError(
                    f"storage_backend='pgsql' requires: {', '.join(env_names)}"
                )
            self.db_url = (
                f"postgresql://{self.pg_user}:{self.pg_password}"
                f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
            )
        return self

    @property
    def engine_kwargs(self) -> dict:
        """Return backend-appropriate SQLAlchemy engine arguments."""
        if self.storage_backend == "pgsql":
            return {"pool_pre_ping": True, "pool_size": 5}
        return {"connect_args": {"check_same_thread": False}}

    @property
    def celery_worker_pool(self) -> str:
        """Derive Celery pool type from broker: prefork for Redis, solo for SQLite."""
        if self.celery_broker_url.startswith("redis"):
            return "prefork"
        return "solo"

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
