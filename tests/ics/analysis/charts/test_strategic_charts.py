"""Tests for strategic chart builders."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.strategic import (
    chart_activation_funnel,
    chart_revenue_by_branch,
    chart_revenue_by_source,
    chart_revenue_impact,
)


class TestChartActivationFunnel:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Stage": ["Total", "ICS", "Stat O", "Debit", "Active"],
                "Count": [1000, 300, 250, 200, 120],
                "% of Total": [100.0, 30.0, 25.0, 20.0, 12.0],
                "Drop-off %": [0.0, 70.0, 16.7, 20.0, 40.0],
            }
        )
        fig = chart_activation_funnel(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_is_funnel(self, chart_config):
        df = pd.DataFrame(
            {
                "Stage": ["Total", "ICS", "Active"],
                "Count": [1000, 300, 120],
                "% of Total": [100.0, 30.0, 12.0],
                "Drop-off %": [0.0, 70.0, 60.0],
            }
        )
        fig = chart_activation_funnel(df, chart_config)
        assert isinstance(fig.data[0], go.Funnel)


class TestChartRevenueImpact:
    def test_returns_figure(self, chart_config):
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
        fig = chart_revenue_impact(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_skips_count_metric(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": [
                    "Estimated Annual Interchange",
                    "Never-Activator Count",
                    "Revenue at Risk (Dormant)",
                ],
                "Value": [15000.0, 80, 5000.0],
            }
        )
        fig = chart_revenue_impact(df, chart_config)
        labels = list(fig.data[0].x)
        assert "Never-Activator Count" not in labels


class TestChartRevenueByBranch:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Accounts": [50, 30, 80],
                "Total L12M Spend": [25000, 15000, 40000],
                "Est. Interchange": [455, 273, 728],
                "Avg Spend": [500, 500, 500],
            }
        )
        fig = chart_revenue_by_branch(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Accounts": [50, 30, 80],
                "Total L12M Spend": [25000, 15000, 40000],
                "Est. Interchange": [455, 273, 728],
                "Avg Spend": [500, 500, 500],
            }
        )
        fig = chart_revenue_by_branch(df, chart_config)
        y_vals = list(fig.data[0].y)
        assert "Total" not in y_vals

    def test_horizontal_bar(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North"],
                "Accounts": [50, 30],
                "Total L12M Spend": [25000, 15000],
                "Est. Interchange": [455, 273],
                "Avg Spend": [500, 500],
            }
        )
        fig = chart_revenue_by_branch(df, chart_config)
        assert fig.data[0].orientation == "h"


class TestChartRevenueBySource:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Accounts": [40, 30, 70],
                "Total L12M Spend": [20000, 15000, 35000],
                "Est. Interchange": [364, 273, 637],
                "Avg Spend": [500, 500, 500],
            }
        )
        fig = chart_revenue_by_source(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Accounts": [40, 30, 70],
                "Total L12M Spend": [20000, 15000, 35000],
                "Est. Interchange": [364, 273, 637],
                "Avg Spend": [500, 500, 500],
            }
        )
        fig = chart_revenue_by_source(df, chart_config)
        x_vals = list(fig.data[0].x)
        assert "Total" not in x_vals
