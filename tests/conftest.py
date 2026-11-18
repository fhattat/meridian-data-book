"""Shared test settings. Run from the repository root: python -m pytest -q tests"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
DB = ROOT / "data" / "meridian.duckdb"


@pytest.fixture(scope="session")
def con():
    """Read-only connection to the database built by run_pipeline.py; tests are skipped without it."""
    if not DB.exists():
        pytest.skip("data/meridian.duckdb not found: run `python run_pipeline.py --env local` first")
    duckdb = pytest.importorskip("duckdb")
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()
