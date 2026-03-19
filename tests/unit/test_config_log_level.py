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
