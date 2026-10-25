"""Unit tests for the Japanese-issuer extension, no network. One test per
mechanism: fixture dates, text-rule matching, the refusal rule, and
translation-lag measurement."""

import datetime

import pytest

from featurex_ja import audit, config, fixture, text_extract_ja, translation_lag
from featurex_ja.llm_extract import DeterministicJaExtractor


def test_fixture_dates_are_never_in_the_future():
    filings = fixture.build_fixture(n_issuers=20, n_filings=100)
    today = datetime.date(2026, 10, 25)
    for f in filings:
        assert datetime.date.fromisoformat(f.japanese_submit_datetime) < today
        if f.english_submit_datetime:
            assert datetime.date.fromisoformat(f.english_submit_datetime) < today
        assert datetime.date.fromisoformat(f.period_end) < today


def test_fixture_issuer_count_matches_request():
    filings = fixture.build_fixture(n_issuers=37, n_filings=200)
    assert fixture.n_distinct_issuers(filings) == 37


def test_text_rule_matches_declared_vocabulary_only():
    assert text_extract_ja.match_label("売上高") == "net_sales"
    assert text_extract_ja.match_label("営業利益") == "operating_income"
    assert text_extract_ja.match_label("当期純利益") == "net_income"
    assert text_extract_ja.match_label("something unrelated") is None


def test_deterministic_extractor_is_reproducible_given_same_seed():
    filings = fixture.build_fixture(n_issuers=10, n_filings=50)
    a = DeterministicJaExtractor(seed=42)
    b = DeterministicJaExtractor(seed=42)
    values_a = [a.extract(f, "net_sales") for f in filings]
    values_b = [b.extract(f, "net_sales") for f in filings]
    assert values_a == values_b


class _FakeLLM:
    """Always returns the true value: isolates the refusal rule from the
    extractor's own error process."""
    def extract(self, filing, field):
        return filing.true_values[field]


def test_refusal_rule_blocks_fields_the_oracle_cannot_confirm():
    filings = fixture.build_fixture(n_issuers=5, n_filings=5)
    llm = _FakeLLM()
    results = audit.reconcile_all(filings, llm)
    for r in results:
        if r.oracle_value is None:
            assert r.refused is True
            assert r.accepted_value is None


def test_accepted_fields_are_always_correct_when_llm_is_perfect():
    filings = fixture.build_fixture(n_issuers=5, n_filings=5)
    llm = _FakeLLM()
    results = audit.reconcile_all(filings, llm)
    accepted = [r for r in results if not r.refused]
    assert all(r.correct_given_accepted for r in accepted)
    assert len(accepted) > 0


class _AlwaysWrongLLM:
    def extract(self, filing, field):
        other = [f for f in config.JA_FIELDS if f != field][0]
        return filing.true_values[other]


def test_refusal_rule_catches_almost_every_wrong_llm_value_when_oracle_present():
    # The oracle carries its own small, declared rounding noise
    # (config.ORACLE_ROUNDING_NOISE_STD), so a rare coincidental near-match
    # between a wrong field's value and the correct field's noisy oracle
    # is possible; the refusal rule's job is to catch the overwhelming
    # majority, not force a mathematically impossible zero.
    filings = fixture.build_fixture(n_issuers=200, n_filings=200)
    llm = _AlwaysWrongLLM()
    results = audit.reconcile_all(filings, llm)
    confirmable = [r for r in results if r.oracle_value is not None]
    assert confirmable, "fixture should produce at least one oracle-confirmable field"
    refused_rate = sum(1 for r in confirmable if r.refused) / len(confirmable)
    assert refused_rate > 0.97


def test_translation_lag_only_counts_filings_with_an_english_version():
    filings = fixture.build_fixture(n_issuers=50, n_filings=300)
    result = translation_lag.measure_lag(filings)
    assert 0 < result["n_with_english_version"] < result["n_total_filings"]
    assert result["median_lag_trading_days"] >= 0
