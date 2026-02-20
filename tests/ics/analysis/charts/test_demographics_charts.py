"""Tests for demographics chart builders (ax16, ax18)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.demographics import (
    chart_balance_trajectory,
    chart_open_vs_close,
    chart_stat_open_close,
)


class TestChartOpenVsClose:
    """ax16: Bar chart of Open vs Closed counts."""

    def test_returns_figure(self, kpi_df, chart_config):
        fig = chart_open_vs_close(kpi_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_two_bars(self, kpi_df, chart_config):
        fig = chart_open_vs_close(kpi_df, chart_config)
        assert len(fig.data[0].x) == 2

    def test_values_match(self, kpi_df, chart_config):
        fig = chart_open_vs_close(kpi_df, chart_config)
        y_vals = list(fig.data[0].y)
        assert y_vals == [80, 20]


class TestChartStatOpenClose:
    """ax18: Grouped bar + line of Stat Code, Count, Avg Balance."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Stat Code": ["O", "C", "Grand Total"],
                "Count": [80, 20, 100],
                "Avg Curr Bal": [5000.0, 1200.0, 4240.0],
                "% of Count": [80.0, 20.0, 100.0],
            }
        )
        fig = chart_stat_open_close(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_and_line(self, chart_config):
        df = pd.DataFrame(
            {
                "Stat Code": ["O", "C", "Grand Total"],
                "Count": [80, 20, 100],
                "Avg Curr Bal": [5000.0, 1200.0, 4240.0],
                "% of Count": [80.0, 20.0, 100.0],
            }
        )
        fig = chart_stat_open_close(df, chart_config)
        assert len(fig.data) == 2
        assert isinstance(fig.data[0], go.Bar)
        assert isinstance(fig.data[1], go.Scatter)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Stat Code": ["O", "C", "Grand Total"],
                "Count": [80, 20, 100],
                "Avg Curr Bal": [5000.0, 1200.0, 4240.0],
                "% of Count": [80.0, 20.0, 100.0],
            }
        )
        fig = chart_stat_open_close(df, chart_config)
        for trace in fig.data:
            x_vals = list(trace.x)
            assert "Grand Total" not in x_vals


class TestChartBalanceTrajectory:
    """ax83: Grouped bar of Avg Bal vs Curr Bal by Branch."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Avg Bal": [5000.0, 3000.0, 4000.0],
                "Curr Bal": [5500.0, 2800.0, 4150.0],
                "Change ($)": [500.0, -200.0, 150.0],
                "Change (%)": [10.0, -6.7, 3.75],
            }
        )
        fig = chart_balance_trajectory(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_two_bar_traces(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Avg Bal": [5000.0, 3000.0, 4000.0],
                "Curr Bal": [5500.0, 2800.0, 4150.0],
            }
        )
        fig = chart_balance_trajectory(df, chart_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        assert len(bar_traces) == 2

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Avg Bal": [5000.0, 3000.0, 4000.0],
                "Curr Bal": [5500.0, 2800.0, 4150.0],
            }
        )
        fig = chart_balance_trajectory(df, chart_config)
        for trace in fig.data:
            if hasattr(trace, "x") and trace.x is not None:
                assert "Total" not in list(trace.x)
