"""Tests for activity chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.activity import (
    chart_business_vs_personal,
    chart_monthly_interchange,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartMonthlyInterchange:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan26", "Feb26", "Mar26"],
                "Total Spend": [10000, 12000, 11000],
                "Total Swipes": [500, 600, 550],
                "Est. Interchange": [182, 218.4, 200.2],
            }
        )
        result = chart_monthly_interchange(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartBusinessVsPersonal:
    def test_returns_png_bytes(self, chart_config):
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
        result = chart_business_vs_personal(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER

    def test_no_chart_metrics_still_returns_png(self, chart_config):
        df = pd.DataFrame(
            {
                "Metric": ["Total Accounts", "Inactive Accounts"],
                "Business": [10, 5],
                "Personal": [40, 16],
            }
        )
        result = chart_business_vs_personal(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
