"""Tests for new summary chart builder (ax64: Penetration by Branch)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.summary import chart_penetration_by_branch


class TestChartPenetrationByBranch:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Total Accounts": [100, 80, 180],
                "ICS Accounts": [30, 20, 50],
                "Penetration %": [30.0, 25.0, 27.8],
            }
        )
        fig = chart_penetration_by_branch(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_excludes_total(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Total Accounts": [100, 80, 180],
                "ICS Accounts": [30, 20, 50],
                "Penetration %": [30.0, 25.0, 27.8],
            }
        )
        fig = chart_penetration_by_branch(df, chart_config)
        y_vals = list(fig.data[0].y)
        assert "Total" not in y_vals

    def test_horizontal_bar(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North"],
                "Total Accounts": [100, 80],
                "ICS Accounts": [30, 20],
                "Penetration %": [30.0, 25.0],
            }
        )
        fig = chart_penetration_by_branch(df, chart_config)
        assert fig.data[0].orientation == "h"
