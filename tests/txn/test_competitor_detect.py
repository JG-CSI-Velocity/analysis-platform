"""Tests for M6A competitor detection analysis with 3-tier matching."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.competitor_detect import analyze_competitor_detection
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(output_dir="/tmp/test")


def _make_df(merchants: list[str], amounts: list[float] | None = None) -> pd.DataFrame:
    n = len(merchants)
    if amounts is None:
        amounts = [100.0] * n
    return pd.DataFrame(
        {
            "merchant_name": merchants,
            "amount": amounts,
            "primary_account_num": [f"ACCT{i}" for i in range(n)],
            "business_flag": ["No"] * n,
        }
    )


class TestCompetitorDetection:
    def test_detects_exact_match(self):
        df = _make_df(["CHASE", "WALMART", "TARGET"])
        ctx: dict = {}
        result = analyze_competitor_detection(df, df, df, _settings(), ctx)
        assert result.error is None
        assert len(ctx["competitor_data"]) == 1

    def test_detects_starts_with_match(self):
        df = _make_df(["BANK OF AMERICA NA", "COSTCO"])
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        assert len(ctx["competitor_data"]) == 1

    def test_detects_contains_match(self):
        df = _make_df(["PURCHASE AT SYNCHRONY STORE", "GROCERY STORE"])
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        assert len(ctx["competitor_data"]) == 1

    def test_false_positive_excluded(self):
        df = _make_df(["CHASE OUTDOORS LLC", "CHASE BANK NA"])
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        # CHASE OUTDOORS should be excluded by false positive filter
        all_merchants = set()
        for comp_df in ctx["competitor_data"].values():
            all_merchants.update(comp_df["merchant_name"].str.upper())
        assert "CHASE OUTDOORS LLC" not in all_merchants
        assert len(ctx["competitor_data"]) >= 1

    def test_no_competitors_returns_empty(self):
        df = _make_df(["WALMART", "TARGET", "COSTCO"])
        ctx: dict = {}
        result = analyze_competitor_detection(df, df, df, _settings(), ctx)
        assert result.error is None
        assert ctx["competitor_summary"].empty
        assert ctx["competitor_data"] == {}

    def test_summary_has_expected_columns(self):
        df = _make_df(["CHASE BANK NA", "ALLY BANK DEPOSIT"])
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        summary = ctx["competitor_summary"]
        expected = {
            "competitor",
            "category",
            "match_tier",
            "total_transactions",
            "unique_accounts",
            "total_amount",
        }
        assert expected.issubset(set(summary.columns))

    def test_summary_sorted_by_amount_descending(self):
        df = _make_df(
            ["CHASE BANK NA", "ALLY BANK DEPOSIT", "VENMO PAYMENT"],
            [500.0, 200.0, 1000.0],
        )
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        summary = ctx["competitor_summary"]
        amounts = summary["total_amount"].tolist()
        assert amounts == sorted(amounts, reverse=True)

    def test_context_none_is_safe(self):
        df = _make_df(["CHASE"])
        result = analyze_competitor_detection(df, df, df, _settings(), None)
        assert result.error is None

    def test_uses_merchant_consolidated_when_available(self):
        df = _make_df(["ORIGINAL NAME"])
        df["merchant_consolidated"] = ["CHASE BANK NA"]
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        assert len(ctx["competitor_data"]) >= 1

    def test_match_tier_in_context_data(self):
        df = _make_df(["CHASE", "BANK OF AMERICA NA"])
        ctx: dict = {}
        analyze_competitor_detection(df, df, df, _settings(), ctx)
        for comp_df in ctx["competitor_data"].values():
            assert "match_tier" in comp_df.columns
