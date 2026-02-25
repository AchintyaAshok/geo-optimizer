from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    db_file = ROOT / "crawllmer.db"
    if db_file.exists():
        db_file.unlink()
