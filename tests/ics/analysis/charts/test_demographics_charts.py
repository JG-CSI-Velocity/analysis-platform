"""Tests for demographics chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.demographics import (
    chart_balance_trajectory,
    chart_open_vs_close,
    chart_stat_open_close,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartOpenVsClose:
    def test_returns_png_bytes(self, kpi_df, chart_config):
        result = chart_open_vs_close(kpi_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartStatOpenClose:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Stat Code": ["O", "C", "Grand Total"],
                "Count": [80, 20, 100],
                "Avg Curr Bal": [5000.0, 1200.0, 4240.0],
                "% of Count": [80.0, 20.0, 100.0],
            }
        )
        result = chart_stat_open_close(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartBalanceTrajectory:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Avg Bal": [5000.0, 3000.0, 4000.0],
                "Curr Bal": [5500.0, 2800.0, 4150.0],
                "Change ($)": [500.0, -200.0, 150.0],
                "Change (%)": [10.0, -6.7, 3.75],
            }
        )
        result = chart_balance_trajectory(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
