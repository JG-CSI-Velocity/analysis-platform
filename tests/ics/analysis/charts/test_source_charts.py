"""Tests for source chart builders."""

import pandas as pd

from ics_toolkit.analysis.charts.source import (
    chart_source_acquisition_mix,
    chart_source_by_branch,
    chart_source_by_prod,
    chart_source_by_stat,
    chart_source_by_year,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TestChartSourceByStat:
    def test_returns_png_bytes(self, crosstab_df, chart_config):
        result = chart_source_by_stat(crosstab_df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartSourceByProd:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "100": [5, 10, 15],
                "200": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        result = chart_source_by_prod(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartSourceByBranch:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Main": [5, 10, 15],
                "North": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        result = chart_source_by_branch(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartSourceByYear:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "2023": [5, 10, 15],
                "2024": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        result = chart_source_by_year(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER


class TestChartSourceAcquisitionMix:
    def test_returns_png_bytes(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["2023-01", "2023-02", "2023-03"],
                "DM": [5, 8, 3],
                "REF": [2, 4, 6],
                "Total": [7, 12, 9],
            }
        )
        result = chart_source_acquisition_mix(df, chart_config)
        assert isinstance(result, bytes)
        assert result[:8] == PNG_HEADER
