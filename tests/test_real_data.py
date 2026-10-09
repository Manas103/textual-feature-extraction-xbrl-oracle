"""Integration tests against the real, already-built SEC database. Skip
(not fail) when the multi-GB bulk files have not been downloaded on this
machine; see conftest.real_con."""

from __future__ import annotations

import pandas as pd
import pytest

from featurex import config, measurements, oracle, reconcile


@pytest.fixture(scope="session")
def reconciled(real_con):
    return reconcile.reconcile_all_fields(real_con)


def test_scale_claim(real_con):
    m = measurements.measure_scale(real_con)
    assert m["n_fields"] == 9
    assert m["n_filings"] >= 14000


def test_point_in_time_claim(real_con, reconciled):
    m = measurements.measure_point_in_time(real_con, reconciled)
    assert m["correct_filter_leaked_rows"] == 0
    assert m["naive_filed_date_filter_leaked_rows"] > 0
    assert m["value"] is True


def test_oracle_is_deterministic(real_con):
    m = measurements.measure_oracle_determinism(real_con)
    assert m["value"] is True


def test_every_disagreement_has_a_cause(reconciled):
    m = measurements.measure_disagreement_classification(reconciled)
    assert m["classified"] == m["total_disagreements"]


def test_field_agreement_is_measured_not_assumed(reconciled):
    m = measurements.measure_field_agreement(reconciled)
    assert 0.0 < m["rate_pct"] < 100.0
    assert m["total"] > 100000
