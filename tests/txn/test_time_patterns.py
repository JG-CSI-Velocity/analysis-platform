"""Tests for M16: Time-of-day / day-of-week patterns."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.time_patterns import analyze_time_patterns
from txn_analysis.settings import Settings


def _settings() -> Settings:
    return Settings(data_file=None, output_dir="/tmp/test")


def _make_df(dates: list[str], amounts: list[float] | None = None) -> pd.DataFrame:
    """Build synthetic txn DataFrame with given dates."""
    if amounts is None:
        amounts = [100.0] * len(dates)
    return pd.DataFrame({
        "transaction_date": dates,
        "amount": amounts,
        "primary_account_num": [f"ACCT{i:03d}" for i in range(len(dates))],
        "merchant_name": ["Test Merchant"] * len(dates),
        "business_flag": ["No"] * len(dates),
    })


class TestTimePatterns:
    def test_basic_dow_breakdown(self):
        # Mon through Sun (2025-07-14 is a Monday)
        dates = [
            "2025-07-14",  # Mon
            "2025-07-15",  # Tue
            "2025-07-16",  # Wed
            "2025-07-17",  # Thu
            "2025-07-18",  # Fri
            "2025-07-19",  # Sat
            "2025-07-20",  # Sun
        ]
        df = _make_df(dates)
        result = analyze_time_patterns(df, df, df, _settings())
        assert result.error is None
        assert len(result.df) == 7
        assert list(result.df["Day"]) == [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]

    def test_weekend_pct(self):
        # 2 weekend txns at $200, 5 weekday txns at $100
        dates = [
            "2025-07-14",  # Mon
            "2025-07-15",  # Tue
            "2025-07-16",  # Wed
            "2025-07-17",  # Thu
            "2025-07-18",  # Fri
            "2025-07-19",  # Sat
            "2025-07-20",  # Sun
        ]
        amounts = [100, 100, 100, 100, 100, 200, 200]
        df = _make_df(dates, amounts)
        result = analyze_time_patterns(df, df, df, _settings())
        # Weekend spend = 400, Total = 900
        expected_pct = round(400 / 900 * 100, 1)
        assert result.metadata["weekend_spend_pct"] == expected_pct

    def test_peak_day(self):
        # 3 Monday txns, 1 of every other day
        dates = ["2025-07-14", "2025-07-14", "2025-07-14", "2025-07-15", "2025-07-16"]
        df = _make_df(dates)
        result = analyze_time_patterns(df, df, df, _settings())
        assert result.metadata["peak_day"] == "Monday"

    def test_missing_column(self):
        df = pd.DataFrame({"amount": [10, 20]})
        result = analyze_time_patterns(df, df, df, _settings())
        assert result.error is not None

    def test_invalid_dates(self):
        df = _make_df(["not-a-date", "also-not", "nope"])
        result = analyze_time_patterns(df, df, df, _settings())
        assert result.error is not None

    def test_summary_populated(self):
        dates = ["2025-07-14", "2025-07-19"]
        df = _make_df(dates)
        result = analyze_time_patterns(df, df, df, _settings())
        assert "Peak day" in result.summary
        assert "Weekend" in result.summary

    def test_sheet_name(self):
        df = _make_df(["2025-07-14"])
        result = analyze_time_patterns(df, df, df, _settings())
        assert result.sheet_name == "M16 Time Patterns"

    def test_day_of_month_sheet(self):
        # Transactions across different parts of the month
        dates = [
            "2025-07-03",  # Early (Days 1-7)
            "2025-07-10",  # Mid-early (Days 8-14)
            "2025-07-18",  # Mid-late (Days 15-21)
            "2025-07-28",  # Late (Days 22-31)
        ]
        df = _make_df(dates)
        result = analyze_time_patterns(df, df, df, _settings())
        assert "day_of_month" in result.data
        dom = result.data["day_of_month"]
        assert len(dom) == 4
        assert list(dom["Period"]) == [
            "Days 1-7", "Days 8-14", "Days 15-21", "Days 22-31"
        ]

    def test_early_vs_late_month_avg_ticket(self):
        # Early month: small txns. Late month: large txns.
        dates = ["2025-07-02", "2025-07-03", "2025-07-25", "2025-07-28"]
        amounts = [10.0, 10.0, 200.0, 200.0]
        df = _make_df(dates, amounts)
        result = analyze_time_patterns(df, df, df, _settings())
        assert result.metadata["early_month_avg_ticket"] == 10.0
        assert result.metadata["late_month_avg_ticket"] == 200.0

    def test_summary_mentions_early_late(self):
        dates = ["2025-07-02", "2025-07-28"]
        amounts = [50.0, 150.0]
        df = _make_df(dates, amounts)
        result = analyze_time_patterns(df, df, df, _settings())
        assert "Early month" in result.summary or "early month" in result.summary
