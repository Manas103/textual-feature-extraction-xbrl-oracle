"""Download and cache the SEC DERA Financial Statement Data Sets.

Each quarterly file is a real, public zip of four pipe-delimited text files
(sub.txt, num.txt, pre.txt, tag.txt) covering every XBRL-tagged filing
submitted that quarter: https://www.sec.gov/dera/data/financial-statement-data-sets.html
Nothing here is synthetic. A descriptive User-Agent with a real contact
address is required by SEC's fair-access policy; see
https://www.sec.gov/os/webmaster-faq#developers
"""

from __future__ import annotations

import pathlib
import urllib.request
import zipfile

from featurex import config

RAW_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"


def quarter_dir(quarter: str) -> pathlib.Path:
    return RAW_DIR / quarter


def is_extracted(quarter: str) -> bool:
    d = quarter_dir(quarter)
    return all((d / name).exists() for name in ("sub.txt", "num.txt", "pre.txt"))


def download_and_extract(quarter: str, force: bool = False) -> pathlib.Path:
    """Idempotent: skips the network entirely if already extracted."""
    d = quarter_dir(quarter)
    if is_extracted(quarter) and not force:
        return d
    d.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / f"{quarter}.zip"
    if not zip_path.exists() or force:
        url = config.FSDS_URL_TEMPLATE.format(quarter=quarter)
        req = urllib.request.Request(url, headers={"User-Agent": config.SEC_USER_AGENT})
        with urllib.request.urlopen(req, timeout=180) as resp, open(zip_path, "wb") as out:
            out.write(resp.read())
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(d)
    zip_path.unlink()
    return d


def ensure_all_downloaded(quarters: list[str] | None = None) -> list[pathlib.Path]:
    quarters = quarters or config.QUARTERS
    return [download_and_extract(q) for q in quarters]
