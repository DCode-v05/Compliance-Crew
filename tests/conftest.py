"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point src.db at a per-test SQLite file and initialise it."""
    db_path = tmp_path / "test_compliance.db"
    from src import db

    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db(db_path)
    return db_path
