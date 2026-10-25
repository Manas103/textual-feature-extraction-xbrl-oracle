"""Full-fixture-scale run using the deterministic extractor (see
featurex_ja/config.py for why real EDINET data was not reachable). Prints
every measurement; `scripts/run_jafilings_live_sample.py` separately
exercises the real `claude` CLI on a small sample."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from featurex_ja import audit, fixture, measurements
from featurex_ja.llm_extract import DeterministicJaExtractor


def main() -> None:
    filings = fixture.build_fixture()
    llm = DeterministicJaExtractor()
    results = audit.reconcile_all(filings, llm)
    report = measurements.run_all_measurements(filings, results)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
