"""The refusal rule: an LLM-extracted value is only ever reported if the
filing's own real jp-gaap XBRL fact confirms it; otherwise this project
refuses rather than guesses.

`reconcile_filing` runs both independent readings (the LLM extraction and
the Japanese text-rule match) against one filing's one field, and the
refusal decision against the oracle, in one pass, the same "resolve both
paths through shared logic so a disagreement traces to one real cause"
discipline `featurex/reconcile.py` already follows for the US filings.
"""

from __future__ import annotations

from dataclasses import dataclass

from featurex_ja import config, text_extract_ja


def _relative_close(a: float, b: float, tol: float = config.AGREEMENT_RELATIVE_TOLERANCE) -> bool:
    if a == 0.0 and b == 0.0:
        return True
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tol


@dataclass
class FieldResult:
    doc_id: str
    field: str
    true_value: float
    llm_value: float | None
    text_rule_value: float | None
    oracle_value: float | None
    raw_agrees_with_text_rule: bool | None  # None when the LLM produced nothing to compare
    refused: bool
    accepted_value: float | None
    correct_given_accepted: bool | None  # precision: only meaningful when not refused


def reconcile_field(filing, field: str, llm_client) -> FieldResult:
    true_value = filing.true_values[field]
    label = filing.label_text[field]

    llm_value = llm_client.extract(filing, field)
    text_rule_value = text_extract_ja.true_value_for_label(filing, label)
    oracle_value = filing.oracle_values[field]

    raw_agrees = None
    if llm_value is not None and text_rule_value is not None:
        raw_agrees = _relative_close(llm_value, text_rule_value)

    refused = oracle_value is None or llm_value is None or not _relative_close(llm_value, oracle_value)
    accepted_value = llm_value if not refused else None
    correct = _relative_close(accepted_value, true_value) if accepted_value is not None else None

    return FieldResult(
        doc_id=filing.doc_id, field=field, true_value=true_value, llm_value=llm_value,
        text_rule_value=text_rule_value, oracle_value=oracle_value,
        raw_agrees_with_text_rule=raw_agrees, refused=refused,
        accepted_value=accepted_value, correct_given_accepted=correct,
    )


def reconcile_all(filings, llm_client) -> list[FieldResult]:
    results = []
    for filing in filings:
        for field in config.JA_FIELDS:
            results.append(reconcile_field(filing, field, llm_client))
    return results
