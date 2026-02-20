"""Tests for txn_analysis.v4_themes -- chart builders and formatting utilities."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from txn_analysis.v4_themes import (
    CATEGORY_PALETTE,
    COLORS,
    COMPETITOR_COLORS,
    FONT_FAMILY,
    GENERATION_COLORS,
    add_source_footer,
    apply_theme,
    bullet_chart,
    donut_chart,
    ensure_theme,
    format_currency,
    format_pct,
    grouped_bar,
    heatmap,
    horizontal_bar,
    insight_title,
    line_trend,
    lollipop_chart,
    scatter_plot,
    stacked_bar,
    waterfall_chart,
)


class TestColorPalettes:
    def test_colors_dict_keys(self):
        assert "primary" in COLORS
        assert "secondary" in COLORS
        assert "accent" in COLORS
        assert "positive" in COLORS
        assert "negative" in COLORS

    def test_category_palette_length(self):
        assert len(CATEGORY_PALETTE) == 8

    def test_competitor_colors_keys(self):
        assert "big_nationals" in COMPETITOR_COLORS
        assert "credit_unions" in COMPETITOR_COLORS

    def test_generation_colors_keys(self):
        assert "Gen Z" in GENERATION_COLORS
        assert "Boomer" in GENERATION_COLORS

    def test_font_family_is_string(self):
        assert isinstance(FONT_FAMILY, str)
        assert "sans-serif" in FONT_FAMILY


class TestThemeRegistration:
    def test_ensure_theme_idempotent(self):
        ensure_theme()
        ensure_theme()  # second call should not raise

    def test_apply_theme_returns_figure(self):
        fig = go.Figure(go.Bar(x=[1, 2], y=[3, 4]))
        result = apply_theme(fig)
        assert isinstance(result, go.Figure)


class TestFormatting:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (1_500_000, "$1.5M"),
            (-2_000_000, "-$2.0M"),
            (50_000, "$50.0K"),
            (10_000, "$10.0K"),
            (5_000, "$5,000"),
            (1_000, "$1,000"),
            (99.50, "$99.50"),
            (0, "$0.00"),
            (-500, "-$500.00"),
        ],
    )
    def test_format_currency(self, value, expected):
        assert format_currency(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (5.3, "+5.3%"),
            (-2.1, "-2.1%"),
            (0.0, "+0.0%"),
        ],
    )
    def test_format_pct(self, value, expected):
        assert format_pct(value) == expected


class TestHorizontalBar:
    def test_returns_figure(self):
        df = pd.DataFrame({"merchant": ["A", "B", "C"], "spend": [100, 200, 300]})
        fig = horizontal_bar(df, "spend", "merchant", "Top Merchants")
        assert isinstance(fig, go.Figure)

    def test_top_n_limits(self):
        df = pd.DataFrame({"name": list("ABCDE"), "val": range(5)})
        fig = horizontal_bar(df, "val", "name", "Test", top_n=3)
        assert len(fig.data[0].x) == 3

    def test_custom_color(self):
        df = pd.DataFrame({"name": ["A"], "val": [100]})
        fig = horizontal_bar(df, "val", "name", "Test", color="#FF0000")
        assert isinstance(fig, go.Figure)


class TestLollipopChart:
    def test_returns_figure(self):
        df = pd.DataFrame({"name": ["A", "B", "C"], "val": [10, 20, 30]})
        fig = lollipop_chart(df, "val", "name", "Test Lollipop")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # stems + dots

    def test_empty_data(self):
        df = pd.DataFrame({"name": [], "val": []})
        fig = lollipop_chart(df, "val", "name", "Empty")
        assert isinstance(fig, go.Figure)


class TestLineTrend:
    def test_single_line(self):
        df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "spend": [100, 200, 150]})
        fig = line_trend(df, "month", ["spend"], "Monthly Spend")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1

    def test_multiple_lines(self):
        df = pd.DataFrame({"month": ["Jan", "Feb"], "pin": [100, 200], "sig": [300, 400]})
        fig = line_trend(df, "month", ["pin", "sig"], "PIN vs SIG")
        assert len(fig.data) == 2

    def test_y_format(self):
        df = pd.DataFrame({"x": [1, 2], "y": [0.5, 0.8]})
        fig = line_trend(df, "x", ["y"], "Pct", y_format=",.0%")
        assert isinstance(fig, go.Figure)


class TestStackedBar:
    def test_basic(self):
        df = pd.DataFrame({"cat": ["A", "B"], "v1": [10, 20], "v2": [30, 40]})
        fig = stacked_bar(df, "cat", ["v1", "v2"], "Stacked")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2

    def test_percentage_mode(self):
        df = pd.DataFrame({"cat": ["A", "B"], "v1": [10, 20], "v2": [30, 40]})
        fig = stacked_bar(df, "cat", ["v1", "v2"], "Pct", as_percentage=True)
        assert isinstance(fig, go.Figure)


class TestDonutChart:
    def test_returns_figure(self):
        fig = donut_chart(["A", "B", "C"], [10, 20, 30], "Composition")
        assert isinstance(fig, go.Figure)
        assert fig.data[0].hole == 0.4

    def test_custom_hole(self):
        fig = donut_chart(["X"], [100], "Single", hole=0.6)
        assert fig.data[0].hole == 0.6


class TestHeatmap:
    def test_returns_figure(self):
        df = pd.DataFrame({"Jan": [1, 2], "Feb": [3, 4]}, index=["A", "B"])
        fig = heatmap(df, "Monthly Heatmap")
        assert isinstance(fig, go.Figure)


class TestBulletChart:
    def test_returns_figure(self):
        fig = bullet_chart(75, 100, "Revenue")
        assert isinstance(fig, go.Figure)

    def test_custom_ranges(self):
        fig = bullet_chart(50, 80, "KPI", ranges=[40, 60, 100])
        assert isinstance(fig, go.Figure)


class TestScatterPlot:
    def test_basic(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        fig = scatter_plot(df, "x", "y", "Scatter")
        assert isinstance(fig, go.Figure)

    def test_with_size_and_color(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4], "sz": [10, 20], "grp": ["A", "B"]})
        fig = scatter_plot(df, "x", "y", "Bubble", size_col="sz", color_col="grp")
        assert isinstance(fig, go.Figure)

    def test_with_hover(self):
        df = pd.DataFrame({"x": [1], "y": [2], "label": ["Point A"]})
        fig = scatter_plot(df, "x", "y", "Hover", hover_col="label")
        assert isinstance(fig, go.Figure)


class TestGroupedBar:
    def test_returns_figure(self):
        df = pd.DataFrame({"cat": ["A", "B"], "m1": [10, 20], "m2": [30, 40]})
        fig = grouped_bar(df, "cat", ["m1", "m2"], "Grouped")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2


class TestWaterfallChart:
    def test_returns_figure(self):
        fig = waterfall_chart(["Revenue", "Costs", "Profit"], [100, -40, 60], "Waterfall")
        assert isinstance(fig, go.Figure)

    def test_empty(self):
        fig = waterfall_chart([], [], "Empty")
        assert isinstance(fig, go.Figure)


class TestInsightTitle:
    def test_main_only(self):
        result = insight_title("Top merchants")
        assert "Top merchants" in result["text"]
        assert isinstance(result, dict)

    def test_with_subtitle(self):
        result = insight_title("Main", "Sub detail")
        assert "Main" in result["text"]
        assert "Sub detail" in result["text"]


class TestAddSourceFooter:
    def test_adds_annotation(self):
        fig = go.Figure(go.Bar(x=[1], y=[2]))
        result = add_source_footer(fig, client_name="Test CU", date_range="2025")
        assert len(result.layout.annotations) == 1
        assert "Test CU" in result.layout.annotations[0].text

    def test_empty_source(self):
        fig = go.Figure(go.Bar(x=[1], y=[2]))
        result = add_source_footer(fig)
        assert isinstance(result, go.Figure)
