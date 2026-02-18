"""Tests for key functions in ars_analysis.dctr."""

import pandas as pd
import pytest

from ars_analysis.dctr import (
    AGE_ORDER,
    BALANCE_ORDER,
    HOLDER_AGE_ORDER,
    _dctr,
    analyze_historical_dctr,
    categorize_account_age,
    categorize_balance,
    categorize_holder_age,
    map_to_decade,
)


class TestDctr:
    def test_basic_rate(self):
        df = pd.DataFrame({"Debit?": ["Yes", "Yes", "No", "No"]})
        total, with_debit, rate = _dctr(df)
        assert total == 4
        assert with_debit == 2
        assert rate == pytest.approx(0.5)  # returns fraction, not percentage

    def test_all_debit(self):
        df = pd.DataFrame({"Debit?": ["Yes", "Yes", "Yes"]})
        total, with_debit, rate = _dctr(df)
        assert rate == pytest.approx(1.0)

    def test_empty_df(self):
        df = pd.DataFrame({"Debit?": []})
        total, with_debit, rate = _dctr(df)
        assert total == 0
        assert rate == 0


class TestCategorizeAccountAge:
    def test_new_account(self):
        assert categorize_account_age(90) in AGE_ORDER

    def test_old_account(self):
        result = categorize_account_age(5000)
        assert result in AGE_ORDER

    def test_zero_days(self):
        result = categorize_account_age(0)
        assert result in AGE_ORDER


class TestCategorizeHolderAge:
    def test_young(self):
        assert categorize_holder_age(20) in HOLDER_AGE_ORDER

    def test_middle(self):
        assert categorize_holder_age(40) in HOLDER_AGE_ORDER

    def test_senior(self):
        assert categorize_holder_age(70) in HOLDER_AGE_ORDER


class TestCategorizeBalance:
    def test_negative(self):
        result = categorize_balance(-100)
        assert result in BALANCE_ORDER

    def test_zero(self):
        result = categorize_balance(0)
        assert result in BALANCE_ORDER

    def test_high_balance(self):
        result = categorize_balance(200000)
        assert result in BALANCE_ORDER


class TestMapToDecade:
    def test_2020s(self):
        # Recent years get individual year strings, not decade
        assert map_to_decade(2023) == "2023"

    def test_1990s(self):
        assert map_to_decade(1995) == "1990s"

    def test_old(self):
        result = map_to_decade(1960)
        assert "Before" in result or "1960" in result


class TestAnalyzeHistoricalDctr:
    def test_basic_analysis(self):
        df = pd.DataFrame(
            {
                "Debit?": ["Yes", "No", "Yes", "No"],
                "Business?": ["No", "No", "Yes", "No"],
                "Date Opened": pd.to_datetime(
                    ["2020-01-01", "2020-06-01", "2019-03-15", "2018-12-01"]
                ),
            }
        )
        yearly, decade, metrics = analyze_historical_dctr(df)
        assert "overall_dctr" in metrics
        # overall_dctr is a fraction (0-1) not percentage
        assert metrics["overall_dctr"] == pytest.approx(0.5)
        assert not yearly.empty
