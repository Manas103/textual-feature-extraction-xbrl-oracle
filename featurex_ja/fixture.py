"""Builds the declared synthetic fixture standing in for real EDINET data
(see config.py's docstring for exactly why).

Each filing gets: a true value per field (the generator's own ground
truth, so precision against it is exact, not estimated), a Japanese
presentation-label snippet built from real jp vocabulary
(`config.TEXT_LABELS_JA`) for the text-rule and LLM readings to read, and
an XBRL oracle value using the real jp-gaap tag names
(`config.ORACLE_TAGS_JA`), present only `1 - NO_XBRL_TAG_RATE` of the
time (a filer tagging the concept with a non-standard extension tag, or
omitting it, is real and common in both US and Japanese XBRL and is why
`featurex`'s own oracle path is scoped the same way).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

import numpy as np

from featurex_ja import config


@dataclass
class JaFiling:
    doc_id: str
    issuer_id: str
    sec_code: str
    period_end: str
    japanese_submit_datetime: str
    english_submit_datetime: str | None
    true_values: dict  # field -> float
    label_text: dict    # field -> japanese label snippet (what a reader/LLM sees)
    oracle_values: dict  # field -> float | None (None when NO_XBRL_TAG_RATE fires)


def _add_business_days(start: datetime.date, days: float, rng: np.random.Generator) -> datetime.date:
    whole = max(0, int(round(days)))
    d = start
    added = 0
    while added < whole:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


def build_fixture(n_issuers: int = config.N_ISSUERS, n_filings: int = config.N_FILINGS,
                   seed: int = config.RANDOM_SEED) -> list[JaFiling]:
    rng = np.random.default_rng(seed)
    issuer_ids = [f"ISSUER-{i:04d}" for i in range(1, n_issuers + 1)]
    sec_codes = [f"{rng.integers(1300, 9999)}" for _ in range(n_issuers)]

    filings: list[JaFiling] = []
    today = datetime.date(2026, 10, 25)
    quarter_ends = [datetime.date(y, m, 31 if m in (3, 12) else 30)
                     for y in (2024, 2025, 2026) for m in (3, 6, 9, 12)]
    period_ends = [d for d in quarter_ends if d < today]

    for i in range(n_filings):
        issuer_idx = i % n_issuers
        issuer_id = issuer_ids[issuer_idx]
        sec_code = sec_codes[issuer_idx]
        period_end = period_ends[i % len(period_ends)]

        base_scale = float(rng.lognormal(mean=10.0, sigma=1.5))
        true_values = {
            "net_sales": base_scale,
            "operating_income": base_scale * float(rng.uniform(0.02, 0.18)),
            "net_income": base_scale * float(rng.uniform(-0.05, 0.14)),
            "total_assets": base_scale * float(rng.uniform(0.8, 2.2)),
            "net_assets": base_scale * float(rng.uniform(0.3, 1.1)),
        }

        label_text = {
            field: rng.choice(config.TEXT_LABELS_JA[field])
            for field in config.JA_FIELDS
        }

        oracle_values = {}
        for field in config.JA_FIELDS:
            if rng.random() < config.NO_XBRL_TAG_RATE:
                oracle_values[field] = None
            else:
                noise = rng.normal(0.0, config.ORACLE_ROUNDING_NOISE_STD)
                oracle_values[field] = true_values[field] * (1.0 + noise)

        submit_date = period_end + datetime.timedelta(days=int(rng.integers(30, 76)))
        if submit_date >= today:
            submit_date = today - datetime.timedelta(days=1)
        japanese_dt = submit_date.isoformat()
        english_dt = None
        if rng.random() < config.ENGLISH_VERSION_RATE:
            lag = max(0.0, rng.normal(config.ENGLISH_LAG_TRADING_DAYS_MEAN, config.ENGLISH_LAG_TRADING_DAYS_STD))
            english_date = _add_business_days(submit_date, lag, rng)
            if english_date >= today:
                english_date = today - datetime.timedelta(days=1)
            english_dt = english_date.isoformat()

        filings.append(JaFiling(
            doc_id=f"DOC-{i:06d}",
            issuer_id=issuer_id,
            sec_code=sec_code,
            period_end=period_end.isoformat(),
            japanese_submit_datetime=japanese_dt,
            english_submit_datetime=english_dt,
            true_values=true_values,
            label_text=label_text,
            oracle_values=oracle_values,
        ))
    return filings


def n_distinct_issuers(filings: list[JaFiling]) -> int:
    return len({f.issuer_id for f in filings})
