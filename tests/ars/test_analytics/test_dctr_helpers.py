"""Tests for DCTR shared helpers -- pure functions, no side effects."""

from datetime import date

import pandas as pd
import pytest

from ars_analysis.analytics.dctr._helpers import (
    analyze_historical_dctr,
    branch_dctr,
    categorize_account_age,
    categorize_balance,
    categorize_holder_age,
    dctr,
    filter_l12m,
    l12m_month_labels,
    l12m_monthly,
    map_to_decade,
    simplify_account_age,
    total_row,
)


class TestDctrCalculation:
    def test_basic_dctr(self):
        df = pd.DataFrame({"Debit?": ["Yes", "Yes", "No", "No", "No"]})
        t, w, rate = dctr(df)
        assert t == 5
        assert w == 2
        assert rate == pytest.approx(0.4)

    def test_empty_df(self):
        df = pd.DataFrame({"Debit?": []})
        t, w, rate = dctr(df)
        assert t == 0
        assert w == 0
        assert rate == 0.0

    def test_all_debit(self):
        df = pd.DataFrame({"Debit?": ["Yes", "Yes", "Yes"]})
        t, w, rate = dctr(df)
        assert rate == 1.0

    def test_no_debit(self):
        df = pd.DataFrame({"Debit?": ["No", "No"]})
        t, w, rate = dctr(df)
        assert rate == 0.0


class TestTotalRow:
    def test_appends_total(self):
        df = pd.DataFrame({
            "Branch": ["A", "B"],
            "Total Accounts": [10, 20],
            "With Debit": [5, 8],
            "DCTR %": [0.5, 0.4],
        })
        result = total_row(df, "Branch")
        assert len(result) == 3
        assert result.iloc[-1]["Branch"] == "TOTAL"
        assert result.iloc[-1]["Total Accounts"] == 30
        assert result.iloc[-1]["With Debit"] == 13

    def test_empty_df_returns_empty(self):
        df = pd.DataFrame()
        result = total_row(df, "Branch")
        assert result.empty


class TestCategorizeAccountAge:
    @pytest.mark.parametrize("days, expected", [
        (30, "0-6 months"),
        (200, "6-12 months"),
        (500, "1-2 years"),
        (1000, "2-5 years"),
        (2000, "5-10 years"),
        (5000, "10+ years"),
    ])
    def test_buckets(self, days, expected):
        assert categorize_account_age(days) == expected

    def test_nan(self):
        assert categorize_account_age(float("nan")) == "Unknown"


class TestCategorizeHolderAge:
    @pytest.mark.parametrize("age, expected", [
        (20, "18-24"),
        (30, "25-34"),
        (40, "35-44"),
        (50, "45-54"),
        (60, "55-64"),
        (70, "65+"),
    ])
    def test_buckets(self, age, expected):
        assert categorize_holder_age(age) == expected

    def test_nan(self):
        assert categorize_holder_age(float("nan")) == "Unknown"


class TestCategorizeBalance:
    @pytest.mark.parametrize("bal, expected", [
        (-100, "Negative"),
        (250, "$0-$499"),
        (750, "$500-$999"),
        (1500, "$1K-$2.5K"),
        (3000, "$2.5K-$5K"),
        (7500, "$5K-$10K"),
        (15000, "$10K-$25K"),
        (30000, "$25K-$50K"),
        (75000, "$50K-$100K"),
        (200000, "$100K+"),
    ])
    def test_buckets(self, bal, expected):
        assert categorize_balance(bal) == expected


class TestSimplifyAccountAge:
    def test_new(self):
        assert simplify_account_age("0-6 months") == "New (0-1 year)"
        assert simplify_account_age("6-12 months") == "New (0-1 year)"

    def test_recent(self):
        assert simplify_account_age("1-2 years") == "Recent (1-5 years)"
        assert simplify_account_age("2-5 years") == "Recent (1-5 years)"

    def test_mature(self):
        assert simplify_account_age("5-10 years") == "Mature (5+ years)"
        assert simplify_account_age("10+ years") == "Mature (5+ years)"


class TestMapToDecade:
    def test_recent_year(self):
        assert map_to_decade(2024) == "2024"

    def test_old_decade(self):
        assert map_to_decade(1985) == "1980s"

    def test_before_1970(self):
        assert map_to_decade(1960) == "Before 1970"

    def test_nan(self):
        assert map_to_decade(float("nan")) is None


class TestL12mMonthLabels:
    def test_produces_12_labels(self):
        labels = l12m_month_labels(date(2024, 2, 28))
        assert len(labels) == 12
        assert labels[0] == "Mar23"
        assert labels[-1] == "Feb24"


class TestFilterL12m:
    def test_filters_to_date_range(self):
        df = pd.DataFrame({
            "Date Opened": pd.to_datetime(["2023-06-15", "2024-01-15", "2024-06-15"]),
        })
        result = filter_l12m(df, date(2023, 3, 1), date(2024, 2, 28))
        assert len(result) == 2

    def test_empty_input(self):
        result = filter_l12m(pd.DataFrame(), date(2023, 1, 1), date(2024, 1, 1))
        assert result.empty


class TestAnalyzeHistoricalDctr:
    def test_returns_yearly_and_decade(self, dctr_eligible_df):
        yearly, decade, ins = analyze_historical_dctr(dctr_eligible_df)
        assert not yearly.empty
        assert ins["total_accounts"] > 0
        assert 0 <= ins["overall_dctr"] <= 1

    def test_empty_df(self):
        yearly, decade, ins = analyze_historical_dctr(pd.DataFrame())
        assert yearly.empty
        assert ins["total_accounts"] == 0


class TestL12mMonthly:
    def test_returns_monthly_table(self, dctr_eligible_df):
        months = l12m_month_labels(date(2024, 2, 28))
        # Filter to L12M first
        df = dctr_eligible_df.copy()
        df["Date Opened"] = pd.to_datetime(df["Date Opened"])
        monthly, ins = l12m_monthly(df, months)
        # May or may not have data depending on fixture dates, but should not error
        assert isinstance(monthly, pd.DataFrame)
        assert isinstance(ins, dict)


class TestBranchDctr:
    def test_returns_branch_breakdown(self, dctr_eligible_df):
        df = dctr_eligible_df[dctr_eligible_df["Stat Code"] == "O"]
        bdf, ins = branch_dctr(df)
        assert not bdf.empty
        assert "best_branch" in ins
        assert "worst_branch" in ins

    def test_empty_df(self):
        bdf, ins = branch_dctr(pd.DataFrame())
        assert bdf.empty
        assert ins == {}
