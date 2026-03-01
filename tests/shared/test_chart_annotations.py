"""Tests for shared chart annotation utilities."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from shared.chart_annotations import (
    add_bar_labels,
    add_comparison_callout,
    directional_color,
    emphasis_colors,
    label_line_ends,
)


class TestAddBarLabels:
    def test_labels_added(self):
        fig, ax = plt.subplots()
        bars = ax.bar([0, 1, 2], [0.3, 0.5, 0.1])
        add_bar_labels(ax, bars, [0.3, 0.5, 0.1])
        texts = [t.get_text() for t in ax.texts]
        assert "30.0%" in texts
        assert "50.0%" in texts
        plt.close(fig)

    def test_custom_format(self):
        fig, ax = plt.subplots()
        bars = ax.bar([0], [100])
        add_bar_labels(ax, bars, [100], fmt="{:.0f}")
        assert ax.texts[0].get_text() == "100"
        plt.close(fig)


class TestLabelLineEnds:
    def test_labels_at_endpoints(self):
        fig, ax = plt.subplots()
        (line,) = ax.plot([0, 1, 2], [10, 20, 30])
        label_line_ends(ax, [line], ["Series A"])
        assert len(ax.texts) == 1
        assert ax.texts[0].get_text() == "Series A"
        plt.close(fig)

    def test_empty_line(self):
        fig, ax = plt.subplots()
        (line,) = ax.plot([], [])
        label_line_ends(ax, [line], ["Empty"])
        assert len(ax.texts) == 0
        plt.close(fig)


class TestAddComparisonCallout:
    def test_positive(self):
        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        artist = add_comparison_callout(ax, 4.0, 5, 5)
        assert "+4.0pp" in artist.get_text()
        plt.close(fig)

    def test_negative_color(self):
        fig, ax = plt.subplots()
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        artist = add_comparison_callout(ax, -2.5, 5, 5)
        assert "-2.5pp" in artist.get_text()
        plt.close(fig)


class TestEmphasisColors:
    def test_hero_at_index(self):
        colors = emphasis_colors(5, hero_index=2)
        assert colors[2] == "#2E4057"
        assert all(c == "#D5D8DC" for i, c in enumerate(colors) if i != 2)

    def test_single_bar(self):
        colors = emphasis_colors(1, hero_index=0)
        assert colors == ["#2E4057"]

    def test_custom_colors(self):
        colors = emphasis_colors(3, hero_index=0, hero="red", muted="gray")
        assert colors == ["red", "gray", "gray"]


class TestDirectionalColor:
    def test_positive(self):
        assert directional_color(5.0) == "#2D936C"

    def test_negative(self):
        assert directional_color(-3.0) == "#C73E1D"

    def test_neutral(self):
        assert directional_color(0.0) == "#8B95A2"

    def test_custom_thresholds(self):
        assert directional_color(0.5, threshold_good=1.0, threshold_bad=-1.0) == "#8B95A2"
        assert directional_color(1.5, threshold_good=1.0, threshold_bad=-1.0) == "#2D936C"
        assert directional_color(-2.0, threshold_good=1.0, threshold_bad=-1.0) == "#C73E1D"
