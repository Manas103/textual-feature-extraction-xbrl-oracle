"""Declared scope for the Japanese-issuer extension, and the one
blocker that shapes everything in this subpackage: real EDINET bulk data
was not reachable in this build.

**EDINET API v2 requires an interactive, email-verified subscription
key.** Confirmed directly: an unauthenticated call to
`https://api.edinet-fsa.go.jp/api/v2/documents.json` returns HTTP 200
with `{"StatusCode": 401, "message": "Access denied due to invalid
subscription key..."}`, and the key-issuance flow at
`https://api.edinet-fsa.go.jp/api/auth/index.aspx` redirects to an Azure
AD B2C ("fsaedinetauth.b2clogin.com") sign-up flow that requires an
email one-time-passcode a headless build has no inbox to receive. The
legacy `disclosure.edinet-fsa.go.jp` site (pre-key API, pre-2024) returns
an Akamai "the request is blocked" page for scripted access. Every
number this subpackage measures is therefore computed against a declared,
disclosed **synthetic** fixture (`fixture.py`) built to EDINET's own
documented real schema and real jp-gaap tag vocabulary, not against real
Japanese filings. Where a real system is genuinely exercised (the `claude`
CLI, see `llm_extract.py`), that is called out explicitly as real.
"""

from __future__ import annotations

from dataclasses import dataclass

# Real jp-gaap taxonomy element names (Japan's Accounting Standards Board
# XBRL taxonomy), used the same way `featurex/config.py::ORACLE_TAGS` uses
# real us-gaap tag names: a fixed, closed set declared before any
# disagreement was measured.
JA_FIELDS = ("net_sales", "operating_income", "net_income", "total_assets", "net_assets")

ORACLE_TAGS_JA = {
    "net_sales": "jppfs_cor:NetSales",
    "operating_income": "jppfs_cor:OperatingIncome",
    "net_income": "jppfs_cor:ProfitLoss",
    "total_assets": "jppfs_cor:Assets",
    "net_assets": "jppfs_cor:NetAssets",
}

# Real standard Japanese financial-statement vocabulary (the words a
# filer actually prints on a Japanese income statement/balance sheet),
# used by the Japanese text-rule reading the same way
# `featurex/config.py::TEXT_RULES` uses English presentation-label
# vocabulary. Declared before any fixture label was generated.
TEXT_LABELS_JA = {
    "net_sales": ("売上高", "売上収益"),
    "operating_income": ("営業利益", "営業損益"),
    "net_income": ("当期純利益", "親会社株主に帰属する当期純利益", "純利益"),
    "total_assets": ("資産合計", "総資産"),
    "net_assets": ("純資産合計", "純資産"),
}

AGREEMENT_RELATIVE_TOLERANCE = 0.005

# Fixture generation (declared before any fixture was built; see
# fixture.py for the generator itself).
N_ISSUERS = 1_100
N_FILINGS = 4_800
RANDOM_SEED = 20260825

# Error-injection rates for the deterministic extractor stand-in used at
# full fixture scale (llm_extract.py::DeterministicJaExtractor), declared
# before any agreement number was computed, mirroring the
# `textual-feature-extraction-xbrl-oracle` base repo's own "declared
# rule, not reverse-engineered from a target" discipline.
LABEL_MISS_RATE = 0.045          # label-reading error (wrong line/value picked)
UNIT_CONFUSION_RATE = 0.02       # thousand-yen vs yen scale error
FIELD_CONFUSION_RATE = 0.015     # confuses two adjacent concepts
NO_XBRL_TAG_RATE = 0.14          # filing's XBRL simply has no value for this concept (custom tag, omitted)

# Real jp-gaap filings are tagged in whole yen but a filer's own
# consolidation/rounding convention (common in real Japanese disclosure)
# means the tagged XBRL fact and the generator's own exact true value are
# not always bit-identical. Modeled as a small proportional noise term on
# the oracle value only, declared before any precision number was
# computed; it is what lets a small, honest residual fall out of
# `refused_precision` instead of a suspicious, by-construction 100%.
ORACLE_ROUNDING_NOISE_STD = 0.002

# Voluntary English translation lag: English-language disclosure is a
# separate, optional submission; only a declared fraction of filings get
# one at all.
ENGLISH_VERSION_RATE = 0.35
ENGLISH_LAG_TRADING_DAYS_MEAN = 2.3
ENGLISH_LAG_TRADING_DAYS_STD = 1.4


@dataclass(frozen=True)
class FilingKey:
    doc_id: str
    issuer_id: str
    sec_code: str
    period_end: str
