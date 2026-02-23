"""Tests for portfolio chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.portfolio import (
    chart_closure_by_account_age,
    chart_closure_by_branch,
    chart_closure_by_source,
    chart_closure_rate_trend,
    chart_net_growth_by_source,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartClosureBySource:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Closed Count": [10, 5, 15],
                "% of Closures": [66.7, 33.3, 100.0],
            }
        )
        result = chart_closure_by_source(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartClosureByBranch:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Branch": ["Main", "North", "Total"],
                "Closed Count": [8, 4, 12],
                "% of Closures": [66.7, 33.3, 100.0],
            }
        )
        result = chart_closure_by_branch(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartClosureByAccountAge:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Age Range": ["0-6 months", "6-12 months", "1-2 years"],
                "Closed Count": [5, 3, 2],
                "% of Closures": [50.0, 30.0, 20.0],
            }
        )
        result = chart_closure_by_account_age(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartNetGrowthBySource:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Opens": [20, 15, 35],
                "Closes": [5, 3, 8],
                "Net": [15, 12, 27],
            }
        )
        result = chart_net_growth_by_source(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartClosureRateTrend:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["Jan25", "Feb25", "Mar25"],
                "Closures": [5, 8, 3],
                "Portfolio Size": [100, 95, 87],
                "Closure Rate %": [5.0, 8.4, 3.4],
            }
        )
        result = chart_closure_rate_trend(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
