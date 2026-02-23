"""Tests for strategic chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.strategic import (
    chart_activation_funnel,
    chart_revenue_by_branch,
    chart_revenue_by_source,
    chart_revenue_impact,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartActivationFunnel:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Stage": ["Total", "ICS", "Stat O", "Debit", "Active"],
                "Count": [1000, 300, 250, 200, 120],
                "% of Total": [100.0, 30.0, 25.0, 20.0, 12.0],
                "Drop-off %": [0.0, 70.0, 16.7, 20.0, 40.0],
            }
        )
        result = chart_activation_funnel(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartRevenueImpact:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": [
                    "Estimated Annual Interchange",
                    "Revenue per Active Card",
                    "Never-Activator Count",
                    "Revenue at Risk (Dormant)",
                ],
                "Value": [15000.0, 125.0, 80, 5000.0],
            }
        )
        result = chart_revenue_impact(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartRevenueByBranch:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Accounts": [50, 30, 80],
                "Total L12M Spend": [25000, 15000, 40000],
                "Est. Interchange": [455, 273, 728],
                "Avg Spend": [500, 500, 500],
            }
        )
        result = chart_revenue_by_branch(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartRevenueBySource:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Accounts": [40, 30, 70],
                "Total L12M Spend": [20000, 15000, 35000],
                "Est. Interchange": [364, 273, 637],
                "Avg Spend": [500, 500, 500],
            }
        )
        result = chart_revenue_by_source(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
