"""Tests for shared.deck -- engine, universal builder, and orchestrator integration."""

from pathlib import Path
from unittest.mock import patch

import pytest

from shared.deck.engine import _FALLBACK_TEMPLATE, DeckBuilder, SlideContent
from shared.deck.universal import (
    _derive_category,
    _group_by_category,
    build_deck_from_results,
)
from shared.types import AnalysisResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chart(tmp_path: Path, name: str = "chart.png") -> Path:
    """Create a tiny valid PNG file for testing."""
    import struct
    import zlib

    def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00\xff\xff\xff")
    idat = _png_chunk(b"IDAT", raw)
    iend = _png_chunk(b"IEND", b"")

    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / name
    p.write_bytes(sig + ihdr + idat + iend)
    return p


def _result(name: str, charts: list[Path] | None = None, **kwargs) -> AnalysisResult:
    """Shorthand for creating an AnalysisResult."""
    return AnalysisResult(name=name, charts=charts or [], **kwargs)


# ---------------------------------------------------------------------------
# SlideContent dataclass
# ---------------------------------------------------------------------------


class TestSlideContent:
    def test_defaults(self):
        sc = SlideContent(slide_type="screenshot", title="Test")
        assert sc.slide_type == "screenshot"
        assert sc.title == "Test"
        assert sc.images is None
        assert sc.kpis is None
        assert sc.bullets is None
        assert sc.layout_index == 5

    def test_all_fields(self):
        sc = SlideContent(
            slide_type="screenshot_kpi",
            title="KPI Slide",
            images=["a.png"],
            kpis={"Revenue": "$1M"},
            bullets=["Point 1"],
            layout_index=9,
        )
        assert sc.images == ["a.png"]
        assert sc.kpis["Revenue"] == "$1M"
        assert sc.layout_index == 9


# ---------------------------------------------------------------------------
# DeckBuilder engine
# ---------------------------------------------------------------------------


class TestDeckBuilderEngine:
    def test_build_produces_pptx(self, tmp_path):
        out = tmp_path / "test.pptx"
        builder = DeckBuilder(_FALLBACK_TEMPLATE)
        slides = [
            SlideContent(slide_type="title", title="Hello World", layout_index=1),
            SlideContent(slide_type="section", title="Section A", layout_index=2),
            SlideContent(slide_type="blank", title="Blank", layout_index=0),
        ]
        result = builder.build(slides, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 0

    def test_build_without_template(self, tmp_path):
        out = tmp_path / "blank.pptx"
        builder = DeckBuilder(None)
        slides = [SlideContent(slide_type="blank", title="No Template", layout_index=0)]
        result = builder.build(slides, out)
        assert result == out
        assert out.exists()

    def test_screenshot_slide_with_image(self, tmp_path):
        chart = _make_chart(tmp_path)
        out = tmp_path / "img.pptx"
        builder = DeckBuilder(_FALLBACK_TEMPLATE)
        slides = [
            SlideContent(
                slide_type="screenshot",
                title="Chart Slide",
                images=[str(chart)],
                layout_index=9,
            ),
        ]
        builder.build(slides, out)
        assert out.exists()

    def test_multi_screenshot_slide(self, tmp_path):
        c1 = _make_chart(tmp_path, "c1.png")
        c2 = _make_chart(tmp_path, "c2.png")
        out = tmp_path / "multi.pptx"
        builder = DeckBuilder(_FALLBACK_TEMPLATE)
        slides = [
            SlideContent(
                slide_type="multi_screenshot",
                title="Two Charts",
                images=[str(c1), str(c2)],
                layout_index=6,
            ),
        ]
        builder.build(slides, out)
        assert out.exists()

    def test_invalid_layout_index_falls_back(self, tmp_path):
        out = tmp_path / "fallback.pptx"
        builder = DeckBuilder(_FALLBACK_TEMPLATE)
        slides = [SlideContent(slide_type="blank", title="Bad Layout", layout_index=999)]
        builder.build(slides, out)
        assert out.exists()

    def test_unknown_slide_type_skipped(self, tmp_path):
        out = tmp_path / "unknown.pptx"
        builder = DeckBuilder(_FALLBACK_TEMPLATE)
        slides = [SlideContent(slide_type="nonexistent", title="Skip Me", layout_index=0)]
        builder.build(slides, out)
        assert out.exists()

    def test_summary_slide(self, tmp_path):
        out = tmp_path / "summary.pptx"
        builder = DeckBuilder(_FALLBACK_TEMPLATE)
        slides = [
            SlideContent(
                slide_type="summary",
                title="Key Findings",
                bullets=["Point 1", "Point 2", "Point 3"],
                layout_index=0,
            ),
        ]
        builder.build(slides, out)
        assert out.exists()


# ---------------------------------------------------------------------------
# Category derivation
# ---------------------------------------------------------------------------


class TestDeriveCategory:
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("top_merchants_by_spend", "Merchant Analysis"),
            ("avg_spend_per_customer", "Spend Patterns"),
            ("monthly_velocity", "Trends"),
            ("customer_segment_breakdown", "Segments"),
            ("generation_distribution", "Demographics"),
            ("account_balance_summary", "Balance Analysis"),
            ("scorecard_summary", "Scorecard"),
            ("competitor_threat_index", "Competitor Analysis"),
            ("ics_distribution", "Distribution"),
            ("referral_source_breakdown", "Source Analysis"),
            ("activity_summary", "Activity"),
            ("portfolio_overview", "Portfolio"),
            ("attrition_by_branch", "Attrition"),
            ("closure_rate", "Attrition"),
            ("retention_rate", "Retention"),
            ("revenue_lost", "Revenue Impact"),
            ("impact_summary", "Revenue Impact"),
            ("unknown_analysis_name", "Unknown"),
        ],
    )
    def test_derive_category(self, name, expected):
        assert _derive_category(name) == expected

    def test_empty_name(self):
        assert _derive_category("") == "Analysis"


