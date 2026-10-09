"""Build data/featurex.duckdb from the real SEC bulk files, downloading them
first if needed.

    python scripts/build.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from featurex import load  # noqa: E402

if __name__ == "__main__":
    con = load.build_database(force=True)
    n_sub = con.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    n_num = con.execute("SELECT COUNT(*) FROM num").fetchone()[0]
    n_pre = con.execute("SELECT COUNT(*) FROM pre").fetchone()[0]
    print(f"submissions: {n_sub}")
    print(f"num: {n_num}")
    print(f"pre: {n_pre}")
