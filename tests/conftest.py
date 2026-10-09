from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from featurex import load  # noqa: E402

DB_PATH = load.DB_PATH


@pytest.fixture(scope="session")
def real_con():
    """The real, already-built DuckDB database. Skips (not fails) if the
    multi-hundred-MB SEC bulk files have not been downloaded and built on
    this machine; see scripts/build.py to build it."""
    if not DB_PATH.exists():
        pytest.skip("data/featurex.duckdb not built; run scripts/build.py first")
    import duckdb

    return duckdb.connect(str(DB_PATH), read_only=True)
