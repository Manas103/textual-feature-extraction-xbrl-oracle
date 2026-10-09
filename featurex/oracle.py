"""The oracle path: look a field up by its standard us-gaap tag name alone.

This never reads a plabel. It is the deterministic ground truth the text
path (text_extract.py) is checked against: for each field, every filing's
own num.txt facts are scanned for one of a fixed, closed set of standard
tags (config.ORACLE_TAGS), independent of whatever label the filer chose to
print next to the number.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from featurex import config, resolve


def oracle_field(con: duckdb.DuckDBPyConnection, field: str) -> pd.DataFrame:
    """One row per filing with a value for `field`: adsh, tag, value."""
    tags = config.ORACLE_TAGS[field]
    kind = config.FIELD_KIND[field]
    rel = resolve.resolve_values(con, tags, kind)
    df = rel.fetchdf()
    if df.empty:
        return pd.DataFrame(columns=["adsh", "tag", "value"])
    priority = {tag: i for i, tag in enumerate(tags)}
    df["priority"] = df["tag"].map(priority)
    df = df.sort_values(["adsh", "priority"]).groupby("adsh", as_index=False).first()
    return df[["adsh", "tag", "value"]]


def oracle_all_fields(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    return {field: oracle_field(con, field) for field in config.FIELDS}
