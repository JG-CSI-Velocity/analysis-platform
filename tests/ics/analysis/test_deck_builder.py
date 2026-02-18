"""Tests for exports/deck_builder.py -- DeckBuilder and helpers."""

import pytest
from pptx import Presentation

from ics_toolkit.analysis.exports.deck_builder import (
    DECK_CONFIG,
    DeckBuilder,
    DeckConfig,
    MultiPositioning,
    PositioningConfig,
    SinglePositioning,
    SlideContent,
    create_summary_slide,
    create_title_slide,
)


class TestDeckConfig:
    def test_defaults(self):
        config = DeckConfig()
        assert config.dpi == 150
        assert config.layout_title == 1
        assert config.layout_section == 2
        assert len(config.layout_chart) == 4

    def test_module_default(self):
        assert DECK_CONFIG.dpi == 150


class TestPositioning:
    def test_single_defaults(self):
        pos = SinglePositioning()
        assert pos.left == 0.5
        assert pos.top == 2.5
        assert pos.width == 6.0

    def test_multi_defaults(self):
        pos = MultiPositioning()
        assert pos.top == 2.5

    def test_positioning_config(self):
        config = PositioningConfig()
        assert config.stacked_right.left == 5.5


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


class TestDeckBuilder:
    def test_init_no_template(self):
        builder = DeckBuilder()
        assert builder.template_path is None
        assert builder.config is DECK_CONFIG

    def test_init_with_config(self):
        config = DeckConfig(dpi=300)
        builder = DeckBuilder(config=config)
        assert builder.config.dpi == 300

    def test_build_blank_presentation(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(slide_type="title", title="Test Title", layout_index=0),
        ]
        output = tmp_path / "test.pptx"
        result = builder.build(slides, output)
        assert result == output
        assert output.exists()

    def test_build_multiple_slide_types(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(
                slide_type="title",
                title="Test Presentation",
                kpis={"subtitle": "2026-01"},
                layout_index=0,
            ),
            SlideContent(
                slide_type="section",
                title="Section 1",
                layout_index=0,
            ),
            SlideContent(
                slide_type="summary",
                title="Summary",
                bullets=["Point 1", "Point 2", "Point 3"],
                layout_index=0,
            ),
        ]
        output = tmp_path / "multi.pptx"
        builder.build(slides, output)

        prs = Presentation(str(output))
        assert len(prs.slides) == 3

    def test_build_creates_parent_dirs(self, tmp_path):
        builder = DeckBuilder()
        slides = [SlideContent(slide_type="title", title="Test", layout_index=0)]
        output = tmp_path / "sub" / "dir" / "test.pptx"
        builder.build(slides, output)
        assert output.exists()

    def test_unknown_slide_type_raises(self, tmp_path):
        builder = DeckBuilder()
        slides = [SlideContent(slide_type="invalid", title="Bad", layout_index=0)]
        with pytest.raises(ValueError, match="Unknown slide_type"):
            builder.build(slides, tmp_path / "bad.pptx")

    def test_screenshot_slide_without_image(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(
                slide_type="screenshot",
                title="No Image",
                images=["/nonexistent/path.png"],
                layout_index=0,
            ),
        ]
        output = tmp_path / "no_img.pptx"
        # Should not raise, just logs warning
        builder.build(slides, output)
        assert output.exists()

    def test_screenshot_kpi_slide(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(
                slide_type="screenshot_kpi",
                title="KPI Slide",
                kpis={"Total": "500", "Rate": "75%"},
                layout_index=0,
            ),
        ]
        output = tmp_path / "kpi.pptx"
        builder.build(slides, output)
        assert output.exists()

    def test_multi_screenshot_slide_no_images(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(
                slide_type="multi_screenshot",
                title="Multi",
                images=None,
                layout_index=0,
            ),
        ]
        output = tmp_path / "multi.pptx"
        builder.build(slides, output)
        assert output.exists()

    def test_section_with_subtitle(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(
                slide_type="section",
                title="Section\nWith subtitle",
                layout_index=0,
            ),
        ]
        output = tmp_path / "section.pptx"
        builder.build(slides, output)
        assert output.exists()

    def test_title_with_subtitle(self, tmp_path):
        builder = DeckBuilder()
        slides = [
            SlideContent(
                slide_type="title",
                title="Main Title",
                kpis={"subtitle": "Q1 2026"},
                layout_index=0,
            ),
        ]
        output = tmp_path / "titled.pptx"
        builder.build(slides, output)
        assert output.exists()


class TestPositioningHelpers:
    def test_single_positioning_layout_4(self):
        builder = DeckBuilder()
        left, top, width = builder._get_single_positioning(4)
        assert left is not None

    def test_single_positioning_layout_9(self):
        builder = DeckBuilder()
        left, top, width = builder._get_single_positioning(9)
        assert left is not None

    def test_single_positioning_layout_10(self):
        builder = DeckBuilder()
        left, top, width = builder._get_single_positioning(10)
        assert left is not None

    def test_single_positioning_layout_11(self):
        builder = DeckBuilder()
        left, top, width = builder._get_single_positioning(11)
        assert left is not None

    def test_single_positioning_default(self):
        builder = DeckBuilder()
        left, top, width = builder._get_single_positioning(99)
        assert left is not None

    def test_multi_positioning_layout_6(self):
        builder = DeckBuilder()
        result = builder._get_multi_positioning(6)
        assert len(result) == 4

    def test_multi_positioning_layout_7(self):
        builder = DeckBuilder()
        result = builder._get_multi_positioning(7)
        assert len(result) == 4

    def test_multi_positioning_default(self):
        builder = DeckBuilder()
        result = builder._get_multi_positioning(99)
        assert len(result) == 4


class TestConvenienceFactories:
    def test_create_title_slide(self):
        sc = create_title_slide("Test CU", "January 2026")
        assert sc.slide_type == "title"
        assert "Test CU" in sc.title
        assert sc.kpis["subtitle"] == "January 2026"
        assert sc.layout_index == DECK_CONFIG.layout_title

    def test_create_title_slide_custom_layout(self):
        sc = create_title_slide("CU", "Jan", layout_index=0)
        assert sc.layout_index == 0

    def test_create_summary_slide(self):
        sc = create_summary_slide(
            "Summary",
            ["A1", "A2", "A3"],
            ["B1", "B2"],
            ["C1"],
        )
        assert sc.slide_type == "summary"
        assert len(sc.bullets) == 9
        # Check interleaving: row1=[A1, B1, C1], row2=[A2, B2, ""], row3=[A3, "", ""]
        assert sc.bullets[0] == "A1"
        assert sc.bullets[1] == "B1"
        assert sc.bullets[2] == "C1"
        assert sc.bullets[3] == "A2"
        assert sc.bullets[4] == "B2"
        assert sc.bullets[5] == ""

    def test_create_summary_slide_custom_layout(self):
        sc = create_summary_slide("S", [], [], [], layout_index=11)
        assert sc.layout_index == 11
