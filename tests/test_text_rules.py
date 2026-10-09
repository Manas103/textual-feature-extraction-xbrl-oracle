"""Unit tests for the text-match rules against real plabel strings this
dataset actually contains, including the ones a first pass of these rules
missed (see README Findings)."""

from __future__ import annotations

from featurex import config


def test_total_revenue_matches_bare_and_total_forms():
    rule = config.TEXT_RULES["total_revenue"]
    assert rule.matches("revenue")
    assert rule.matches("total revenue")
    assert rule.matches("net sales")
    assert rule.matches("product sales, net")
    assert not rule.matches("cost of revenue")
    assert not rule.matches("sales and marketing")
    assert not rule.matches("deferred revenue")


def test_net_income_matches_parenthetical_orderings():
    rule = config.TEXT_RULES["net_income"]
    assert rule.matches("net (loss) income")
    assert rule.matches("net income (loss)")
    assert rule.matches("net loss and comprehensive loss")
    assert not rule.matches("net loss per common share - diluted")
    assert not rule.matches("net income attributable to noncontrolling interests")


def test_total_stockholders_equity_matches_apostrophe_and_fund_vocabulary():
    rule = config.TEXT_RULES["total_stockholders_equity"]
    assert rule.matches("total stockholder's equity")
    assert rule.matches("total stockholders deficit")
    assert rule.matches("total net assets")
    assert not rule.matches("total liabilities and stockholders equity")


def test_diluted_shares_outstanding_matches_without_requiring_weighted_average():
    rule = config.TEXT_RULES["diluted_shares_outstanding"]
    assert rule.matches("diluted (in shares)")
    assert rule.matches("weighted average number of diluted shares outstanding")
    assert not rule.matches("diluted (in dollars per share)")


def test_diluted_shares_outstanding_does_not_resolve_bare_diluted_label():
    """A disclosed limitation, not a bug: a bare "Diluted" plabel with no
    other word on the line is genuinely ambiguous between the EPS value and
    the share count by text alone, and this project does not try to resolve
    it from statement position."""
    rule = config.TEXT_RULES["diluted_shares_outstanding"]
    assert not rule.matches("diluted")
