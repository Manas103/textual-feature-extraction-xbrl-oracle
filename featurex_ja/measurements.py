"""The 5 claims, each measured against the declared synthetic fixture
(see config.py for exactly why real EDINET data could not be used) with
the deterministic extractor at full scale, except where a script
explicitly substitutes the real `claude` CLI client on a live sample."""

from __future__ import annotations

from featurex_ja import audit, fixture, translation_lag


def measure_scale(filings) -> dict:
    return {
        "n_filings": len(filings),
        "n_issuers": fixture.n_distinct_issuers(filings),
        "n_fields": 5,
    }


def measure_raw_agreement(results: list[audit.FieldResult]) -> dict:
    """Claim: raw field agreement between the two independent readings
    (LLM extraction vs. the Japanese text-rule match), before the oracle
    refusal rule is applied."""
    comparable = [r for r in results if r.raw_agrees_with_text_rule is not None]
    agree = sum(1 for r in comparable if r.raw_agrees_with_text_rule)
    rate = agree / len(comparable) if comparable else None
    return {
        "n_comparable": len(comparable),
        "n_total": len(results),
        "agree": agree,
        "rate_pct": round(100.0 * rate, 1) if rate is not None else None,
    }


def measure_refused_precision(results: list[audit.FieldResult]) -> dict:
    """Claim: precision and coverage after refusing any field the
    filing's own XBRL facts do not confirm."""
    total = len(results)
    accepted = [r for r in results if not r.refused]
    correct = sum(1 for r in accepted if r.correct_given_accepted)
    incorrect = len(accepted) - correct
    coverage = len(accepted) / total if total else None
    precision = correct / len(accepted) if accepted else None
    return {
        "n_total": total,
        "n_accepted": len(accepted),
        "n_refused": total - len(accepted),
        "n_accepted_but_incorrect": incorrect,
        "coverage_pct": round(100.0 * coverage, 1) if coverage is not None else None,
        "precision_pct": round(100.0 * precision, 3) if precision is not None else None,
    }


def measure_translation_lag(filings) -> dict:
    return translation_lag.measure_lag(filings)


def run_all_measurements(filings, results: list[audit.FieldResult]) -> dict:
    return {
        "scale": measure_scale(filings),
        "raw_agreement": measure_raw_agreement(results),
        "refused_precision": measure_refused_precision(results),
        "translation_lag": measure_translation_lag(filings),
    }
