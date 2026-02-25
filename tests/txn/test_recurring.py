"""Tests for M15: Recurring payment detection and onset tracking."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.recurring import (
    _build_onset_timeline,
    _summarize_onsets_by_month,
    analyze_recurring_payments,
)
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
                rows.append(
                    {
                        "merchant_consolidated": merchant,
                        "merchant_name": merchant,
                        "primary_account_num": acct,
                        "amount": 15.99,
                        "year_month": month,
                        "transaction_date": f"{month}-15",
                        "business_flag": "No",
                    }
                )
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
            rows.append(
                {
                    "merchant_consolidated": "NETFLIX.COM",
                    "merchant_name": "NETFLIX.COM",
                    "primary_account_num": "1001",
                    "amount": 15.99,
                    "year_month": m,
                    "transaction_date": f"{m}-15",
                    "business_flag": "No",
                }
            )
        rows.append(
            {
                "merchant_consolidated": "NETFLIX.COM",
                "merchant_name": "NETFLIX.COM",
                "primary_account_num": "1002",
                "amount": 15.99,
                "year_month": "2025-01",
                "transaction_date": "2025-01-15",
                "business_flag": "No",
            }
        )
        df = pd.DataFrame(rows)
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.error is None
        # Only 1 account (1001) qualifies as recurring
        assert result.metadata["recurring_accounts"] == 1

    def test_sheet_name(self):
        df = _make_df(["X"], ["1001"], ["2025-01", "2025-02", "2025-03"])
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.sheet_name == "M15 Recurring"


class TestOnsetTimeline:
    def test_onset_month_is_third_month(self):
        """Onset happens in the 3rd month (when threshold is crossed)."""
        df = _make_df(
            merchants=["NETFLIX.COM"],
            accounts=["1001"],
            months=["2025-01", "2025-02", "2025-03", "2025-04"],
        )
        onsets = _build_onset_timeline(df, min_months=3)
        assert len(onsets) == 1
        assert onsets.iloc[0]["onset_month"] == "2025-03"
        assert onsets.iloc[0]["merchant_consolidated"] == "NETFLIX.COM"

    def test_no_onset_below_threshold(self):
        df = _make_df(
            merchants=["HULU"],
            accounts=["1001"],
            months=["2025-01", "2025-02"],
        )
        onsets = _build_onset_timeline(df, min_months=3)
        assert onsets.empty

    def test_multiple_accounts_different_onset_months(self):
        """Two accounts start recurring at different times."""
        rows = []
        # Account 1001: Netflix from Jan-Mar (onset = Mar)
        for m in ["2025-01", "2025-02", "2025-03"]:
            rows.append(
                {
                    "merchant_consolidated": "NETFLIX.COM",
                    "primary_account_num": "1001",
                    "amount": 15.99,
                    "year_month": m,
                    "transaction_date": f"{m}-15",
                    "business_flag": "No",
                }
            )
        # Account 1002: Netflix from Feb-Apr (onset = Apr)
        for m in ["2025-02", "2025-03", "2025-04"]:
            rows.append(
                {
                    "merchant_consolidated": "NETFLIX.COM",
                    "primary_account_num": "1002",
                    "amount": 15.99,
                    "year_month": m,
                    "transaction_date": f"{m}-15",
                    "business_flag": "No",
                }
            )
        df = pd.DataFrame(rows)
        onsets = _build_onset_timeline(df, min_months=3)
        assert len(onsets) == 2
        assert set(onsets["onset_month"]) == {"2025-03", "2025-04"}

    def test_multiple_merchants_per_account(self):
        """One account can have onsets for different merchants."""
        rows = []
        for merchant in ["NETFLIX.COM", "SPOTIFY"]:
            for m in ["2025-01", "2025-02", "2025-03"]:
                rows.append(
                    {
                        "merchant_consolidated": merchant,
                        "primary_account_num": "1001",
                        "amount": 15.99,
                        "year_month": m,
                        "transaction_date": f"{m}-15",
                        "business_flag": "No",
                    }
                )
        df = pd.DataFrame(rows)
        onsets = _build_onset_timeline(df, min_months=3)
        assert len(onsets) == 2
        assert set(onsets["merchant_consolidated"]) == {"NETFLIX.COM", "SPOTIFY"}


class TestOnsetSummaryByMonth:
    def test_aggregates_by_month(self):
        df = _make_df(
            merchants=["NETFLIX.COM", "SPOTIFY"],
            accounts=["1001", "1002"],
            months=["2025-01", "2025-02", "2025-03"],
        )
        onsets = _build_onset_timeline(df, min_months=3)
        summary = _summarize_onsets_by_month(onsets, df)
        # All onsets happen in 2025-03 (the 3rd month)
        assert len(summary) == 1
        assert summary.iloc[0]["Month"] == "2025-03"
        # 2 accounts x 2 merchants = 4 relationships
        assert summary.iloc[0]["New Recurring Relationships"] == 4
        assert summary.iloc[0]["New Recurring Accounts"] == 2

    def test_empty_onsets(self):
        df = _make_df(["HULU"], ["1001"], ["2025-01", "2025-02"])
        onsets = _build_onset_timeline(df, min_months=3)
        summary = _summarize_onsets_by_month(onsets, df)
        assert summary.empty

    def test_staggered_onsets_across_months(self):
        """Onsets in different months should produce separate rows."""
        rows = []
        # 1001+Netflix: Jan-Mar (onset Mar)
        for m in ["2025-01", "2025-02", "2025-03"]:
            rows.append(
                {
                    "merchant_consolidated": "NETFLIX.COM",
                    "primary_account_num": "1001",
                    "amount": 15.99,
                    "year_month": m,
                    "transaction_date": f"{m}-15",
                    "business_flag": "No",
                }
            )
        # 1002+Spotify: Feb-Apr (onset Apr)
        for m in ["2025-02", "2025-03", "2025-04"]:
            rows.append(
                {
                    "merchant_consolidated": "SPOTIFY",
                    "primary_account_num": "1002",
                    "amount": 9.99,
                    "year_month": m,
                    "transaction_date": f"{m}-15",
                    "business_flag": "No",
                }
            )
        df = pd.DataFrame(rows)
        onsets = _build_onset_timeline(df, min_months=3)
        summary = _summarize_onsets_by_month(onsets, df)
        assert len(summary) == 2
        months = summary["Month"].tolist()
        assert "2025-03" in months
        assert "2025-04" in months

    def test_spend_at_onset(self):
        """Spend at onset should reflect the transactions in the onset month."""
        df = _make_df(
            merchants=["NETFLIX.COM"],
            accounts=["1001"],
            months=["2025-01", "2025-02", "2025-03"],
        )
        onsets = _build_onset_timeline(df, min_months=3)
        summary = _summarize_onsets_by_month(onsets, df)
        assert summary.iloc[0]["Spend at Onset"] == 15.99


class TestRecurringWithOnsets:
    def test_onsets_sheet_present(self):
        df = _make_df(
            merchants=["NETFLIX.COM"],
            accounts=["1001"],
            months=["2025-01", "2025-02", "2025-03", "2025-04"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert "onsets" in result.data
        assert not result.data["onsets"].empty

    def test_onset_metadata(self):
        df = _make_df(
            merchants=["NETFLIX.COM", "SPOTIFY"],
            accounts=["1001"],
            months=["2025-01", "2025-02", "2025-03"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert result.metadata["onset_count"] == 2

    def test_summary_mentions_latest_onset(self):
        df = _make_df(
            merchants=["NETFLIX.COM"],
            accounts=["1001"],
            months=["2025-01", "2025-02", "2025-03"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert "new recurring" in result.summary.lower()
        assert "2025-03" in result.summary

    def test_context_populated(self):
        df = _make_df(
            merchants=["NETFLIX.COM"],
            accounts=["1001", "1002"],
            months=["2025-01", "2025-02", "2025-03"],
        )
        ctx: dict = {"completed_results": {}}
        result = analyze_recurring_payments(df, df, df, _settings(), context=ctx)
        assert "recurring_onsets" in ctx
        assert ctx["recurring_onsets"]["total_recurring_accounts"] == 2
        assert ctx["recurring_onsets"]["total_recurring_pct"] > 0

    def test_no_onsets_when_no_recurring(self):
        df = _make_df(
            merchants=["HULU"],
            accounts=["1001"],
            months=["2025-01", "2025-02"],
        )
        result = analyze_recurring_payments(df, df, df, _settings())
        assert "onsets" not in result.data
