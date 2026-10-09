"""Unit tests for the reconciliation classifier against a small, handcrafted
set of filings, one built to trigger each named disagreement cause on
purpose, independent of whatever the real SEC data happens to contain.
"""

from __future__ import annotations

import datetime

import duckdb
import pandas as pd
import pytest

from featurex import load, reconcile


@pytest.fixture
def synthetic_con():
    con = duckdb.connect(":memory:")
    con.execute(load.SCHEMA)

    period = datetime.date(2025, 12, 31)
    filed = datetime.date(2026, 1, 20)
    accepted = datetime.datetime(2026, 1, 20, 16, 0, 0)

    submissions = [
        ("adsh1", 1, "AGREE CO", "10-K", period, 2025, "FY", filed, accepted, "q"),
        ("adsh2", 2, "LABEL MISS CO", "10-K", period, 2025, "FY", filed, accepted, "q"),
        ("adsh3", 3, "SIGN FLIP CO", "10-K", period, 2025, "FY", filed, accepted, "q"),
        ("adsh4", 4, "DURATION CO", "10-K", period, 2025, "FY", filed, accepted, "q"),
        ("adsh5", 5, "CUSTOM TAG CO", "10-K", period, 2025, "FY", filed, accepted, "q"),
        ("adsh6", 6, "PRIORITY CO", "10-K", period, 2025, "FY", filed, accepted, "q"),
    ]
    con.executemany(
        "INSERT INTO submissions VALUES (?,?,?,?,?,?,?,?,?,?)", submissions
    )

    num_rows = [
        # adsh1: clean agreement.
        ("adsh1", "Revenues", "us-gaap/2025", period, 4, "USD", None, None, 100.0),
        # adsh2: oracle has a value; no pre.txt line will match any rule.
        ("adsh2", "Revenues", "us-gaap/2025", period, 4, "USD", None, None, 200.0),
        # adsh3: text path's own tag is negated relative to the oracle's.
        ("adsh3", "Revenues", "us-gaap/2025", period, 4, "USD", None, None, 300.0),
        ("adsh3", "CustomNegatedRevTag", "us-gaap/2025", period, 4, "USD", None, None, -300.0),
        # adsh4: text path picks a tag whose *expected*-duration value is
        # wrong, but an alternate-duration row for that same tag matches.
        ("adsh4", "Revenues", "us-gaap/2025", period, 4, "USD", None, None, 1000.0),
        ("adsh4", "SalesRevenueNet", "us-gaap/2025", period, 4, "USD", None, None, 250.0),
        ("adsh4", "SalesRevenueNet", "us-gaap/2025", period, 1, "USD", None, None, 1000.0),
        # adsh5: text path's tag is not an oracle tag for this field at all.
        ("adsh5", "Revenues", "us-gaap/2025", period, 4, "USD", None, None, 500.0),
        ("adsh5", "TotallyUnrelatedTag", "us-gaap/2025", period, 4, "USD", None, None, 777.0),
        # adsh6: two real oracle tags disagree; text matches the lower-priority one.
        ("adsh6", "Revenues", "us-gaap/2025", period, 4, "USD", None, None, 600.0),
        (
            "adsh6",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap/2025",
            period,
            4,
            "USD",
            None,
            None,
            650.0,
        ),
    ]
    con.executemany(
        "INSERT INTO num VALUES (?,?,?,?,?,?,?,?,?)", num_rows
    )

    pre_rows = [
        ("adsh1", 1, 1, "IS", 0, "H", "Revenues", "us-gaap/2025", "Total revenue", 0),
        ("adsh2", 1, 1, "IS", 0, "H", "SomeOtherTag", "us-gaap/2025", "Segment contribution detail", 0),
        ("adsh3", 1, 1, "IS", 0, "H", "CustomNegatedRevTag", "us-gaap/2025", "Total revenue", 1),
        ("adsh4", 1, 1, "IS", 0, "H", "SalesRevenueNet", "us-gaap/2025", "Total revenue", 0),
        ("adsh5", 1, 1, "IS", 0, "H", "TotallyUnrelatedTag", "us-gaap/2025", "Total revenue", 0),
        (
            "adsh6",
            1,
            1,
            "IS",
            0,
            "H",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap/2025",
            "Total revenue",
            0,
        ),
    ]
    con.executemany(
        "INSERT INTO pre VALUES (?,?,?,?,?,?,?,?,?,?)", pre_rows
    )
    return con


def test_each_cause_fires_on_the_filing_built_for_it(synthetic_con):
    df = reconcile.reconcile_field(synthetic_con, "total_revenue")
    by_adsh = df.set_index("adsh")

    assert bool(by_adsh.loc["adsh1", "agree"]) is True
    assert pd.isna(by_adsh.loc["adsh1", "cause"])

    assert bool(by_adsh.loc["adsh2", "agree"]) is False
    assert by_adsh.loc["adsh2", "cause"] == "label_not_matched"

    assert bool(by_adsh.loc["adsh3", "agree"]) is False
    assert by_adsh.loc["adsh3", "cause"] == "sign_mismatch"

    assert bool(by_adsh.loc["adsh4", "agree"]) is False
    assert by_adsh.loc["adsh4", "cause"] == "duration_mismatch"

    assert bool(by_adsh.loc["adsh5", "agree"]) is False
    assert by_adsh.loc["adsh5", "cause"] == "custom_tag_different_concept"

    assert bool(by_adsh.loc["adsh6", "agree"]) is False
    assert by_adsh.loc["adsh6", "cause"] == "unexplained_value_mismatch"


def test_every_row_has_oracle_ground_truth(synthetic_con):
    df = reconcile.reconcile_field(synthetic_con, "total_revenue")
    assert df["oracle_value"].notna().all()
    assert len(df) == 6
