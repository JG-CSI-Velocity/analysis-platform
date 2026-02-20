"""Tests for referral chart builders and registry."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.charts import (
    REFERRAL_CHART_REGISTRY,
    create_referral_charts,
)
from ics_toolkit.referral.charts.branch_density import chart_branch_density
from ics_toolkit.referral.charts.code_health import chart_code_health
from ics_toolkit.referral.charts.emerging_referrers import chart_emerging_referrers
from ics_toolkit.referral.charts.staff_multipliers import chart_staff_multipliers
from ics_toolkit.referral.charts.top_referrers import chart_top_referrers
from ics_toolkit.settings import ChartConfig


@pytest.fixture
def chart_config():
    return ChartConfig()


@pytest.fixture
def top_referrers_df():
    return pd.DataFrame(
        {
            "Referrer": ["ALICE", "BOB", "CHARLIE"],
            "Influence Score": [85.0, 72.0, 60.0],
            "Total Referrals": [10, 7, 5],
            "Unique Accounts": [8, 6, 4],
        }
    )


@pytest.fixture
def emerging_referrers_df():
    return pd.DataFrame(
        {
            "Referrer": ["NEW_A", "NEW_B"],
            "Influence Score": [70.0, 55.0],
            "Burst Count": [3, 2],
            "First Referral": pd.to_datetime(["2025-12-01", "2025-11-15"]),
        }
    )


@pytest.fixture
def staff_df():
    return pd.DataFrame(
        {
            "Staff": ["SARAH", "MIKE"],
            "Multiplier Score": [80.0, 60.0],
            "Referrals Processed": [25, 18],
            "Unique Referrers": [10, 8],
        }
    )


@pytest.fixture
def branch_df():
    return pd.DataFrame(
        {
            "Branch": ["001", "002", "003"],
            "Avg Influence Score": [75.0, 60.0, 45.0],
            "Total Referrals": [20, 15, 10],
        }
    )


@pytest.fixture
def code_health_df():
    return pd.DataFrame(
        {
            "Channel": ["BRANCH_STANDARD", "BRANCH_STANDARD", "MANUAL"],
            "Type": ["Standard", "Standard", "Manual"],
            "Reliability": ["High", "Medium", "Low"],
            "Count": [30, 10, 5],
            "% of Total": [66.67, 22.22, 11.11],
        }
    )


class TestChartRegistry:
    def test_has_five_entries(self):
        assert len(REFERRAL_CHART_REGISTRY) == 5

    def test_all_entries_callable(self):
        for name, func in REFERRAL_CHART_REGISTRY.items():
            assert callable(func), f"{name} is not callable"

    def test_expected_names(self):
        expected = {
            "Top Referrers",
            "Emerging Referrers",
            "Staff Multipliers",
            "Branch Influence Density",
            "Code Health Report",
        }
        assert set(REFERRAL_CHART_REGISTRY.keys()) == expected


class TestChartTopReferrers:
    def test_returns_figure(self, top_referrers_df, chart_config):
        fig = chart_top_referrers(top_referrers_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_trace(self, top_referrers_df, chart_config):
        fig = chart_top_referrers(top_referrers_df, chart_config)
        assert any(isinstance(t, go.Bar) for t in fig.data)

    def test_horizontal_orientation(self, top_referrers_df, chart_config):
        fig = chart_top_referrers(top_referrers_df, chart_config)
        bar = [t for t in fig.data if isinstance(t, go.Bar)][0]
        assert bar.orientation == "h"


class TestChartEmergingReferrers:
    def test_returns_figure(self, emerging_referrers_df, chart_config):
        fig = chart_emerging_referrers(emerging_referrers_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_scatter_trace(self, emerging_referrers_df, chart_config):
        fig = chart_emerging_referrers(emerging_referrers_df, chart_config)
        assert any(isinstance(t, go.Scatter) for t in fig.data)

    def test_marker_mode(self, emerging_referrers_df, chart_config):
        fig = chart_emerging_referrers(emerging_referrers_df, chart_config)
        scatter = [t for t in fig.data if isinstance(t, go.Scatter)][0]
        assert scatter.mode == "markers"


class TestChartStaffMultipliers:
    def test_returns_figure(self, staff_df, chart_config):
        fig = chart_staff_multipliers(staff_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_traces(self, staff_df, chart_config):
        fig = chart_staff_multipliers(staff_df, chart_config)
        bars = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bars) >= 1

    def test_grouped_barmode(self, staff_df, chart_config):
        fig = chart_staff_multipliers(staff_df, chart_config)
        assert fig.layout.barmode == "group"


class TestChartBranchDensity:
    def test_returns_figure(self, branch_df, chart_config):
        fig = chart_branch_density(branch_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_trace(self, branch_df, chart_config):
        fig = chart_branch_density(branch_df, chart_config)
        assert any(isinstance(t, go.Bar) for t in fig.data)

    def test_vertical_orientation(self, branch_df, chart_config):
        fig = chart_branch_density(branch_df, chart_config)
        bar = [t for t in fig.data if isinstance(t, go.Bar)][0]
        # Default orientation is vertical (None or "v")
        assert bar.orientation in (None, "v")


class TestChartCodeHealth:
    def test_returns_figure(self, code_health_df, chart_config):
        fig = chart_code_health(code_health_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_stacked_barmode(self, code_health_df, chart_config):
        fig = chart_code_health(code_health_df, chart_config)
        assert fig.layout.barmode == "stack"

    def test_one_trace_per_reliability(self, code_health_df, chart_config):
        fig = chart_code_health(code_health_df, chart_config)
        n_reliabilities = code_health_df["Reliability"].nunique()
        assert len(fig.data) == n_reliabilities


class TestCreateReferralCharts:
    def test_creates_charts_for_matching_analyses(self, top_referrers_df, chart_config):
        analyses = [
            AnalysisResult.from_df("Top Referrers", "Top Referrers", top_referrers_df),
        ]
        charts = create_referral_charts(analyses, chart_config)
        assert "Top Referrers" in charts
        assert isinstance(charts["Top Referrers"], go.Figure)

    def test_skips_empty_analyses(self, chart_config):
        analyses = [
            AnalysisResult.from_df("Top Referrers", "Top Referrers", pd.DataFrame()),
        ]
        charts = create_referral_charts(analyses, chart_config)
        assert "Top Referrers" not in charts

    def test_skips_errored_analyses(self, top_referrers_df, chart_config):
        analyses = [
            AnalysisResult.from_df(
                "Top Referrers",
                "Top Referrers",
                top_referrers_df,
                error="oops",
            ),
        ]
        charts = create_referral_charts(analyses, chart_config)
        assert "Top Referrers" not in charts

    def test_skips_unregistered_analyses(self, chart_config):
        analyses = [
            AnalysisResult.from_df("Unknown Analysis", "Unknown", pd.DataFrame({"a": [1]})),
        ]
        charts = create_referral_charts(analyses, chart_config)
        assert len(charts) == 0
