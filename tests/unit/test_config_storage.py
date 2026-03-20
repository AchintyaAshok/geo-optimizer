from __future__ import annotations

import pytest
from pydantic import ValidationError

from crawllmer.core.config import Settings


class TestStorageBackendDefault:
    def test_default_is_sqlite(self) -> None:
        s = Settings()
        assert s.storage_backend == "sqlite"
        assert s.db_url == "sqlite:///./crawllmer.db"

    def test_sqlite_engine_kwargs(self) -> None:
        s = Settings()
        assert s.engine_kwargs == {"connect_args": {"check_same_thread": False}}

    def test_rejects_invalid_backend(self) -> None:
        with pytest.raises(ValidationError):
            Settings(storage_backend="mysql")


class TestPgsqlBackend:
    def test_pgsql_requires_credentials(self) -> None:
        with pytest.raises(ValidationError, match="CRAWLLMER_PG_HOST"):
            Settings(storage_backend="pgsql")

    def test_pgsql_missing_partial_credentials(self) -> None:
        with pytest.raises(ValidationError, match="requires either"):
            Settings(
                storage_backend="pgsql",
                pg_host="localhost",
                pg_user="user",
                pg_database="db",
            )

    def test_pgsql_accepts_db_url_directly(self) -> None:
        s = Settings(
            storage_backend="pgsql",
            db_url="postgresql://u:p@host:5432/db",
        )
        assert s.db_url == "postgresql://u:p@host:5432/db"

    def test_pgsql_parts_override_db_url(self) -> None:
        s = Settings(
            storage_backend="pgsql",
            db_url="postgresql://old:old@old:5432/old",
            pg_host="new",
            pg_user="u",
            pg_password="p",
            pg_database="d",
        )
        assert "new" in s.db_url
        assert "old" not in s.db_url

    def test_pgsql_assembles_db_url(self) -> None:
        s = Settings(
            storage_backend="pgsql",
            pg_host="db.example.com",
            pg_port=5432,
            pg_user="myuser",
            pg_password="secret",
            pg_database="mydb",
        )
        assert s.db_url == "postgresql://myuser:secret@db.example.com:5432/mydb"

    def test_pgsql_custom_port(self) -> None:
        s = Settings(
            storage_backend="pgsql",
            pg_host="localhost",
            pg_port=5433,
            pg_user="u",
            pg_password="p",
            pg_database="d",
        )
        assert ":5433/" in s.db_url

    def test_pgsql_engine_kwargs(self) -> None:
        s = Settings(
            storage_backend="pgsql",
            pg_host="localhost",
            pg_user="u",
            pg_password="p",
            pg_database="d",
        )
        assert s.engine_kwargs == {"pool_pre_ping": True, "pool_size": 5}
