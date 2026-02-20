"""Tests for new activity chart builders (ax71, ax72)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.activity import (
    chart_business_vs_personal,
    chart_monthly_interchange,
)


class TestChartMonthlyInterchange:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan26", "Feb26", "Mar26"],
                "Total Spend": [10000, 12000, 11000],
                "Total Swipes": [500, 600, 550],
                "Est. Interchange": [182, 218.4, 200.2],
            }
        )
        fig = chart_monthly_interchange(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_two_traces(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan26", "Feb26"],
                "Total Spend": [10000, 12000],
                "Total Swipes": [500, 600],
                "Est. Interchange": [182, 218.4],
            }
        )
        fig = chart_monthly_interchange(df, chart_config)
        assert len(fig.data) == 2

    def test_has_bar_and_line(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan26", "Feb26"],
                "Total Spend": [10000, 12000],
                "Total Swipes": [500, 600],
                "Est. Interchange": [182, 218.4],
            }
        )
        fig = chart_monthly_interchange(df, chart_config)
        assert isinstance(fig.data[0], go.Bar)
        assert isinstance(fig.data[1], go.Scatter)


class TestChartBusinessVsPersonal:
    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": [
                    "Total Accounts",
                    "% Active",
                    "Total Swipes",
                    "Total Spend",
                    "Avg Swipes / Account",
                    "Avg Spend / Account",
                    "Avg Swipes / Active",
                    "Avg Spend / Active",
                    "Avg Spend / Swipe",
                    "Avg Current Balance",
                    "Active Accounts",
                    "Inactive Accounts",
                ],
                "Business": [10, 50.0, 200, 5000, 20, 500, 40, 1000, 25, 3000, 5, 5],
                "Personal": [40, 60.0, 800, 20000, 20, 500, 33, 833, 25, 2500, 24, 16],
            }
        )
        fig = chart_business_vs_personal(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_two_traces(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": ["% Active", "Avg Swipes / Account", "Avg Spend / Account"],
                "Business": [50.0, 20, 500],
                "Personal": [60.0, 20, 500],
            }
        )
        fig = chart_business_vs_personal(df, chart_config)
        assert len(fig.data) == 2

    def test_empty_on_no_chart_metrics(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": ["Total Accounts", "Inactive Accounts"],
                "Business": [10, 5],
                "Personal": [40, 16],
            }
        )
        fig = chart_business_vs_personal(df, chart_config)
        assert len(fig.data) == 0
