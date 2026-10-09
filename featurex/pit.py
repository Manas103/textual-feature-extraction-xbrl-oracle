"""Point-in-time discipline: a feature is never knowable before the filing
that carries it was accepted by EDGAR.

`accepted` in `submissions` is a real timestamp (date and time), not just a
date. An earlier version of this filter used `filed <= as_of_date` (dates
only) and leaked: EDGAR timestamps many filings late in the trading day, so
a same-calendar-day cutoff let an afternoon filing's features count as known
as of that morning. See the README for the measured size of that leak before
it was fixed.
"""

from __future__ import annotations

import datetime

import duckdb
import pandas as pd


def features_as_of(con: duckdb.DuckDBPyConnection, reconciled: pd.DataFrame, as_of: datetime.datetime) -> pd.DataFrame:
    """Every reconciled row for a filing whose acceptance timestamp is at or
    before `as_of`."""
    accepted = con.execute("SELECT adsh, accepted FROM submissions").fetchdf()
    merged = reconciled.merge(accepted, on="adsh", how="left")
    return merged[merged["accepted"] <= as_of].drop(columns=["accepted"])


def leaky_filed_date_as_of(con: duckdb.DuckDBPyConnection, reconciled: pd.DataFrame, as_of_date: datetime.date) -> pd.DataFrame:
    """The deliberately wrong version kept only to measure the leak it
    caused: filters by the filing's `filed` date with no time of day."""
    filed = con.execute("SELECT adsh, filed FROM submissions").fetchdf()
    merged = reconciled.merge(filed, on="adsh", how="left")
    cutoff = pd.Timestamp(as_of_date)
    return merged[merged["filed"] <= cutoff].drop(columns=["filed"])
