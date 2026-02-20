"""Tests for new portfolio chart builders (ax67-ax70)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.portfolio import (
    chart_closure_by_account_age,
    chart_closure_by_branch,
    chart_closure_by_source,
    chart_closure_rate_trend,
    chart_net_growth_by_source,
)


class TestChartClosureBySource:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Closed Count": [10, 5, 15],
                "% of Closures": [66.7, 33.3, 100.0],
            }
        )
        fig = chart_closure_by_source(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Closed Count": [10, 5, 15],
                "% of Closures": [66.7, 33.3, 100.0],
            }
        )
        fig = chart_closure_by_source(df, chart_config)
        x_vals = list(fig.data[0].x)
        assert "Total" not in x_vals


class TestChartClosureByBranch:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Closed Count": [8, 4, 12],
                "% of Closures": [66.7, 33.3, 100.0],
            }
        )
        fig = chart_closure_by_branch(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Closed Count": [8, 4, 12],
                "% of Closures": [66.7, 33.3, 100.0],
            }
        )
        fig = chart_closure_by_branch(df, chart_config)
        y_vals = list(fig.data[0].y)
        assert "Total" not in y_vals

    def test_horizontal_bar(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North"],
                "Closed Count": [8, 4],
                "% of Closures": [66.7, 33.3],
            }
        )
        fig = chart_closure_by_branch(df, chart_config)
        assert fig.data[0].orientation == "h"


class TestChartClosureByAccountAge:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Age Range": ["0-6 months", "6-12 months", "1-2 years"],
                "Closed Count": [5, 3, 2],
                "% of Closures": [50.0, 30.0, 20.0],
            }
        )
        fig = chart_closure_by_account_age(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_trace(self, chart_config):
        df = pd.DataFrame(
            {
                "Age Range": ["0-6 months", "6-12 months"],
                "Closed Count": [5, 3],
                "% of Closures": [62.5, 37.5],
            }
        )
        fig = chart_closure_by_account_age(df, chart_config)
        assert isinstance(fig.data[0], go.Bar)


class TestChartNetGrowthBySource:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Opens": [20, 15, 35],
                "Closes": [5, 3, 8],
                "Net": [15, 12, 27],
            }
        )
        fig = chart_net_growth_by_source(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Opens": [20, 15, 35],
                "Closes": [5, 3, 8],
                "Net": [15, 12, 27],
            }
        )
        fig = chart_net_growth_by_source(df, chart_config)
        for trace in fig.data:
            x_vals = list(trace.x)
            assert "Total" not in x_vals

    def test_has_three_traces(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF"],
                "Opens": [20, 15],
                "Closes": [5, 3],
                "Net": [15, 12],
            }
        )
        fig = chart_net_growth_by_source(df, chart_config)
        assert len(fig.data) == 3


class TestChartClosureRateTrend:
    """ax82: Line chart of monthly closure rate."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan25", "Feb25", "Mar25"],
                "Closures": [5, 8, 3],
                "Portfolio Size": [100, 95, 87],
                "Closure Rate %": [5.0, 8.4, 3.4],
            }
        )
        fig = chart_closure_rate_trend(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_and_line(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan25", "Feb25"],
                "Closures": [5, 8],
                "Portfolio Size": [100, 95],
                "Closure Rate %": [5.0, 8.4],
            }
        )
        fig = chart_closure_rate_trend(df, chart_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(bar_traces) >= 1
        assert len(scatter_traces) >= 1

    def test_has_dual_axes(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan25", "Feb25"],
                "Closures": [5, 8],
                "Portfolio Size": [100, 95],
                "Closure Rate %": [5.0, 8.4],
            }
        )
        fig = chart_closure_rate_trend(df, chart_config)
        y_axes = {t.yaxis for t in fig.data if hasattr(t, "yaxis")}
        assert "y" in y_axes
        assert "y2" in y_axes
