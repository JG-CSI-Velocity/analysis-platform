"""Tests for utils.py -- filters, enrichment, helpers."""

from datetime import datetime

import pandas as pd

from ics_toolkit.analysis.utils import (
    add_account_age,
    add_age_range,
    add_balance_tier,
    add_l12m_activity,
    add_opening_month,
    generate_last_12_months,
    get_ics_accounts,
    get_ics_stat_o,
    get_ics_stat_o_debit,
    get_open_accounts,
)
from tests.ics.analysis.conftest import L12M_TAGS


class TestFilters:
    def test_get_ics_accounts(self, sample_df):
        result = get_ics_accounts(sample_df)
        assert all(result["ICS Account"] == "Yes")
        assert len(result) < len(sample_df)
        assert len(result) > 0

    def test_get_ics_stat_o(self, sample_df):
        result = get_ics_stat_o(sample_df)
        assert all(result["ICS Account"] == "Yes")
        assert all(result["Stat Code"] == "O")

    def test_get_ics_stat_o_debit(self, sample_df):
        result = get_ics_stat_o_debit(sample_df)
        assert all(result["ICS Account"] == "Yes")
        assert all(result["Stat Code"] == "O")
        assert all(result["Debit?"] == "Yes")

    def test_get_open_accounts(self, sample_df):
        result = get_open_accounts(sample_df)
        assert all(result["Stat Code"] == "O")

    def test_get_ics_stat_o_custom_codes(self, sample_df):
        """open_codes=['A'] filters to Stat Code A instead of O."""
        # Overwrite some stat codes to 'A'
        df = sample_df.copy()
        df.loc[df["Stat Code"] == "O", "Stat Code"] = "A"
        result = get_ics_stat_o(df, open_codes=["A"])
        assert all(result["ICS Account"] == "Yes")
        assert all(result["Stat Code"] == "A")
        assert len(result) > 0

    def test_get_ics_stat_o_debit_custom_codes(self, sample_df):
        df = sample_df.copy()
        df.loc[df["Stat Code"] == "O", "Stat Code"] = "A"
        result = get_ics_stat_o_debit(df, open_codes=["A"])
        assert all(result["ICS Account"] == "Yes")
        assert all(result["Stat Code"] == "A")
        assert all(result["Debit?"] == "Yes")

    def test_get_open_accounts_custom_codes(self, sample_df):
        df = sample_df.copy()
        df.loc[df["Stat Code"] == "O", "Stat Code"] = "A"
        result = get_open_accounts(df, open_codes=["A"])
        assert all(result["Stat Code"] == "A")
        assert len(result) > 0

    def test_get_ics_stat_o_multiple_codes(self, sample_df):
        """Multiple open codes work (e.g. both O and A)."""
        result = get_ics_stat_o(sample_df, open_codes=["O", "A"])
        assert all(result["ICS Account"] == "Yes")
        assert all(result["Stat Code"].isin(["O", "A"]))

    def test_filters_return_copies(self, sample_df):
        result = get_ics_accounts(sample_df)
        result["ICS Account"] = "Modified"
        # Original should be unaffected
        assert "Modified" not in sample_df["ICS Account"].values


class TestEnrichment:
    def test_add_l12m_activity(self, sample_df):
        result = add_l12m_activity(sample_df.copy(), L12M_TAGS)
        assert "Total L12M Swipes" in result.columns
        assert "Total L12M Spend" in result.columns
        assert "Active in L12M" in result.columns
        assert result["Total L12M Swipes"].dtype == int

    def test_add_l12m_activity_no_columns(self):
        df = pd.DataFrame({"col1": [1, 2]})
        result = add_l12m_activity(df, ["Feb25"])
        assert result["Total L12M Swipes"].sum() == 0

    def test_add_opening_month(self, sample_df):
        result = add_opening_month(sample_df.copy())
        assert "Opening Month" in result.columns
        # Should be YYYY-MM format
        sample_val = result["Opening Month"].dropna().iloc[0]
        assert len(sample_val) == 7  # e.g., "2025-06"

    def test_add_account_age(self, sample_df):
        ref = datetime(2026, 1, 15)
        result = add_account_age(sample_df.copy(), reference_date=ref)
        assert "Account Age Days" in result.columns
        assert all(result["Account Age Days"] >= 0)

    def test_add_balance_tier(self, sample_df, sample_settings):
        result = add_balance_tier(sample_df.copy(), sample_settings)
        assert "Balance Tier" in result.columns
        # Should have categorized all rows
        assert result["Balance Tier"].notna().sum() > 0

    def test_add_age_range(self, sample_df, sample_settings):
        ref = datetime(2026, 1, 15)
        df = add_account_age(sample_df.copy(), reference_date=ref)
        result = add_age_range(df, sample_settings)
        assert "Age Range" in result.columns


class TestHelpers:
    def test_generate_last_12_months(self):
        ref = datetime(2026, 1, 15)
        tags = generate_last_12_months(ref)
        assert len(tags) == 12
        assert tags[0] == "Feb25"
        assert tags[-1] == "Jan26"

    def test_generate_last_12_months_different_date(self):
        ref = datetime(2025, 6, 10)
        tags = generate_last_12_months(ref)
        assert len(tags) == 12
        assert tags[0] == "Jul24"
        assert tags[-1] == "Jun25"
