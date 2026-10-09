"""Turn a (adsh, tag, version) candidate into the one real numeric value it
names, using the filing's own form and period from `submissions` to pick the
right duration.

Every lookup is restricted to `coreg IS NULL AND segments IS NULL`: the
consolidated, top-of-statement figure, not a guarantor subsidiary or a
segment/member breakdown row. `qtrs` is fixed by form: a 10-K's income
statement and cash flow figures are the full fiscal year (qtrs = 4); a
10-Q's are the single reported quarter (qtrs = 1), not the year-to-date
column XBRL also tags alongside it. That second choice is a declared
simplification: a real 10-Q often carries both, and this project always
takes the quarterly one.
"""

from __future__ import annotations

import duckdb
import pandas as pd


def expected_qtrs(form: str, kind: str) -> int:
    if kind == "instant":
        return 0
    return 4 if form == "10-K" else 1


def resolve_values(con: duckdb.DuckDBPyConnection, tags: tuple[str, ...], kind: str) -> "duckdb.DuckDBPyRelation":
    """All (adsh, tag, value, qtrs) rows, one candidate row per (adsh, tag),
    restricted to the consolidated figure at the filing's own expected
    duration. Returns a DuckDB relation; callers decide tag priority.
    """
    tag_list = ", ".join(f"'{t}'" for t in tags)
    return con.sql(
        f"""
        SELECT n.adsh, n.tag, n.value, n.qtrs,
               EXISTS (
                   SELECT 1 FROM num n2
                   WHERE n2.adsh = n.adsh AND n2.tag = n.tag
                     AND n2.coreg IS NULL AND n2.segments IS NULL
                     AND n2.ddate = s.period AND n2.qtrs != n.qtrs
               ) AS has_alt_duration
        FROM num n
        JOIN submissions s ON s.adsh = n.adsh
        WHERE n.tag IN ({tag_list})
          AND n.coreg IS NULL AND n.segments IS NULL
          AND n.value IS NOT NULL
          AND n.ddate = s.period
          AND n.qtrs = (CASE WHEN '{kind}' = 'instant' THEN 0
                              WHEN s.form = '10-K' THEN 4 ELSE 1 END)
        """
    )


def resolve_matched_values(
    con: duckdb.DuckDBPyConnection, matched: pd.DataFrame, kind: str
) -> pd.DataFrame:
    """Resolve a text-match table (adsh, tag, version, line) to its one
    consolidated value at the filing's own expected duration, plus whether
    an alternate-duration value exists for the same tag (a diagnostic for
    the duration_mismatch disagreement cause).
    """
    con.register("_matched", matched[["adsh", "tag"]])
    out = con.sql(
        """
        SELECT m.adsh, m.tag, n.value, n.qtrs,
               EXISTS (
                   SELECT 1 FROM num n2
                   WHERE n2.adsh = n.adsh AND n2.tag = n.tag
                     AND n2.coreg IS NULL AND n2.segments IS NULL
                     AND n2.ddate = s.period AND n2.qtrs != n.qtrs
               ) AS has_alt_duration
        FROM _matched m
        JOIN submissions s ON s.adsh = m.adsh
        JOIN num n ON n.adsh = m.adsh AND n.tag = m.tag
                   AND n.coreg IS NULL AND n.segments IS NULL
                   AND n.value IS NOT NULL
                   AND n.ddate = s.period
                   AND n.qtrs = (CASE WHEN ? = 'instant' THEN 0
                                       WHEN s.form = '10-K' THEN 4 ELSE 1 END)
        """,
        params=[kind],
    ).fetchdf()
    con.unregister("_matched")
    return out.drop_duplicates(subset=["adsh"])
