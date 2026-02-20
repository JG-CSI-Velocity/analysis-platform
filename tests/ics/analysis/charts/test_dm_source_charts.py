"""Tests for DM source chart builders (ax46, ax49, ax51, ax52)."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from ics_toolkit.analysis.charts.dm_source import (
    chart_dm_activity_by_branch,
    chart_dm_by_branch,
    chart_dm_by_year,
    chart_dm_monthly_trends,
)


@pytest.fixture
def dm_branch_df():
    """Sample DM by Branch DataFrame."""
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
    """Sample DM by Year Opened DataFrame."""
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
    """Sample DM Activity by Branch DataFrame."""
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
    """Sample DM Monthly Trends DataFrame."""
    return pd.DataFrame(
        {
            "Month": ["Feb25", "Mar25", "Apr25"],
            "Total Swipes": [100, 120, 110],
            "Total Spend": [1000.0, 1200.0, 1100.0],
            "Active Accounts": [8, 9, 8],
        }
    )


class TestChartDmByBranch:
    """ax46: Horizontal bar of DM count by Branch."""

    def test_returns_figure(self, dm_branch_df, chart_config):
        fig = chart_dm_by_branch(dm_branch_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_traces(self, dm_branch_df, chart_config):
        fig = chart_dm_by_branch(dm_branch_df, chart_config)
        assert len(fig.data) >= 1

    def test_excludes_total(self, dm_branch_df, chart_config):
        fig = chart_dm_by_branch(dm_branch_df, chart_config)
        for trace in fig.data:
            if hasattr(trace, "y") and trace.y is not None:
                assert "Total" not in list(trace.y)

    def test_horizontal_orientation(self, dm_branch_df, chart_config):
        fig = chart_dm_by_branch(dm_branch_df, chart_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        for trace in bar_traces:
            assert trace.orientation == "h"


class TestChartDmByYear:
    """ax49: Vertical bar of DM count by Year Opened."""

    def test_returns_figure(self, dm_year_df, chart_config):
        fig = chart_dm_by_year(dm_year_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, dm_year_df, chart_config):
        fig = chart_dm_by_year(dm_year_df, chart_config)
        for trace in fig.data:
            if hasattr(trace, "x") and trace.x is not None:
                assert "Total" not in list(trace.x)

    def test_has_bar_trace(self, dm_year_df, chart_config):
        fig = chart_dm_by_year(dm_year_df, chart_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) == 1


class TestChartDmActivityByBranch:
    """ax51: Grouped bar + line of DM activity by Branch."""

    def test_returns_figure(self, dm_activity_branch_df, chart_config):
        fig = chart_dm_activity_by_branch(dm_activity_branch_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_multiple_traces(self, dm_activity_branch_df, chart_config):
        fig = chart_dm_activity_by_branch(dm_activity_branch_df, chart_config)
        assert len(fig.data) >= 2

    def test_excludes_total(self, dm_activity_branch_df, chart_config):
        fig = chart_dm_activity_by_branch(dm_activity_branch_df, chart_config)
        for trace in fig.data:
            if hasattr(trace, "x") and trace.x is not None:
                assert "Total" not in list(trace.x)

    def test_has_secondary_axis(self, dm_activity_branch_df, chart_config):
        fig = chart_dm_activity_by_branch(dm_activity_branch_df, chart_config)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert any(t.yaxis == "y2" for t in scatter_traces)


class TestChartDmMonthlyTrends:
    """ax52: Dual-axis line of Swipes + Spend over L12M."""

    def test_returns_figure(self, dm_monthly_df, chart_config):
        fig = chart_dm_monthly_trends(dm_monthly_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_three_traces(self, dm_monthly_df, chart_config):
        fig = chart_dm_monthly_trends(dm_monthly_df, chart_config)
        assert len(fig.data) == 3

    def test_has_dual_axes(self, dm_monthly_df, chart_config):
        fig = chart_dm_monthly_trends(dm_monthly_df, chart_config)
        y_axes = {t.yaxis for t in fig.data if hasattr(t, "yaxis")}
        assert "y" in y_axes
        assert "y2" in y_axes

    def test_spend_on_secondary_axis(self, dm_monthly_df, chart_config):
        fig = chart_dm_monthly_trends(dm_monthly_df, chart_config)
        spend_trace = [t for t in fig.data if t.name == "Total Spend"]
        assert len(spend_trace) == 1
        assert spend_trace[0].yaxis == "y2"
