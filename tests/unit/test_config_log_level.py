from __future__ import annotations

import pytest
from pydantic import ValidationError

from crawllmer.core.config import Settings


def test_default_log_level_is_debug() -> None:
    s = Settings()
    assert s.log_level == "DEBUG"


def test_log_level_accepts_valid_values() -> None:
    for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        s = Settings(log_level=level)
        assert s.log_level == level


def test_log_level_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="VERBOSE")


def test_spider_defaults() -> None:
    s = Settings()
    assert s.spider_max_depth == 3
    assert s.spider_max_scan_pages == 100
    assert s.spider_max_index_pages == 50
    assert s.spider_timeout_per_page == 5


def test_spider_extensions_set_parses_csv() -> None:
    s = Settings()
    exts = s.spider_extensions_set
    assert ".html" in exts
    assert ".htm" in exts
    assert ".txt" in exts
    assert ".md" in exts
    assert "" in exts  # trailing comma = extensionless paths


def test_spider_extensions_set_custom() -> None:
    s = Settings(spider_include_extensions=".html,.pdf")
    exts = s.spider_extensions_set
    assert exts == {".html", ".pdf"}
    assert "" not in exts  # no trailing comma
