"""Tests for Reg E helper functions."""

import pandas as pd
import pytest

from ars_analysis.analytics.rege._helpers import (
    ACCT_AGE_ORDER,
    HOLDER_AGE_ORDER,
    categorize_account_age,
    categorize_holder_age,
    detect_reg_e_column,
    reg_e_base,
    rege,
    total_row,
)


class TestRegeCalc:
    """Core rege() calculation."""

    def test_basic(self):
        df = pd.DataFrame({"col": ["Y", "N", "Y", "N", "Y"]})
        t, oi, r = rege(df, "col", ["Y"])
        assert t == 5
        assert oi == 3
        assert r == pytest.approx(0.6)

    def test_empty_df(self):
        df = pd.DataFrame({"col": pd.Series([], dtype=str)})
        t, oi, r = rege(df, "col", ["Y"])
        assert (t, oi, r) == (0, 0, 0.0)

    def test_no_matches(self):
        df = pd.DataFrame({"col": ["N", "N", "N"]})
        t, oi, r = rege(df, "col", ["Y"])
        assert t == 3
        assert oi == 0
        assert r == 0.0

    def test_all_match(self):
        df = pd.DataFrame({"col": ["Y", "Y", "Y"]})
        t, oi, r = rege(df, "col", ["Y"])
        assert r == pytest.approx(1.0)


class TestDetectRegEColumn:
    """Auto-detect 'Reg E Code ...' column."""

    def test_finds_latest(self):
        df = pd.DataFrame({
            "Reg E Code 2023.01": [1], "Reg E Code 2024.02": [2], "Other": [3],
        })
        assert detect_reg_e_column(df) == "Reg E Code 2024.02"

    def test_single_col(self):
        df = pd.DataFrame({"Reg E Code 2024.02": [1]})
        assert detect_reg_e_column(df) == "Reg E Code 2024.02"

    def test_no_match(self):
        df = pd.DataFrame({"Other": [1]})
        assert detect_reg_e_column(df) is None


class TestRegEBase:
    """reg_e_base() returns correct base data."""

    def test_returns_base(self, rege_ctx):
        base, base_l12m, col, opts = reg_e_base(rege_ctx)
        assert len(base) > 0
        assert col == "Reg E Code 2024.02"
        assert opts == ["Y"]
        # base should be personal with debit
        assert all(base["Debit?"] == "Yes")
        assert all(base["Business?"] == "No")

    def test_missing_opt_in(self, rege_ctx):
        rege_ctx.client.reg_e_opt_in = []
        with pytest.raises(ValueError, match="No Reg E opt-in codes"):
            reg_e_base(rege_ctx)

    def test_missing_column(self, rege_ctx):
        rege_ctx.client.reg_e_column = "Nonexistent"
        with pytest.raises(ValueError, match="not in data"):
            reg_e_base(rege_ctx)


class TestTotalRow:
    """total_row() appends a TOTAL row."""

    def test_adds_total(self):
        df = pd.DataFrame({
            "Label": ["A", "B"],
            "Total Accounts": [10, 20],
            "Opted In": [3, 8],
            "Opt-In Rate": [0.3, 0.4],
        })
        result = total_row(df, "Label")
        assert len(result) == 3
        tot = result[result["Label"] == "TOTAL"]
        assert tot["Total Accounts"].iloc[0] == 30
        assert tot["Opted In"].iloc[0] == 11
        assert tot["Opt-In Rate"].iloc[0] == pytest.approx(11 / 30)

    def test_empty_df(self):
        df = pd.DataFrame()
        assert total_row(df, "Label").empty


class TestCategorizeAccountAge:
    """7-bucket account age categorization."""

    @pytest.mark.parametrize("days, expected", [
        (90, "0-6 months"),
        (200, "6-12 months"),
        (500, "1-2 years"),
        (1000, "2-5 years"),
        (3000, "5-10 years"),
        (5000, "10-20 years"),
        (8000, "20+ years"),
    ])
    def test_buckets(self, days, expected):
        assert categorize_account_age(days) == expected

    def test_nan(self):
        assert categorize_account_age(float("nan")) == "Unknown"

    def test_order_count(self):
        assert len(ACCT_AGE_ORDER) == 7


class TestCategorizeHolderAge:
    """7-bucket holder age categorization."""

    @pytest.mark.parametrize("age, expected", [
        (20, "18-24"),
        (30, "25-34"),
        (40, "35-44"),
        (50, "45-54"),
        (60, "55-64"),
        (70, "65-74"),
        (80, "75+"),
    ])
    def test_buckets(self, age, expected):
        assert categorize_holder_age(age) == expected

    def test_nan(self):
        assert categorize_holder_age(float("nan")) == "Unknown"

    def test_order_count(self):
        assert len(HOLDER_AGE_ORDER) == 7
