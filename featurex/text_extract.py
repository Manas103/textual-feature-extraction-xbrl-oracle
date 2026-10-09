"""The text path: match a filing's own human-readable presentation label.

For each field, every pre.txt row on that field's expected statement is
tested against the field's TextRule, lowercased. A filing can have more than
one matching line (a subtotal and a segment reconciliation both saying
"total revenues", for instance); the lowest `line` number wins, since
line order mirrors a reader's top-to-bottom reading of the statement and the
primary consolidated total is reported before any breakdown of it.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from featurex import config


def _candidate_rows(con: duckdb.DuckDBPyConnection, stmt: str) -> pd.DataFrame:
    return con.execute(
        """
        SELECT adsh, line, tag, version, plabel
        FROM pre
        WHERE stmt = ? AND inpth = 0 AND plabel IS NOT NULL
        """,
        [stmt],
    ).fetchdf()


def match_field(con: duckdb.DuckDBPyConnection, field: str) -> pd.DataFrame:
    """One row per filing that matched `field`'s text rule: adsh, tag, version."""
    stmt = config.FIELD_STATEMENT[field]
    rule = config.TEXT_RULES[field]
    rows = _candidate_rows(con, stmt)
    mask = rows["plabel"].str.lower().apply(rule.matches)
    matched = rows[mask].sort_values(["adsh", "line"])
    winners = matched.groupby("adsh", as_index=False).first()
    return winners[["adsh", "tag", "version", "line"]]


def match_all_fields(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    return {field: match_field(con, field) for field in config.FIELDS}
