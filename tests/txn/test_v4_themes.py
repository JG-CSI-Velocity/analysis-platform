"""Tests for txn_analysis chart builders and formatting utilities."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from txn_analysis.charts.builders import (
    bullet_chart,
    donut_chart,
    grouped_bar,
    heatmap,
    horizontal_bar,
    line_trend,
    lollipop_chart,
    scatter_plot,
    stacked_bar,
    waterfall_chart,
)
from txn_analysis.charts.theme import (
    CATEGORY_PALETTE,
    COLORS,
    COMPETITOR_COLORS,
    FONT_FAMILY,
    GENERATION_COLORS,
    add_source_footer,
    format_currency,
    format_pct,
    set_insight_title,
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
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_top_n_limits(self):
        df = pd.DataFrame({"name": list("ABCDE"), "val": range(5)})
        fig = horizontal_bar(df, "val", "name", "Test", top_n=3)
        ax = fig.get_axes()[0]
        assert len(ax.patches) == 3
        plt.close(fig)

    def test_custom_color(self):
        df = pd.DataFrame({"name": ["A"], "val": [100]})
        fig = horizontal_bar(df, "val", "name", "Test", color="#FF0000")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestLollipopChart:
    def test_returns_figure(self):
        df = pd.DataFrame({"name": ["A", "B", "C"], "val": [10, 20, 30]})
        fig = lollipop_chart(df, "val", "name", "Test Lollipop")
        assert isinstance(fig, Figure)
        assert len(fig.get_axes()) > 0
        plt.close(fig)

    def test_empty_data(self):
        df = pd.DataFrame({"name": [], "val": []})
        fig = lollipop_chart(df, "val", "name", "Empty")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestLineTrend:
    def test_single_line(self):
        df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "spend": [100, 200, 150]})
        fig = line_trend(df, "month", ["spend"], "Monthly Spend")
        assert isinstance(fig, Figure)
        ax = fig.get_axes()[0]
        assert len(ax.lines) == 1
        plt.close(fig)

    def test_multiple_lines(self):
        df = pd.DataFrame({"month": ["Jan", "Feb"], "pin": [100, 200], "sig": [300, 400]})
        fig = line_trend(df, "month", ["pin", "sig"], "PIN vs SIG")
        ax = fig.get_axes()[0]
        assert len(ax.lines) == 2
        plt.close(fig)

    def test_y_format(self):
        df = pd.DataFrame({"x": [1, 2], "y": [0.5, 0.8]})
        fig = line_trend(df, "x", ["y"], "Pct", y_format=",.0%")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestStackedBar:
    def test_basic(self):
        df = pd.DataFrame({"cat": ["A", "B"], "v1": [10, 20], "v2": [30, 40]})
        fig = stacked_bar(df, "cat", ["v1", "v2"], "Stacked")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_percentage_mode(self):
        df = pd.DataFrame({"cat": ["A", "B"], "v1": [10, 20], "v2": [30, 40]})
        fig = stacked_bar(df, "cat", ["v1", "v2"], "Pct", as_percentage=True)
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestDonutChart:
    def test_returns_figure(self):
        fig = donut_chart(["A", "B", "C"], [10, 20, 30], "Composition")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_custom_hole(self):
        fig = donut_chart(["X"], [100], "Single", hole=0.6)
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestHeatmap:
    def test_returns_figure(self):
        df = pd.DataFrame({"Jan": [1, 2], "Feb": [3, 4]}, index=["A", "B"])
        fig = heatmap(df, "Monthly Heatmap")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestBulletChart:
    def test_returns_figure(self):
        fig = bullet_chart(75, 100, "Revenue")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_custom_ranges(self):
        fig = bullet_chart(50, 80, "KPI", ranges=[40, 60, 100])
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestScatterPlot:
    def test_basic(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        fig = scatter_plot(df, "x", "y", "Scatter")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_with_size_and_color(self):
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4], "sz": [10, 20], "grp": ["A", "B"]})
        fig = scatter_plot(df, "x", "y", "Bubble", size_col="sz", color_col="grp")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_with_hover(self):
        df = pd.DataFrame({"x": [1], "y": [2], "label": ["Point A"]})
        fig = scatter_plot(df, "x", "y", "Hover", hover_col="label")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestGroupedBar:
    def test_returns_figure(self):
        df = pd.DataFrame({"cat": ["A", "B"], "m1": [10, 20], "m2": [30, 40]})
        fig = grouped_bar(df, "cat", ["m1", "m2"], "Grouped")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestWaterfallChart:
    def test_returns_figure(self):
        fig = waterfall_chart(["Revenue", "Costs", "Profit"], [100, -40, 60], "Waterfall")
        assert isinstance(fig, Figure)
        plt.close(fig)

    def test_empty(self):
        fig = waterfall_chart([], [], "Empty")
        assert isinstance(fig, Figure)
        plt.close(fig)


class TestInsightTitle:
    def test_main_only(self):
        fig, ax = plt.subplots()
        try:
            set_insight_title(ax, "Top merchants")
            assert ax.get_title(loc="left") == "Top merchants"
        finally:
            plt.close(fig)

    def test_with_subtitle(self):
        fig, ax = plt.subplots()
        try:
            set_insight_title(ax, "Main", "Sub detail")
            assert ax.get_title(loc="left") == "Main"
            texts = [t.get_text() for t in ax.texts]
            assert "Sub detail" in texts
        finally:
            plt.close(fig)


class TestAddSourceFooter:
    def test_adds_text(self):
        fig, ax = plt.subplots()
        try:
            ax.bar([1], [2])
            add_source_footer(fig, client_name="Test CU", date_range="2025")
            texts = [t.get_text() for t in fig.texts]
            assert any("Test CU" in t for t in texts)
        finally:
            plt.close(fig)

    def test_empty_source(self):
        fig, ax = plt.subplots()
        try:
            ax.bar([1], [2])
            add_source_footer(fig)
            assert len(fig.texts) == 0
        finally:
            plt.close(fig)
