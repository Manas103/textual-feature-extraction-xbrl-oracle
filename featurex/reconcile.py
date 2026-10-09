"""Reconcile the text path against the oracle path, field by field, and
classify every disagreement by cause.

Scope: a (filing, field) pair only enters the measured denominator when the
oracle has a value (config.ORACLE_TAGS found a standard tag for it). Within
that scope, "agree" means the text path found a value within
config.AGREEMENT_RELATIVE_TOLERANCE of the oracle's; everything else is a
disagreement, and every disagreement gets exactly one named cause below,
chosen by a fixed, structural, pre-written rule order, not by looking at
which cause would make the final count prettier.
"""

from __future__ import annotations

import math

import duckdb
import pandas as pd

from featurex import config, oracle, resolve, text_extract

CAUSES = (
    "label_not_matched",
    "duration_mismatch",
    "sign_mismatch",
    "custom_tag_different_concept",
    "unexplained_value_mismatch",
)


def _relative_close(a: float, b: float, tol: float) -> bool:
    if a == 0.0 and b == 0.0:
        return True
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tol


def reconcile_field(con: duckdb.DuckDBPyConnection, field: str) -> pd.DataFrame:
    """One row per (adsh, field) where the oracle has a ground-truth value:
    oracle_value, text_value (nullable), agree, cause (nullable when agree)."""
    kind = config.FIELD_KIND[field]
    tol = config.AGREEMENT_RELATIVE_TOLERANCE

    oracle_df = oracle.oracle_field(con, field).rename(
        columns={"tag": "oracle_tag", "value": "oracle_value"}
    )
    matched = text_extract.match_field(con, field)
    text_values = resolve.resolve_matched_values(con, matched, kind)
    text_full = matched.merge(text_values, on=["adsh", "tag"], how="left").rename(
        columns={"tag": "text_tag", "value": "text_value", "qtrs": "text_qtrs"}
    )

    merged = oracle_df.merge(
        text_full[["adsh", "text_tag", "text_value", "has_alt_duration"]],
        on="adsh",
        how="left",
    )

    oracle_tag_sets = set(config.ORACLE_TAGS[field])

    def classify(row) -> tuple[bool, str | None]:
        if pd.isna(row["text_value"]):
            return False, "label_not_matched"
        a, b = float(row["text_value"]), float(row["oracle_value"])
        if _relative_close(a, b, tol):
            return True, None
        if _relative_close(-a, b, tol):
            return False, "sign_mismatch"
        if bool(row.get("has_alt_duration")):
            return False, "duration_mismatch"
        if row["text_tag"] not in oracle_tag_sets:
            return False, "custom_tag_different_concept"
        return False, "unexplained_value_mismatch"

    results = merged.apply(classify, axis=1, result_type="expand")
    merged["agree"] = results[0]
    merged["cause"] = results[1]
    merged["field"] = field
    return merged[
        ["adsh", "field", "oracle_tag", "oracle_value", "text_tag", "text_value", "agree", "cause"]
    ]


def reconcile_all_fields(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    frames = [reconcile_field(con, field) for field in config.FIELDS]
    return pd.concat(frames, ignore_index=True)
