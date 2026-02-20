"""Tests for source chart builders (ax09, ax10, ax11, ax13)."""

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.charts.source import (
    chart_source_acquisition_mix,
    chart_source_by_branch,
    chart_source_by_prod,
    chart_source_by_stat,
    chart_source_by_year,
)


class TestChartSourceByStat:
    """ax09: Stacked bar of Source x Stat Code."""

    def test_returns_figure(self, crosstab_df, chart_config):
        fig = chart_source_by_stat(crosstab_df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_has_traces(self, crosstab_df, chart_config):
        fig = chart_source_by_stat(crosstab_df, chart_config)
        assert len(fig.data) >= 1

    def test_stacked_layout(self, crosstab_df, chart_config):
        fig = chart_source_by_stat(crosstab_df, chart_config)
        assert fig.layout.barmode == "stack"

    def test_excludes_total_row(self, crosstab_df, chart_config):
        fig = chart_source_by_stat(crosstab_df, chart_config)
        for trace in fig.data:
            assert "Total" not in list(trace.x)


class TestChartSourceByProd:
    """ax10: Grouped bar of Source x Prod Code."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "100": [5, 10, 15],
                "200": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        fig = chart_source_by_prod(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_grouped_layout(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "100": [5, 10, 15],
                "200": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        fig = chart_source_by_prod(df, chart_config)
        assert fig.layout.barmode == "group"


class TestChartSourceByBranch:
    """ax11: Heatmap of Source x Branch."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Main": [5, 10, 15],
                "North": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        fig = chart_source_by_branch(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_is_heatmap(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "Main": [5, 10, 15],
                "North": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        fig = chart_source_by_branch(df, chart_config)
        assert isinstance(fig.data[0], go.Heatmap)


class TestChartSourceByYear:
    """ax13: Stacked bar of Source by Year Opened."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "2023": [5, 10, 15],
                "2024": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        fig = chart_source_by_year(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_stacked_layout(self, chart_config):
        df = pd.DataFrame(
            {
                "Source": ["DM", "REF", "Total"],
                "2023": [5, 10, 15],
                "2024": [3, 8, 11],
                "Total": [8, 18, 26],
            }
        )
        fig = chart_source_by_year(df, chart_config)
        assert fig.layout.barmode == "stack"


class TestChartSourceAcquisitionMix:
    """ax85: Stacked bar of monthly new account opens by source channel."""

    def test_returns_figure(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["2023-01", "2023-02", "2023-03"],
                "DM": [5, 8, 3],
                "REF": [2, 4, 6],
                "Total": [7, 12, 9],
            }
        )
        fig = chart_source_acquisition_mix(df, chart_config)
        assert isinstance(fig, go.Figure)

    def test_stacked_layout(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["2023-01", "2023-02"],
                "DM": [5, 8],
                "REF": [2, 4],
                "Total": [7, 12],
            }
        )
        fig = chart_source_acquisition_mix(df, chart_config)
        assert fig.layout.barmode == "stack"

    def test_has_source_traces(self, chart_config):
        df = pd.DataFrame(
            {
                "Month": ["2023-01", "2023-02"],
                "DM": [5, 8],
                "REF": [2, 4],
                "Total": [7, 12],
            }
        )
        fig = chart_source_acquisition_mix(df, chart_config)
        trace_names = {t.name for t in fig.data}
        assert "DM" in trace_names
        assert "REF" in trace_names
        assert "Total" not in trace_names
