"""Tests for shared.charts module."""

from pathlib import Path

import pytest

from shared.charts import CATEGORY_PALETTE, COLORS, save_chart_png


class TestColorConstants:
    def test_colors_has_required_keys(self):
        for key in ("primary", "secondary", "accent", "positive", "negative", "neutral"):
            assert key in COLORS

    def test_colors_are_hex(self):
        for name, val in COLORS.items():
            assert val.startswith("#"), f"{name} is not a hex color: {val}"
            assert len(val) == 7, f"{name} has wrong length: {val}"

    def test_palette_has_entries(self):
        assert len(CATEGORY_PALETTE) >= 6


class TestSaveChartPng:
    def test_plotly_figure(self, tmp_path):
        import plotly.graph_objects as go

        fig = go.Figure(go.Bar(x=[1, 2], y=[3, 4]))
        out = tmp_path / "chart.png"
        result = save_chart_png(fig, out, scale=1)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_unsupported_type(self, tmp_path):
        with pytest.raises(TypeError, match="Unsupported figure type"):
            save_chart_png("not a figure", tmp_path / "bad.png")

    def test_creates_parent_dirs(self, tmp_path):
        import plotly.graph_objects as go

        fig = go.Figure(go.Bar(x=[1], y=[1]))
        out = tmp_path / "sub" / "dir" / "chart.png"
        save_chart_png(fig, out, scale=1)
        assert out.exists()
