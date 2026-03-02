"""Tests for M10: Member segmentation by spend tier."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.member_segments import analyze_member_segments
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test")


def _make_df() -> pd.DataFrame:
    """Create synthetic data with a mix of active and dormant accounts."""
    rows = []
    # Active high-spender (recent, high spend)
    for i in range(20):
        rows.append(
            {
                "primary_account_num": "ACCT001",
                "amount": 500.0,
                "transaction_date": f"2025-10-{(i % 28) + 1:02d}",
                "business_flag": "No",
            }
        )
    # Active mid-spender
    for i in range(10):
        rows.append(
            {
                "primary_account_num": "ACCT002",
                "amount": 50.0,
                "transaction_date": f"2025-10-{(i % 28) + 1:02d}",
                "business_flag": "No",
            }
        )
    # Active low-spender
    for i in range(5):
        rows.append(
            {
                "primary_account_num": "ACCT003",
                "amount": 10.0,
                "transaction_date": f"2025-10-{(i % 28) + 1:02d}",
                "business_flag": "No",
            }
        )
    # Dormant account (last txn >90 days ago relative to max date in dataset)
    rows.append(
        {
            "primary_account_num": "ACCT004",
            "amount": 25.0,
            "transaction_date": "2025-06-01",
            "business_flag": "No",
        }
    )
    return pd.DataFrame(rows)


class TestMemberSegments:
    def test_basic_result(self):
        df = _make_df()
        result = analyze_member_segments(df, df, df, _settings())
        assert result.error is None
        assert not result.df.empty

    def test_segment_names(self):
        df = _make_df()
        result = analyze_member_segments(df, df, df, _settings())
        segments = set(result.df["segment"])
        assert segments <= {"High Value", "Active", "Low Activity", "Dormant"}

    def test_dormant_detected(self):
        df = _make_df()
        result = analyze_member_segments(df, df, df, _settings())
        dormant = result.df[result.df["segment"] == "Dormant"]
        assert len(dormant) > 0
        assert dormant.iloc[0]["account_count"] >= 1

    def test_context_populated(self):
        df = _make_df()
        ctx: dict = {}
        analyze_member_segments(df, df, df, _settings(), context=ctx)
        assert "member_segments" in ctx
        assert ctx["member_segments"]["total_accounts"] == 4
        assert ctx["member_segments"]["dormant_count"] >= 1

    def test_empty_df(self):
        empty = pd.DataFrame()
        result = analyze_member_segments(empty, empty, empty, _settings())
        assert result.df.empty

    def test_columns_present(self):
        df = _make_df()
        result = analyze_member_segments(df, df, df, _settings())
        expected_cols = {"segment", "account_count", "total_spend", "avg_spend", "pct_of_accounts"}
        assert expected_cols <= set(result.df.columns)

    def test_pct_of_accounts_sums_to_100(self):
        df = _make_df()
        result = analyze_member_segments(df, df, df, _settings())
        total_pct = result.df["pct_of_accounts"].sum()
        assert abs(total_pct - 100.0) < 0.5

    def test_segment_order(self):
        df = _make_df()
        result = analyze_member_segments(df, df, df, _settings())
        expected_order = ["High Value", "Active", "Low Activity", "Dormant"]
        actual = result.df["segment"].tolist()
        # Should be in the canonical order (only present segments)
        filtered_expected = [s for s in expected_order if s in actual]
        assert actual == filtered_expected
