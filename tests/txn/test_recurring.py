"""Tests for M15: Recurring payment detection."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.recurring import analyze_recurring_payments
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test")


def _make_df(
    merchants: list[str],
    accounts: list[str],
    months: list[str],
) -> pd.DataFrame:
    """Build synthetic txn DataFrame with all combos of merchants x accounts x months."""
    rows = []
    for acct in accounts:
        for merchant in merchants:
            for month in months:
                rows.append({
                    "merchant_consolidated": merchant,
                    "merchant_name": merchant,
                    "primary_account_num": acct,
                    "amount": 15.99,
                    "year_month": month,
                    "transaction_date": f"{month}-15",
                    "business_flag": "No",
                })
    return pd.DataFrame(rows)


class TestRecurringPayments:
    def test_detects_recurring(self):
        df = _make_df(
            merchants=["NETFLIX.COM", "SPOTIFY"],
            accounts=["1001", "1002"],
            months=["2025-01", "2025-02", "2025-03", "2025-04"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.error is None
        assert len(result.df) == 2
        assert result.metadata["recurring_accounts"] == 2
        assert "NETFLIX.COM" in result.df["Merchant"].values

    def test_no_recurring_below_threshold(self):
        # Only 2 months -- below the 3-month minimum
        df = _make_df(
            merchants=["HULU"],
            accounts=["1001"],
            months=["2025-01", "2025-02"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.error is None
        assert "No recurring" in result.df.iloc[0]["Note"]

    def test_missing_columns(self):
        df = pd.DataFrame({"amount": [10, 20]})
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.error is not None

    def test_summary_populated(self):
        df = _make_df(
            merchants=["AMAZON PRIME"],
            accounts=["1001", "1002", "1003"],
            months=["2025-01", "2025-02", "2025-03"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert "3 accounts" in result.summary
        assert result.metadata["recurring_pct"] > 0

    def test_mixed_recurring_and_not(self):
        # 1001 has Netflix for 4 months (recurring), 1002 has it for 1 month (not)
        rows = []
        for m in ["2025-01", "2025-02", "2025-03", "2025-04"]:
            rows.append({
                "merchant_consolidated": "NETFLIX.COM",
                "merchant_name": "NETFLIX.COM",
                "primary_account_num": "1001",
                "amount": 15.99,
                "year_month": m,
                "transaction_date": f"{m}-15",
                "business_flag": "No",
            })
        rows.append({
            "merchant_consolidated": "NETFLIX.COM",
            "merchant_name": "NETFLIX.COM",
            "primary_account_num": "1002",
            "amount": 15.99,
            "year_month": "2025-01",
            "transaction_date": "2025-01-15",
            "business_flag": "No",
        })
        df = pd.DataFrame(rows)
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.error is None
        # Only 1 account (1001) qualifies as recurring
        assert result.metadata["recurring_accounts"] == 1

    def test_sheet_name(self):
        df = _make_df(["X"], ["1001"], ["2025-01", "2025-02", "2025-03"])
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.sheet_name == "M15 Recurring"
