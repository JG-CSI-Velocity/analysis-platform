"""Tests for ars.pipeline.steps.format -- ODD formatting pipeline."""

import pandas as pd
import pytest

from ars_analysis.pipeline.steps.format import (
    FormatResult,
    _swipe_category,
    format_odd,
)


class TestSwipeCategory:
    @pytest.mark.parametrize("swipes,expected", [
        (0, "Non-user"),
        (0.5, "Non-user"),
        (1, "1-5 Swipes"),
        (5, "1-5 Swipes"),
        (6, "6-10 Swipes"),
        (10, "6-10 Swipes"),
        (15, "11-15 Swipes"),
        (20, "16-20 Swipes"),
        (25, "21-25 Swipes"),
        (30, "26-40 Swipes"),
        (40, "26-40 Swipes"),
        (41, "41+ Swipes"),
        (100, "41+ Swipes"),
    ])
    def test_categories(self, swipes, expected):
        assert _swipe_category(swipes) == expected


class TestFormatOdd:
    @pytest.fixture
    def basic_df(self):
        """A minimal ODD DataFrame with PIN/Sig spend columns."""
        return pd.DataFrame({
            "Account": ["A001", "A002", "A003"],
            "Stat Code": ["O", "O", "C"],
            "01/26 PIN $": [100.0, 200.0, 0.0],
            "01/26 Sig $": [50.0, 100.0, 0.0],
            "01/26 PIN #": [5, 10, 0],
            "01/26 Sig #": [3, 6, 0],
            "PYTD Balance": [1000.0, 2000.0, 0.0],
            "YTD Deposits": [500.0, 700.0, 0.0],
        })

    def test_drops_pytd_ytd(self, basic_df):
        result = format_odd(basic_df)
        pytd_cols = [c for c in result.columns if "PYTD" in c or "YTD" in c]
        assert len(pytd_cols) == 0

    def test_creates_total_spend(self, basic_df):
        result = format_odd(basic_df)
        assert "Total Spend" in result.columns
        assert result["Total Spend"].iloc[0] == 150.0  # 100 + 50

    def test_creates_total_swipes(self, basic_df):
        result = format_odd(basic_df)
        assert "Total Swipes" in result.columns
        assert result["Total Swipes"].iloc[0] == 8  # 5 + 3

    def test_does_not_mutate_input(self, basic_df):
        original_cols = list(basic_df.columns)
        format_odd(basic_df)
        assert list(basic_df.columns) == original_cols

    def test_age_calculation(self):
        df = pd.DataFrame({
            "Account": ["A001"],
            "DOB": ["1990-06-15"],
            "Date Opened": ["2020-01-01"],
        })
        result = format_odd(df)
        assert "Account Holder Age" in result.columns
        assert result["Account Holder Age"].iloc[0] > 30

    def test_empty_dataframe(self):
        df = pd.DataFrame({"Col1": [], "Col2": []})
        result = format_odd(df)
        assert len(result) == 0

    def test_response_grouping(self):
        df = pd.DataFrame({
            "Account": ["A001", "A002", "A003"],
            "# of Offers": [3, 1, 0],
            "# of Responses": [2, 0, 0],
        })
        result = format_odd(df)
        assert "Response Grouping" in result.columns
        assert result["Response Grouping"].iloc[0] == "MR"
        assert result["Response Grouping"].iloc[1] == "Non-Responder"
        assert result["Response Grouping"].iloc[2] == "No Offer"


class TestFormatResult:
    def test_empty(self):
        r = FormatResult()
        assert r.total == 0

    def test_total(self):
        r = FormatResult(
            formatted=[("a", "b", "c")],
            errors=[("d", "e", "f")],
        )
        assert r.total == 2
