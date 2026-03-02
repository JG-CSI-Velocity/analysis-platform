"""Tests for M26: Merchant loyalty metrics."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.merchant_loyalty import (
    _compute_hhi,
    _compute_repeat_rate,
    analyze_merchant_loyalty,
)
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test")


def _make_df(
    accounts: list[str],
    merchants: list[str],
    amounts: list[float] | None = None,
    dates: list[str] | None = None,
) -> pd.DataFrame:
    n = len(accounts)
    data = {
        "primary_account_num": accounts,
        "merchant_consolidated": merchants,
        "amount": amounts or [100.0] * n,
        "business_flag": ["No"] * n,
    }
    if dates:
        data["transaction_date"] = dates
    return pd.DataFrame(data)


class TestComputeRepeatRate:
    def test_all_repeat(self):
        # Single merchant visited 5 times -> 100% repeat rate
        df = _make_df(["A"] * 5, ["Walmart"] * 5)
        assert _compute_repeat_rate(df) == 100.0

    def test_no_repeats(self):
        # 2 merchants visited once each -> 0% (threshold is 3)
        df = _make_df(["A"] * 2, ["Walmart", "Target"])
        assert _compute_repeat_rate(df) == 0.0

    def test_mixed(self):
        # 2 merchants: one visited 4x (repeat), one visited 1x (not)
        df = _make_df(
            ["A"] * 5,
            ["Walmart", "Walmart", "Walmart", "Walmart", "Target"],
        )
        # 1 of 2 merchants = 50%
        assert _compute_repeat_rate(df) == 50.0

    def test_empty(self):
        df = pd.DataFrame({"merchant_consolidated": pd.Series([], dtype=str)})
        assert _compute_repeat_rate(df) == 0.0


class TestComputeHHI:
    def test_single_merchant(self):
        # All spend at one merchant -> HHI = 1.0
        df = _make_df(["A"] * 3, ["Walmart"] * 3, [100, 200, 300])
        assert _compute_hhi(df) == 1.0

    def test_equal_split(self):
        # Equal spend at 4 merchants -> HHI = 4 * (0.25^2) = 0.25
        df = _make_df(
            ["A"] * 4,
            ["W", "T", "C", "K"],
            [100, 100, 100, 100],
        )
        assert _compute_hhi(df) == 0.25

    def test_empty(self):
        df = pd.DataFrame(columns=["merchant_consolidated", "amount"])
        assert _compute_hhi(df) == 0.0

    def test_zero_spend(self):
        df = _make_df(["A"] * 2, ["W", "T"], [0, 0])
        assert _compute_hhi(df) == 0.0


class TestAnalyzeMerchantLoyalty:
    def test_basic_result(self):
        df = _make_df(
            ["A", "A", "A", "A", "B", "B"],
            ["W", "W", "W", "T", "W", "T"],
            [100, 100, 100, 50, 200, 100],
        )
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert result.error is None
        assert "main" in result.data
        assert "account_detail" in result.data

    def test_account_detail(self):
        df = _make_df(
            ["A", "A", "A", "B", "B"],
            ["W", "W", "W", "T", "T"],
        )
        result = analyze_merchant_loyalty(df, df, df, _settings())
        detail = result.data["account_detail"]
        assert len(detail) == 2
        assert set(detail["Account"]) == {"A", "B"}

    def test_summary_populated(self):
        df = _make_df(["A"] * 5, ["W"] * 3 + ["T"] * 2)
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert "repeat rate" in result.summary.lower()
        assert "HHI" in result.summary

    def test_metadata_keys(self):
        df = _make_df(["A"] * 3, ["W"] * 3)
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert result.metadata["sheet_name"] == "M26 Merchant Loyalty"
        assert "avg_repeat_rate" in result.metadata
        assert "avg_hhi" in result.metadata

    def test_new_merchants_sheet(self):
        df = _make_df(
            ["A", "A", "A"],
            ["W", "T", "C"],
            dates=["2025-01-15", "2025-02-15", "2025-03-15"],
        )
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert "new_merchants" in result.data
        nm = result.data["new_merchants"]
        assert len(nm) == 3  # 3 months, each with 1 new merchant

    def test_no_merchant_col(self):
        df = pd.DataFrame({"amount": [100], "primary_account_num": ["A"]})
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert result.error is not None

    def test_empty_df(self):
        df = pd.DataFrame()
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert result.error is not None

    def test_merchant_name_fallback(self):
        """Use merchant_name if merchant_consolidated missing."""
        df = pd.DataFrame(
            {
                "primary_account_num": ["A", "A", "A"],
                "merchant_name": ["W", "W", "W"],
                "amount": [100, 200, 300],
                "business_flag": ["No"] * 3,
            }
        )
        result = analyze_merchant_loyalty(df, df, df, _settings())
        assert result.error is None

    def test_segment_breakdown_with_odd(self):
        df = _make_df(
            ["A1", "A1", "A2", "A2"],
            ["W", "W", "T", "T"],
            [100, 100, 200, 200],
        )
        odd = pd.DataFrame(
            {
                "Acct Number": ["A1", "A2"],
                "Date Opened": ["2024-01-01", "2024-01-01"],
                "Nov25 Segmentation": ["Responder", "Non-Responder"],
            }
        )
        ctx = {"odd_df": odd}
        result = analyze_merchant_loyalty(df, df, df, _settings(), context=ctx)
        assert "by_segment" in result.data
        seg = result.data["by_segment"]
        assert set(seg["Segment"]) == {"Responder", "Non-Responder"}
