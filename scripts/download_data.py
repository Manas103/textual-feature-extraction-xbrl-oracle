"""Download and cache the 4 real SEC DERA quarterly bulk files this project
uses. Idempotent: run it as many times as you like.

    python scripts/download_data.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from featurex import download  # noqa: E402

if __name__ == "__main__":
    for path in download.ensure_all_downloaded():
        print(f"ready: {path}")
