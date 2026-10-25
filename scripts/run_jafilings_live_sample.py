"""Genuinely exercises the real `claude` CLI (ClaudeCLIJaExtractor) on a
small live sample, the same scale of live-call sample
`grounded-reconciliation-assistant` (20 calls) and
`campaign-report-verification-gate` (16 calls) already establish as this
portfolio's precedent for "real, not simulated, but not full-fixture-
scale." Prints how often the real model's field identification agreed
with the deterministic stand-in and with the fixture's own ground truth.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from featurex_ja import config, fixture
from featurex_ja.llm_extract import ClaudeCLIJaExtractor, DeterministicJaExtractor

N_LIVE_CALLS = 20


def main() -> None:
    filings = fixture.build_fixture(n_issuers=20, n_filings=20)
    claude = ClaudeCLIJaExtractor()
    deterministic = DeterministicJaExtractor()

    rows = []
    for i in range(N_LIVE_CALLS):
        filing = filings[i % len(filings)]
        field = config.JA_FIELDS[i % len(config.JA_FIELDS)]
        true_value = filing.true_values[field]

        identified = claude.extract_field_name(filing.label_text[field], true_value)
        deterministic_value = deterministic.extract(filing, field)

        rows.append({
            "doc_id": filing.doc_id,
            "intended_field": field,
            "label_text": filing.label_text[field],
            "claude_identified_field": identified,
            "claude_correct": identified == field,
            "deterministic_matches_true_value": deterministic_value == true_value,
        })

    n_correct = sum(1 for r in rows if r["claude_correct"])
    summary = {
        "n_live_calls": len(rows),
        "n_correct_field_identification": n_correct,
        "accuracy_pct": round(100.0 * n_correct / len(rows), 1) if rows else None,
        "rows": rows,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
