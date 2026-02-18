"""High-level PPTX report orchestrator using DeckBuilder."""

import logging
import tempfile
from datetime import datetime
from pathlib import Path

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.settings import AnalysisSettings as Settings

logger = logging.getLogger(__name__)

# Maps analysis name -> section grouping for slide organization.
# Executive Summary first for the presentation narrative flow.
SECTION_MAP = {
    "Executive Summary": [
        "Executive Summary",
    ],
    "Summary": [
        "Total ICS Accounts",
        "Open ICS Accounts",
        "ICS by Stat Code",
        "Product Code Distribution",
        "Debit Distribution",
        "Debit x Prod Code",
        "Debit x Branch",
    ],
    "Portfolio Health": [
        "Engagement Decay",
        "Net Portfolio Growth",
        "Spend Concentration",
    ],
    "Source Analysis": [
        "Source Distribution",
        "Source x Stat Code",
        "Source x Prod Code",
        "Source x Branch",
        "Account Type",
        "Source by Year",
    ],
    "Demographics": [
        "Age Comparison",
        "Closures",
        "Open vs Close",
        "Balance Tiers",
        "Stat Open Close",
        "Age vs Balance",
        "Balance Tier Detail",
        "Age Distribution",
    ],
    "Activity Analysis": [
        "L12M Activity Summary",
        "Activity by Debit+Source",
        "Activity by Balance",
        "Activity by Branch",
        "Monthly Trends",
    ],
    "Cohort Analysis": [
        "Cohort Activation",
        "Cohort Heatmap",
        "Cohort Milestones",
        "Activation Summary",
        "Growth Patterns",
        "Activation Personas",
        "Branch Activation",
    ],
    "Performance": [
        "Days to First Use",
        "Branch Performance Index",
    ],
    "Strategic Insights": [
        "Activation Funnel",
        "Revenue Impact",
    ],
}


def _build_analysis_lookup(analyses: list[AnalysisResult]) -> dict[str, AnalysisResult]:
    """Build a name -> result lookup for successful analyses."""
    return {a.name: a for a in analyses if a.error is None}


