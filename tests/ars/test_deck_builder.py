"""Tests for ars_analysis.deck_builder -- SlideContent, helpers, and DeckBuilder."""

import matplotlib.pyplot as plt
import pytest

from ars_analysis.deck_builder import (
    DECK_CONFIG,
    SlideContent,
    apply_matplotlib_defaults,
    make_figure,
    setup_slide_helpers,
)


class TestDeckConfig:
    def test_has_required_keys(self):
        for key in ("dpi", "layout_title", "layout_section", "layout_chart", "positioning"):
            assert key in DECK_CONFIG, f"Missing key: {key}"

    def test_layout_chart_is_list(self):
        assert isinstance(DECK_CONFIG["layout_chart"], list)
        assert len(DECK_CONFIG["layout_chart"]) >= 1


class TestSlideContent:
    def test_minimal(self):
        sc = SlideContent(slide_type="title", title="Test")
        assert sc.slide_type == "title"
        assert sc.title == "Test"
        assert sc.images is None
        assert sc.kpis is None
        assert sc.bullets is None
        assert sc.layout_index == 5

    def test_with_all_fields(self):
        sc = SlideContent(
            slide_type="screenshot_kpi",
            title="Chart",
            images=["/tmp/test.png"],
            kpis={"Total": "100"},
            bullets=["Point 1"],
            layout_index=4,
        )
        assert sc.images == ["/tmp/test.png"]
        assert sc.kpis == {"Total": "100"}
        assert sc.layout_index == 4

    def test_valid_slide_types(self):
        for st in ("title", "section", "screenshot", "screenshot_kpi",
                    "multi_screenshot", "summary", "blank"):
            sc = SlideContent(slide_type=st, title="test")
            assert sc.slide_type == st


class TestMakeFigure:
    def test_single(self):
        fig, ax = make_figure("single")
        w, h = fig.get_size_inches()
        assert w == DECK_CONFIG["fig_single"][0]
        assert h == DECK_CONFIG["fig_single"][1]
        plt.close(fig)

    def test_double(self):
        fig, ax = make_figure("double")
        w, h = fig.get_size_inches()
        assert w == DECK_CONFIG["fig_double"][0]
        plt.close(fig)

    def test_default(self):
        fig, ax = make_figure()
        plt.close(fig)

    def test_unknown_falls_back(self):
        fig, ax = make_figure("nonexistent_type")
        plt.close(fig)


class TestApplyMatplotlibDefaults:
    def test_sets_rcparams(self):
        apply_matplotlib_defaults()
        assert plt.rcParams["axes.spines.top"] is False
        assert plt.rcParams["axes.spines.right"] is False
        assert plt.rcParams["figure.facecolor"] == "white"


class TestSetupSlideHelpers:
    def test_returns_tuple_of_four(self, tmp_path):
        chart_dir = tmp_path / "charts"
        result = setup_slide_helpers(chart_dir)
        assert len(result) == 4
        slides, add_chart, add_section, add_multi = result
        assert isinstance(slides, list)
        assert callable(add_chart)
        assert callable(add_section)
        assert callable(add_multi)

    def test_creates_chart_dir(self, tmp_path):
        chart_dir = tmp_path / "new_charts"
        setup_slide_helpers(chart_dir)
        assert chart_dir.exists()

    def test_add_chart_slide(self, tmp_path):
        chart_dir = tmp_path / "charts"
        slides, add_chart, _, _ = setup_slide_helpers(chart_dir)
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        add_chart(fig, "test.png", "Test Chart")
        assert len(slides) == 1
        assert slides[0].slide_type == "screenshot"
        assert slides[0].title == "Test Chart"
        assert (chart_dir / "test.png").exists()

    def test_add_section(self, tmp_path):
        chart_dir = tmp_path / "charts"
        slides, _, add_section, _ = setup_slide_helpers(chart_dir)
        add_section("Overview")
        assert len(slides) == 1
        assert slides[0].slide_type == "section"
        assert slides[0].title == "Overview"

    def test_add_multi_chart_slide(self, tmp_path):
        chart_dir = tmp_path / "charts"
        slides, _, _, add_multi = setup_slide_helpers(chart_dir)
        fig1, ax1 = plt.subplots()
        fig2, ax2 = plt.subplots()
        ax1.plot([1, 2])
        ax2.plot([3, 4])
        add_multi(fig1, fig2, "left.png", "right.png", "Side by Side")
        assert len(slides) == 1
        assert slides[0].slide_type == "multi_screenshot"
        assert (chart_dir / "left.png").exists()
        assert (chart_dir / "right.png").exists()

    def test_add_chart_with_kpis(self, tmp_path):
        chart_dir = tmp_path / "charts"
        slides, add_chart, _, _ = setup_slide_helpers(chart_dir)
        fig, ax = plt.subplots()
        add_chart(fig, "kpi.png", "KPI Slide", slide_type="screenshot_kpi",
                  kpis={"Total": "500"})
        assert slides[0].slide_type == "screenshot_kpi"
        assert slides[0].kpis == {"Total": "500"}
