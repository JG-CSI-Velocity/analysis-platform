"""Tests for DM source chart builders."""

import pandas as pd
import pytest

from ics_toolkit.analysis.charts.dm_source import (
    chart_dm_activity_by_branch,
    chart_dm_by_branch,
    chart_dm_by_year,
    chart_dm_monthly_trends,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def dm_branch_df():
    return pd.DataFrame(
        {
            "Branch": ["Main", "North", "South", "Total"],
            "Count": [10, 8, 5, 23],
            "% of DM": [43.5, 34.8, 21.7, 100.0],
            "Debit Count": [6, 5, 3, 14],
            "Debit %": [60.0, 62.5, 60.0, 60.9],
            "Avg Balance": [1500.0, 2000.0, 1200.0, 1566.67],
        }
    )


@pytest.fixture
def dm_year_df():
    return pd.DataFrame(
        {
            "Year Opened": ["2023", "2024", "2025", "Total"],
            "Count": [5, 10, 8, 23],
            "%": [21.7, 43.5, 34.8, 100.0],
            "Debit Count": [3, 6, 5, 14],
            "Debit %": [60.0, 60.0, 62.5, 60.9],
            "Avg Balance": [1200.0, 1800.0, 1500.0, 1566.67],
        }
    )


@pytest.fixture
def dm_activity_branch_df():
    return pd.DataFrame(
        {
            "Branch": ["Main", "North", "South", "Total"],
            "Count": [6, 5, 3, 14],
            "Active Count": [4, 3, 2, 9],
            "Activation %": [66.7, 60.0, 66.7, 64.3],
            "Avg Swipes": [15.0, 12.0, 10.0, 12.9],
            "Avg Spend": [150.0, 120.0, 100.0, 128.6],
        }
    )


@pytest.fixture
def dm_monthly_df():
    return pd.DataFrame(
        {
            "Month": ["Feb25", "Mar25", "Apr25"],
            "Total Swipes": [100, 120, 110],
            "Total Spend": [1000.0, 1200.0, 1100.0],
            "Active Accounts": [8, 9, 8],
        }
    )


class TestChartDmByBranch:
    def test_returns_png_bytes(self, dm_branch_df, chart_config):
        result = chart_dm_by_branch(dm_branch_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartDmByYear:
    def test_returns_png_bytes(self, dm_year_df, chart_config):
        result = chart_dm_by_year(dm_year_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartDmActivityByBranch:
    def test_returns_png_bytes(self, dm_activity_branch_df, chart_config):
        result = chart_dm_activity_by_branch(dm_activity_branch_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartDmMonthlyTrends:
    def test_returns_png_bytes(self, dm_monthly_df, chart_config):
        result = chart_dm_monthly_trends(dm_monthly_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