def write_pptx_report(
    settings: Settings,
    analyses: list[AnalysisResult],
    charts: dict | None = None,
    chart_pngs: dict[str, bytes] | None = None,
    output_path: Path | None = None,
) -> Path:
    """Build and save a PPTX presentation.

    Args:
        chart_pngs: Pre-rendered PNG bytes keyed by analysis name.
            If provided, charts arg is ignored (avoids double-rendering).
        charts: Plotly figure dict (legacy; rendered on the fly if chart_pngs not given).

    Returns the path to the generated file.
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = settings.output_dir / f"ICS_Analysis_{timestamp}.pptx"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    lookup = _build_analysis_lookup(analyses)
    if chart_pngs is None:
        chart_pngs = _render_chart_pngs(charts, settings) if charts else {}

    try:
        from ics_toolkit.analysis.exports.deck_builder import (  # noqa: F401
            DeckBuilder,
            SlideContent,
        )

        _build_with_deck_builder(
            settings,
            lookup,
            chart_pngs,
            output_path,
        )
    except ImportError:
        logger.warning("DeckBuilder not available; building simple PPTX")
        _build_simple_pptx(settings, lookup, chart_pngs, output_path)

    logger.info("PPTX report saved: %s", output_path)
    return output_path


def _render_chart_pngs(charts: dict, settings: Settings) -> dict[str, bytes]:
    """Render all charts to PNG bytes."""
    pngs: dict[str, bytes] = {}
    try:
        from ics_toolkit.analysis.charts import render_chart_png

        for name, fig in charts.items():
            try:
                pngs[name] = render_chart_png(fig, settings.charts)
            except Exception as e:
                logger.warning("Chart PNG for '%s' failed: %s", name, e)
    except ImportError:
        logger.warning("kaleido not available; skipping chart PNGs")
    return pngs


def _save_pngs_to_tempdir(
    chart_pngs: dict[str, bytes],
    tmp_dir: Path,
) -> dict[str, str]:
    """Save chart PNG bytes to temp files, return name -> file path mapping."""
    paths: dict[str, str] = {}
    for name, png_bytes in chart_pngs.items():
        safe_name = name.replace(" ", "_").replace("/", "_").replace("+", "")
        path = tmp_dir / f"{safe_name}.png"
        path.write_bytes(png_bytes)
        paths[name] = str(path)
    return paths


def _build_with_deck_builder(
    settings: Settings,
    lookup: dict[str, AnalysisResult],
    chart_pngs: dict[str, bytes],
    output_path: Path,
) -> None:
    """Build PPTX using the full DeckBuilder with CSI templates."""
    from ics_toolkit.analysis.exports.deck_builder import DeckBuilder, SlideContent
    from ics_toolkit.analysis.exports.kpi_slides import (
        build_executive_kpi_slide,
        build_narrative_slide,
        generate_declarative_title,
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        png_paths = _save_pngs_to_tempdir(chart_pngs, Path(tmp_dir))

        slides: list[SlideContent] = []

        # Title slide
        slides.append(
            SlideContent(
                slide_type="title",
                title="ICS Accounts Analysis",
                kpis={
                    "subtitle": settings.client_name or f"Client {settings.client_id}",
                },
                layout_index=1,
            )
        )

        # Section slides with their analyses
        for section_name, analysis_names in SECTION_MAP.items():
            section_analyses = [(name, lookup[name]) for name in analysis_names if name in lookup]
            if not section_analyses:
                continue

            slides.append(
                SlideContent(
                    slide_type="section",
                    title=section_name,
                    layout_index=2,
                )
            )

            for name, analysis in section_analyses:
                # Executive Summary gets KPI + narrative slides
                if name == "Executive Summary":
                    kpi_slide = build_executive_kpi_slide(analysis)
                    if kpi_slide:
                        slides.append(kpi_slide)
                    narrative_slide = build_narrative_slide(analysis)
                    if narrative_slide:
                        slides.append(narrative_slide)
                    continue

                img_path = png_paths.get(name)
                if img_path:
                    title = generate_declarative_title(analysis)
                    slides.append(
                        SlideContent(
                            slide_type="screenshot",
                            title=title,
                            images=[img_path],
                            layout_index=5,
                        )
                    )

        builder = DeckBuilder(template_path=settings.pptx_template)
        builder.build(slides, output_path)


def _build_simple_pptx(
    settings: Settings,
    lookup: dict[str, AnalysisResult],
    chart_pngs: dict[str, bytes],
    output_path: Path,
) -> None:
    """Fallback: build a basic PPTX without DeckBuilder."""
    from io import BytesIO

    from pptx import Presentation
    from pptx.util import Inches, Pt

    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # Title slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = "ICS Accounts Analysis"
    slide.placeholders[1].text = settings.client_name or f"Client {settings.client_id}"

    # Add chart slides
    blank_layout = prs.slide_layouts[6]
    for section_name, analysis_names in SECTION_MAP.items():
        for name in analysis_names:
            if name not in lookup:
                continue

            png = chart_pngs.get(name)
            if not png:
                continue

            slide = prs.slides.add_slide(blank_layout)
            txBox = slide.shapes.add_textbox(
                Inches(0.5),
                Inches(0.3),
                Inches(12),
                Inches(0.6),
            )
            txBox.text_frame.paragraphs[0].text = lookup[name].title
            txBox.text_frame.paragraphs[0].font.size = Pt(18)
            txBox.text_frame.paragraphs[0].font.bold = True

            slide.shapes.add_picture(
                BytesIO(png),
                Inches(1.5),
                Inches(1.2),
                Inches(10),
                Inches(5.5),
            )

    prs.save(str(output_path))
