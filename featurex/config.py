"""The 9 canonical fields, their oracle tag sets, and their text-match rules.

Two independent definitions of "what counts as revenue" (or net income, or
any of the other 7 fields) live in this one file, on purpose: ORACLE_TAGS is
a lookup by the filing's own us-gaap tag name (what the filer's XBRL
actually says the concept is), and TEXT_RULES is a lookup by the filing's
own human-readable presentation label (what a reader sees on the page). A
disagreement between the two paths is a real signal, not a recomputation of
the same thing twice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEC_USER_AGENT = "AutoJobApplierBuild manas.vudugula1@gmail.com"

QUARTERS = ["2025q3", "2025q4", "2026q1", "2026q2"]

FSDS_URL_TEMPLATE = (
    "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{quarter}.zip"
)

# "flow" fields are measured over a period (duration, qtrs != 0 in num.txt);
# "instant" fields are measured at a point in time (qtrs == 0).
FIELDS = (
    "total_revenue",
    "cost_of_revenue",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_stockholders_equity",
    "operating_cash_flow",
    "eps_diluted",
    "diluted_shares_outstanding",
)

FIELD_KIND = {
    "total_revenue": "flow",
    "cost_of_revenue": "flow",
    "net_income": "flow",
    "total_assets": "instant",
    "total_liabilities": "instant",
    "total_stockholders_equity": "instant",
    "operating_cash_flow": "flow",
    "eps_diluted": "flow",
    "diluted_shares_outstanding": "flow",
}

# The statement a field's primary presentation line is expected on, matching
# pre.txt's own `stmt` column (IS = income statement, BS = balance sheet,
# CF = cash flow statement).
FIELD_STATEMENT = {
    "total_revenue": "IS",
    "cost_of_revenue": "IS",
    "net_income": "IS",
    "total_assets": "BS",
    "total_liabilities": "BS",
    "total_stockholders_equity": "BS",
    "operating_cash_flow": "CF",
    "eps_diluted": "IS",
    "diluted_shares_outstanding": "IS",
}

# The oracle side: a fixed, closed, ordered list of standard us-gaap tags
# per field, chosen before any disagreement was ever measured, from the
# tags' own published definitions in tag.txt, not from reading pre.txt
# labels. Order is a deterministic priority (first tag with a matching
# num.txt row wins) for the rare filing that tags the same concept two ways.
ORACLE_TAGS = {
    "total_revenue": (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ),
    "cost_of_revenue": (
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
        "CostOfGoodsSold",
        "CostOfServices",
    ),
    "net_income": (
        "NetIncomeLoss",
        "ProfitLoss",
    ),
    "total_assets": (
        "Assets",
    ),
    "total_liabilities": (
        "Liabilities",
    ),
    "total_stockholders_equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
    "operating_cash_flow": (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ),
    "eps_diluted": (
        "EarningsPerShareDiluted",
    ),
    "diluted_shares_outstanding": (
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfDilutedSharesOutstandingIncludingDilutiveSecurities",
    ),
}


@dataclass(frozen=True)
class TextRule:
    """A field's text-match rule, applied to a lowercased plabel string."""

    must_all: tuple[str, ...] = ()
    must_any: tuple[str, ...] = ()
    must_not: tuple[str, ...] = ()
    any_groups: tuple[tuple[str, ...], ...] = ()

    def matches(self, label_lower: str) -> bool:
        if not all(term in label_lower for term in self.must_all):
            return False
        if self.must_any and not any(term in label_lower for term in self.must_any):
            return False
        for group in self.any_groups:
            if not any(term in label_lower for term in group):
                return False
        if any(term in label_lower for term in self.must_not):
            return False
        return True


# The text side: keyword rules over the filer's own presentation label
# (pre.txt plabel), written from the vocabulary of real filings, not from
# the oracle tag names above. A filer who writes "Total revenues" and tags
# it with a custom, non-standard concept still matches here; that is
# exactly the case this project exists to catch. These rules were revised
# once, against the real vocabulary this dataset actually uses (parenthetical
# "Net (loss) income", "Net cash provided from operating activities", the
# apostrophed "Total Stockholder's Equity"), before any agreement number was
# computed a second time; see the README Findings for what the first pass
# missed and why.
TEXT_RULES: dict[str, TextRule] = {
    "total_revenue": TextRule(
        must_any=("revenue", "net sales", "total sales", "product sales"),
        must_not=("cost", "deferred", "unearned", "per share", "growth", "recognized", "marketing"),
    ),
    "cost_of_revenue": TextRule(
        must_any=(
            "cost of revenue", "cost of sales", "cost of goods", "cost of service", "cost of products",
            "costs of revenue", "costs of sales", "costs of goods", "costs of service", "costs of products",
            "cogs",
        ),
        must_not=("per share",),
    ),
    "net_income": TextRule(
        must_any=(
            "net income", "net loss", "net earnings",
            "net (loss) income", "net (income) loss",
            "net loss (income)", "net income (loss)",
        ),
        must_not=(
            "per share", "per common share", "per basic share", "per diluted share",
            "attributable to noncontrolling", "margin",
        ),
    ),
    "total_assets": TextRule(
        must_all=("total assets",),
        must_not=("net",),
    ),
    "total_liabilities": TextRule(
        must_all=("total liabilities",),
        must_not=("stockholders", "shareholders", "equity"),
    ),
    "total_stockholders_equity": TextRule(
        any_groups=(
            ("stockholder", "shareholder", "net assets"),
            ("equity", "deficit", "net assets"),
        ),
        must_any=("total",),
        must_not=("noncontrolling", "liabilities"),
    ),
    "operating_cash_flow": TextRule(
        must_all=("operating activities",),
        must_any=("net cash",),
    ),
    "eps_diluted": TextRule(
        must_all=("diluted", "per share"),
        must_not=("weighted average", "shares"),
    ),
    "diluted_shares_outstanding": TextRule(
        must_all=("diluted", "shares"),
        must_not=("per share",),
    ),
}

# Relative tolerance for two numeric values to count as agreeing. 0.5% absorbs
# harmless floating-point and rounding noise without papering over a real
# mismatch; every field here is a 6+ figure dollar amount, share count, or a
# per-share value, so an absolute tolerance would not scale across them.
AGREEMENT_RELATIVE_TOLERANCE = 0.005

FORMS = ("10-Q", "10-K")
