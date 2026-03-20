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

    # ── Database URL ────────────────────────────────────────────────────
    # Set explicitly for sqlite:// or postgresql:// connection strings.
    # When storage_backend=sqlite and unset, defaults to sqlite:///./crawllmer.db
    # When storage_backend=pgsql, built from PG_* fields or set directly.
    db_url: str | None = None

    # ── PostgreSQL (required when storage_backend == "pgsql") ──────────
    pg_host: str | None = None
    pg_port: int | None = 5432
    pg_user: str | None = None
    pg_password: str | None = None
    pg_database: str | None = None

    # ── Celery ─────────────────────────────────────────────────────────
    celery_broker_url: str = "sqla+sqlite:///./celery-broker.db"
    celery_result_backend: str = "db+sqlite:///./celery-results.db"
    celery_task_acks_late: bool = True
    celery_task_reject_on_worker_lost: bool = True
    celery_broker_visibility_timeout: int = 3600

    # ── Logging ────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG"

    # ── Worker ─────────────────────────────────────────────────────────
    worker_poll_seconds: int = 2
    celery_worker_concurrency: int = 4

    # ── UI ──────────────────────────────────────────────────────────────
    api_base_url: str = "http://localhost:8000"

    ui_refresh_seconds: int = 2

    # ── Spider (fallback crawler) ──────────────────────────────────────
    spider_max_depth: int = 3
    spider_max_scan_pages: int = 100
    spider_max_index_pages: int = 50
    spider_include_extensions: str = ".html,.htm,.txt,.md,"
    spider_timeout_per_page: int = 5

    @model_validator(mode="after")
    def _validate_storage_config(self) -> Settings:
        """Build or validate db_url based on storage_backend.

        sqlite: defaults to sqlite:///./crawllmer.db if db_url not set.
        pgsql:  prefers PG_* fields → builds URL from parts.
                falls back to db_url if it starts with postgresql://.
                raises if neither is available.
        """
        if self.storage_backend == "sqlite":
            if self.db_url is None:
                self.db_url = "sqlite:///./crawllmer.db"
        elif self.storage_backend == "pgsql":
            pg_fields = ("pg_host", "pg_user", "pg_password", "pg_database")
            has_parts = all(getattr(self, f) is not None for f in pg_fields)

            if has_parts:
                port = self.pg_port or 5432
                self.db_url = (
                    f"postgresql://{self.pg_user}:{self.pg_password}"
                    f"@{self.pg_host}:{port}/{self.pg_database}"
                )
            elif self.db_url and self.db_url.startswith("postgresql://"):
                pass
            else:
                raise ValueError(
                    "storage_backend='pgsql' requires either "
                    "CRAWLLMER_PG_HOST/USER/PASSWORD/DATABASE or "
                    "CRAWLLMER_DB_URL=postgresql://..."
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