class TestGroupByCategory:
    def test_uses_metadata_category(self):
        results = {
            "a": _result("a", metadata={"category": "Custom"}),
            "b": _result("b", metadata={"category": "Custom"}),
        }
        groups = _group_by_category(results)
        assert "Custom" in groups
        assert len(groups["Custom"]) == 2

    def test_falls_back_to_name_derivation(self):
        results = {
            "top_merchants": _result("top_merchants"),
            "monthly_velocity": _result("monthly_velocity"),
        }
        groups = _group_by_category(results)
        assert "Merchant Analysis" in groups
        assert "Trends" in groups

    def test_mixed_metadata_and_derivation(self):
        results = {
            "a": _result("a", metadata={"category": "Explicit"}),
            "top_merchants": _result("top_merchants"),
        }
        groups = _group_by_category(results)
        assert "Explicit" in groups
        assert "Merchant Analysis" in groups


# ---------------------------------------------------------------------------
# Universal build_deck_from_results
# ---------------------------------------------------------------------------


class TestBuildDeckFromResults:
    def test_basic_deck(self, tmp_path):
        c1 = _make_chart(tmp_path / "charts", "c1.png")
        results = {
            "top_merchants": _result(
                "top_merchants",
                title="Top Merchants",
                charts=[c1],
            ),
        }
        out = tmp_path / "output"
        path = build_deck_from_results(
            results,
            pipeline="txn",
            client_id="1234",
            output_dir=out,
        )
        assert path is not None
        assert path.exists()
        assert "1234" in path.name
        assert "txn" in path.name

    def test_empty_results_returns_none(self, tmp_path):
        path = build_deck_from_results(
            {},
            pipeline="txn",
            output_dir=tmp_path / "out",
        )
        assert path is None

    def test_no_charts_returns_none(self, tmp_path):
        results = {"a": _result("a", title="No Charts")}
        path = build_deck_from_results(
            results,
            pipeline="txn",
            output_dir=tmp_path / "out",
        )
        assert path is None

    def test_multi_chart_result(self, tmp_path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        c1 = _make_chart(charts_dir, "c1.png")
        c2 = _make_chart(charts_dir, "c2.png")
        results = {
            "analysis": _result("analysis", title="Multi", charts=[c1, c2]),
        }
        path = build_deck_from_results(
            results,
            pipeline="ics",
            output_dir=tmp_path / "out",
        )
        assert path is not None
        assert path.exists()

    def test_three_plus_charts(self, tmp_path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        charts = [_make_chart(charts_dir, f"c{i}.png") for i in range(4)]
        results = {
            "big_analysis": _result("big_analysis", title="Many Charts", charts=charts),
        }
        path = build_deck_from_results(
            results,
            pipeline="txn",
            output_dir=tmp_path / "out",
        )
        assert path is not None
        assert path.exists()

    def test_section_grouping(self, tmp_path):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir()
        c1 = _make_chart(charts_dir, "c1.png")
        c2 = _make_chart(charts_dir, "c2.png")
        results = {
            "top_merchants": _result("top_merchants", title="Merchants", charts=[c1]),
            "monthly_velocity": _result("monthly_velocity", title="Velocity", charts=[c2]),
        }
        path = build_deck_from_results(
            results,
            pipeline="txn",
            output_dir=tmp_path / "out",
        )
        assert path is not None
        assert path.exists()

    def test_client_name_in_filename(self, tmp_path):
        c1 = _make_chart(tmp_path / "charts", "c.png")
        results = {"a": _result("a", title="A", charts=[c1])}
        path = build_deck_from_results(
            results,
            pipeline="ics",
            client_id="9999",
            client_name="Test CU",
            output_dir=tmp_path / "out",
        )
        assert path is not None
        assert "9999" in path.name

    def test_missing_template_returns_none(self, tmp_path):
        c1 = _make_chart(tmp_path / "charts", "c.png")
        results = {"a": _result("a", title="A", charts=[c1])}
        path = build_deck_from_results(
            results,
            pipeline="txn",
            output_dir=tmp_path / "out",
            template_path=tmp_path / "no_such_template.pptx",
        )
        assert path is None

    def test_nonexistent_chart_path_skipped(self, tmp_path):
        results = {
            "a": _result("a", title="A", charts=[Path("/does/not/exist.png")]),
        }
        path = build_deck_from_results(
            results,
            pipeline="txn",
            output_dir=tmp_path / "out",
        )
        assert path is None


# ---------------------------------------------------------------------------
# Template file exists
# ---------------------------------------------------------------------------


class TestTemplate:
    def test_fallback_template_exists(self):
        assert _FALLBACK_TEMPLATE.exists(), f"Template not found: {_FALLBACK_TEMPLATE}"


# ---------------------------------------------------------------------------
# Orchestrator _ensure_deck
# ---------------------------------------------------------------------------


class TestEnsureDeck:
    def test_skips_when_pptx_already_exists(self, tmp_path):
        from platform_app.orchestrator import _ensure_deck

        pptx = tmp_path / "existing.pptx"
        pptx.write_bytes(b"fake pptx")

        with patch("shared.deck.build_deck_from_results") as mock_build:
            _ensure_deck(
                {"a": _result("a")},
                "txn",
                "1234",
                "Test",
                tmp_path,
                None,
            )
            mock_build.assert_not_called()

    def test_calls_build_when_no_pptx(self, tmp_path):
        from platform_app.orchestrator import _ensure_deck

        with patch(
            "shared.deck.build_deck_from_results",
            return_value=None,
        ) as mock_build:
            _ensure_deck(
                {"a": _result("a")},
                "txn",
                "1234",
                "Test",
                tmp_path,
                None,
            )
            mock_build.assert_called_once()

    def test_noop_on_empty_results(self, tmp_path):
        from platform_app.orchestrator import _ensure_deck

        with patch("shared.deck.build_deck_from_results") as mock_build:
            _ensure_deck({}, "txn", "1234", "Test", tmp_path, None)
            mock_build.assert_not_called()
