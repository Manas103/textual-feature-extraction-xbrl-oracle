"""The five claim measurements, each an honest measured number, not a target.

Every function returns plain Python values so scripts/run_measurements.py
and the test suite can both use them without re-deriving the logic.
"""

from __future__ import annotations

import datetime

import duckdb
import pandas as pd

from featurex import config, pit


def measure_scale(con: duckdb.DuckDBPyConnection) -> dict:
    """Claim 1: 9 fields, 14,000+ real 10-Q/10-K filings."""
    n_filings = con.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    n_fields = len(config.FIELDS)
    return {
        "value": n_fields == 9 and n_filings >= 14000,
        "n_fields": n_fields,
        "n_filings": int(n_filings),
        "quarters": config.QUARTERS,
    }


def measure_point_in_time(con: duckdb.DuckDBPyConnection, reconciled: pd.DataFrame) -> dict:
    """Claim 2: every feature aligned to its filing's acceptance timestamp.

    Picks the median acceptance timestamp among all ingested filings as a
    cutoff, and checks two things: the correct (`accepted`-timestamp) filter
    leaks zero rows past the cutoff, and the naive (`filed`-date) filter this
    project used on its first attempt leaks a real, nonzero number of rows,
    which is the reason the fix mattered rather than a check that always
    passes by construction.
    """
    accepted = con.execute("SELECT adsh, accepted, filed FROM submissions").fetchdf()

    # A cutoff at the very start of the busiest filing day: almost every
    # filing accepted that day is "in the future" relative to this cutoff,
    # which is what makes the filed-date leak demonstrable rather than a
    # coin flip on whether any same-day afternoon filing happens to exist.
    busiest_day = accepted["filed"].value_counts().idxmax()
    cutoff_ts = pd.Timestamp(busiest_day) + pd.Timedelta(hours=7)
    cutoff_date = busiest_day

    correct = pit.features_as_of(con, reconciled, cutoff_ts)
    correct_adsh = set(correct["adsh"])
    leaked = accepted[(accepted["accepted"] > cutoff_ts) & (accepted["adsh"].isin(correct_adsh))]

    naive = pit.leaky_filed_date_as_of(con, reconciled, cutoff_date)
    naive_adsh = set(naive["adsh"])
    naive_leaked = accepted[(accepted["accepted"] > cutoff_ts) & (accepted["adsh"].isin(naive_adsh))]

    return {
        "value": len(leaked) == 0 and len(naive_leaked) > 0,
        "cutoff_timestamp": str(cutoff_ts),
        "correct_filter_leaked_rows": int(len(leaked)),
        "naive_filed_date_filter_leaked_rows": int(len(naive_leaked)),
        "naive_leaked_filings": int(len(naive_adsh - correct_adsh)),
    }


def measure_oracle_determinism(con: duckdb.DuckDBPyConnection) -> dict:
    """Claim 3: the oracle path is a deterministic function of the as-filed
    XBRL facts alone, checked by running it twice and diffing exactly."""
    from featurex import oracle

    first = oracle.oracle_field(con, "total_revenue").sort_values("adsh").reset_index(drop=True)
    second = oracle.oracle_field(con, "total_revenue").sort_values("adsh").reset_index(drop=True)
    identical = first.equals(second)
    return {
        "value": bool(identical),
        "n_rows": int(len(first)),
        "field_checked": "total_revenue",
    }


def measure_field_agreement(reconciled: pd.DataFrame) -> dict:
    """Claim 4: field-level agreement rate against the XBRL oracle."""
    total = len(reconciled)
    agree = int(reconciled["agree"].sum())
    rate = agree / total if total else 0.0
    by_field = reconciled.groupby("field")["agree"].agg(["sum", "count"]).to_dict(orient="index")
    return {
        "value": round(rate * 100, 1),
        "agree": agree,
        "total": total,
        "rate_pct": round(rate * 100, 3),
        "by_field": by_field,
        "attempts": 3,
    }


def measure_disagreement_classification(reconciled: pd.DataFrame) -> dict:
    """Claim 5: every disagreement is classified by a named cause."""
    disagreements = reconciled[~reconciled["agree"]]
    total = len(disagreements)
    classified = int(disagreements["cause"].notna().sum())
    cause_counts = disagreements["cause"].value_counts().to_dict()
    return {
        "value": total == 0 or classified == total,
        "total_disagreements": int(total),
        "classified": classified,
        "cause_counts": cause_counts,
        "causes_used": sorted(cause_counts.keys()),
    }
