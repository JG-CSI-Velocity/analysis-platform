"""Tests for referral chart builders and registry."""

from __future__ import annotations

import pandas as pd
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
    def test_returns_png_bytes(self, top_referrers_df, chart_config):
        result = chart_top_referrers(top_referrers_df, chart_config)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_png_header(self, top_referrers_df, chart_config):
        result = chart_top_referrers(top_referrers_df, chart_config)
        assert result[:4] == b"\x89PNG"

    def test_empty_df_returns_empty(self, chart_config):
        result = chart_top_referrers(pd.DataFrame(columns=["Referrer", "Influence Score"]), chart_config)
        assert result == b""


class TestChartEmergingReferrers:
    def test_returns_png_bytes(self, emerging_referrers_df, chart_config):
        result = chart_emerging_referrers(emerging_referrers_df, chart_config)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_png_header(self, emerging_referrers_df, chart_config):
        result = chart_emerging_referrers(emerging_referrers_df, chart_config)
        assert result[:4] == b"\x89PNG"

    def test_empty_df_returns_empty(self, chart_config):
        result = chart_emerging_referrers(pd.DataFrame(), chart_config)
        assert result == b""


class TestChartStaffMultipliers:
    def test_returns_png_bytes(self, staff_df, chart_config):
        result = chart_staff_multipliers(staff_df, chart_config)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_png_header(self, staff_df, chart_config):
        result = chart_staff_multipliers(staff_df, chart_config)
        assert result[:4] == b"\x89PNG"

    def test_without_referrals_processed(self, chart_config):
        df = pd.DataFrame({"Staff": ["A", "B"], "Multiplier Score": [80, 60]})
        result = chart_staff_multipliers(df, chart_config)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestChartBranchDensity:
    def test_returns_png_bytes(self, branch_df, chart_config):
        result = chart_branch_density(branch_df, chart_config)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_png_header(self, branch_df, chart_config):
        result = chart_branch_density(branch_df, chart_config)
        assert result[:4] == b"\x89PNG"

    def test_empty_df_returns_empty(self, chart_config):
        result = chart_branch_density(pd.DataFrame(columns=["Branch", "Avg Influence Score"]), chart_config)
        assert result == b""


class TestChartCodeHealth:
    def test_returns_png_bytes(self, code_health_df, chart_config):
        result = chart_code_health(code_health_df, chart_config)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_png_header(self, code_health_df, chart_config):
        result = chart_code_health(code_health_df, chart_config)
        assert result[:4] == b"\x89PNG"

    def test_empty_df_returns_empty(self, chart_config):
        result = chart_code_health(pd.DataFrame(), chart_config)
        assert result == b""


class TestCreateReferralCharts:
    def test_creates_charts_for_matching_analyses(self, top_referrers_df, chart_config):
        analyses = [
            AnalysisResult.from_df("Top Referrers", "Top Referrers", top_referrers_df),
        ]
        charts = create_referral_charts(analyses, chart_config)
        assert "Top Referrers" in charts
        assert isinstance(charts["Top Referrers"], bytes)
        assert charts["Top Referrers"][:4] == b"\x89PNG"

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
