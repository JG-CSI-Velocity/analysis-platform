"""Tests for performance chart builders (ax81)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.performance import (
    chart_product_code_performance,
)


class TestChartProductCodePerformance:
    """ax81: Grouped bar of activation rate + avg swipes by Product Code."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Prod Code": ["100", "200", "Total"],
                "Accounts": [20, 15, 35],
                "Activation %": [75.0, 60.0, 68.6],
                "Avg Swipes": [12.0, 8.0, 10.3],
                "Avg Spend": [150.0, 100.0, 128.6],
                "Avg Balance": [5000.0, 3000.0, 4143.0],
            }
        )
        fig = chart_product_code_performance(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_bar_and_line(self, chart_config):
        df = pd.DataFrame(
            {
                "Prod Code": ["100", "200", "Total"],
                "Accounts": [20, 15, 35],
                "Activation %": [75.0, 60.0, 68.6],
            }
        )
        fig = chart_product_code_performance(df, chart_config)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(bar_traces) >= 1
        assert len(scatter_traces) >= 1

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Prod Code": ["100", "200", "Total"],
                "Accounts": [20, 15, 35],
                "Activation %": [75.0, 60.0, 68.6],
            }
        )
        fig = chart_product_code_performance(df, chart_config)
        for trace in fig.data:
            if hasattr(trace, "x") and trace.x is not None:
                assert "Total" not in list(trace.x)

    def test_has_dual_axes(self, chart_config):
        df = pd.DataFrame(
            {
                "Prod Code": ["100", "200"],
                "Accounts": [20, 15],
                "Activation %": [75.0, 60.0],
            }
        )
        fig = chart_product_code_performance(df, chart_config)
        y_axes = {t.yaxis for t in fig.data if hasattr(t, "yaxis")}
        assert "y" in y_axes
        assert "y2" in y_axes
