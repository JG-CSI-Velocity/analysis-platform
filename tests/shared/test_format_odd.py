"""Tests for the 7-step ODDD formatting pipeline."""

import pandas as pd
import pytest

from shared.format_odd import (
    _categorize_swipes,
    _step2_drop_pytd_ytd,
    _step3_totals_averages_categories,
    _step5_age_calculations,
    _step6_mail_response_grouping,
    _step7_control_segmentation,
    format_odd,
)


@pytest.fixture
def sample_oddd():
    """Minimal ODDD-like DataFrame for testing."""
    return pd.DataFrame(
        {
            "Acct Number": ["001", "002", "003"],
            "Stat Code": ["O", "O", "C"],
            "Business?": ["No", "Yes", "No"],
            "Debit?": ["Yes", "No", "Yes"],
            "Date Opened": ["2020-01-15", "2019-06-01", "2018-03-10"],
            "DOB": ["1990-05-20", "1985-11-03", "1975-08-15"],
            "Jan25 PIN $": [100, 200, 0],
            "Jan25 Sig $": [50, 100, 0],
            "Jan25 PIN #": [5, 10, 0],
            "Jan25 Sig #": [3, 7, 0],
            "Feb25 PIN $": [120, 180, 0],
            "Feb25 Sig $": [60, 90, 0],
            "Feb25 PIN #": [6, 9, 0],
            "Feb25 Sig #": [4, 5, 0],
            "PYTD Spend": [1000, 2000, 0],
            "YTD Items": [50, 100, 0],
            "Jan25 Mail": ["NU", "TH-10", None],
            "Jan25 Resp": ["NU 5+", "NU 1-4", None],
        }
    )


class TestStep2:
    def test_drops_pytd_ytd(self, sample_oddd):
        result = _step2_drop_pytd_ytd(sample_oddd)
        assert "PYTD Spend" not in result.columns
        assert "YTD Items" not in result.columns
        assert "Acct Number" in result.columns


class TestStep3:
    def test_creates_total_columns(self, sample_oddd):
        df = _step2_drop_pytd_ytd(sample_oddd)
        result = _step3_totals_averages_categories(df)
        assert "Total Spend" in result.columns
        assert "Total Swipes" in result.columns
        assert "MonthlySwipes12" in result.columns
        assert "SwipeCat12" in result.columns


class TestStep5:
    def test_creates_age_columns(self, sample_oddd):
        result = _step5_age_calculations(sample_oddd)
        assert "Account Holder Age" in result.columns
        assert "Account Age" in result.columns
        assert result["Account Holder Age"].notna().all()


class TestStep6:
    def test_response_grouping(self, sample_oddd):
        result = _step6_mail_response_grouping(sample_oddd)
        assert "# of Offers" in result.columns
        assert "# of Responses" in result.columns
        assert "Response Grouping" in result.columns
        # Account 001: 1 offer, 1 response (NU 5+) -> SO-SR
        assert result.loc[0, "Response Grouping"] == "SO-SR"
        # Account 003: 0 offers -> No Offer
        assert result.loc[2, "Response Grouping"] == "No Offer"


class TestStep7:
    def test_creates_segmentation_columns(self, sample_oddd):
        result = _step7_control_segmentation(sample_oddd)
        assert "Jan25 Segmentation" in result.columns
        # Account 001: mailed + responded -> Responder
        assert result.loc[0, "Jan25 Segmentation"] == "Responder"
        # Account 002: mailed + not responded (NU 1-4 excluded) -> Non-Responder
        assert result.loc[1, "Jan25 Segmentation"] == "Non-Responder"
        # Account 003: not mailed -> Control
        assert result.loc[2, "Jan25 Segmentation"] == "Control"


class TestCategorizeSwipes:
    def test_non_user(self):
        assert _categorize_swipes(0) == "Non-user"
        assert _categorize_swipes(0.5) == "Non-user"

    def test_tiers(self):
        assert _categorize_swipes(3) == "1-5 Swipes"
        assert _categorize_swipes(8) == "6-10 Swipes"
        assert _categorize_swipes(50) == "41+ Swipes"


class TestFormatOddEndToEnd:
    def test_full_pipeline(self, sample_oddd):
        result = format_odd(sample_oddd)
        # PYTD/YTD dropped
        assert "PYTD Spend" not in result.columns
        # Totals created
        assert "Total Spend" in result.columns
        # Ages calculated
        assert "Account Holder Age" in result.columns
        # Response grouping done
        assert "Response Grouping" in result.columns
        # Segmentation done
        assert "Jan25 Segmentation" in result.columns
        # Original data preserved
        assert len(result) == 3
