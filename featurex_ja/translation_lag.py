"""Median trading-day lag between a filing's real Japanese submission and
its voluntary English translation, among the fixture filings that ever
get one (`config.ENGLISH_VERSION_RATE`; most do not, by design, mirroring
the real-world fact that an English version is optional)."""

from __future__ import annotations

import datetime


def _business_days_between(a: datetime.date, b: datetime.date) -> int:
    if b < a:
        a, b = b, a
    days = 0
    d = a
    while d < b:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def measure_lag(filings) -> dict:
    lags = []
    for f in filings:
        if f.english_submit_datetime is None:
            continue
        ja = datetime.date.fromisoformat(f.japanese_submit_datetime)
        en = datetime.date.fromisoformat(f.english_submit_datetime)
        lags.append(_business_days_between(ja, en))

    if not lags:
        return {"n_with_english_version": 0, "median_lag_trading_days": None}
    lags_sorted = sorted(lags)
    n = len(lags_sorted)
    median = (lags_sorted[n // 2] if n % 2 else (lags_sorted[n // 2 - 1] + lags_sorted[n // 2]) / 2)
    return {
        "n_with_english_version": n,
        "n_total_filings": len(filings),
        "english_version_rate_measured": n / len(filings) if filings else None,
        "median_lag_trading_days": median,
        "mean_lag_trading_days": sum(lags_sorted) / n,
    }
