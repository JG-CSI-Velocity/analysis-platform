"""PowerPoint deck builder -- generate presentation from analysis results."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from pptx import Presentation
from ars_analysis.pipeline.context import PipelineContext

# Embedded fallback template (ships with the package)
_FALLBACK_TEMPLATE = Path(__file__).parent / "template" / "Template12.25.pptx"

# Layout indices in the template
_LAYOUT_DIVIDER = 2  # Section divider: title + subtitle
_LAYOUT_CHART = 5  # Chart slide: title + picture + text area
_LAYOUT_BLANK = 11  # Blank with title only

# Placeholder indices for layout 5 (chart slide)
_PH_TITLE = 0
_PH_SUBTITLE = 13  # Content Placeholder below title
_PH_PICTURE = 14  # Picture placeholder
_PH_TEXT_HEADER = 26  # Right-side header
_PH_TEXT_BODY = 19  # Right-side body text (notes area)

# Section display names for divider slides
_SECTION_LABELS = {
    "overview": "Overview",
    "dctr": "Debit Card Transaction Revenue",
    "rege": "Regulation E",
    "attrition": "Attrition Analysis",
    "value": "Value Analysis",
    "mailer": "Mailer Analysis",
    "transaction": "Transaction Intelligence",
    "ics": "ICS Account Analysis",
    "insights": "Key Insights",
}


def build_deck(ctx: PipelineContext) -> Path | None:
    """Build a PowerPoint deck from analysis results.

    Uses the ARS template with chart images inserted into slide layouts.
    Returns the output path, or None if no slides were generated.
    """
    if not ctx.all_slides:
        logger.warning("No slides to build deck from")
        return None

    # Resolve template: settings path > embedded fallback
    template = _FALLBACK_TEMPLATE
    if ctx.settings and hasattr(ctx.settings, "paths"):
        cfg_template = getattr(ctx.settings.paths, "template_path", None)
        if cfg_template and Path(cfg_template).exists():
            template = Path(cfg_template)

    if not template.exists():
        logger.warning("Template not found: {name}", name=template.name)
        return None

    prs = Presentation(str(template))

    # Group slides by section
    sections = _group_by_section(ctx.all_slides)

    slides_added = 0
    for section_key, results in sections.items():
        # Add section divider
        section_label = _SECTION_LABELS.get(section_key, section_key.upper())
        _add_divider_slide(prs, section_label, f"{len(results)} analyses")

        # Add individual analysis slides
        for result in results:
            if not getattr(result, "success", True):
                continue

            chart_path = getattr(result, "chart_path", None)
            if chart_path and Path(chart_path).exists():
                _add_chart_slide(prs, result)
                slides_added += 1
            else:
                _add_text_slide(prs, result)
                slides_added += 1

    if slides_added == 0:
        logger.warning("No chart or data slides to add to deck")
        return None

    # Save
    ctx.paths.pptx_dir.mkdir(parents=True, exist_ok=True)
    output_path = ctx.paths.pptx_dir / f"{ctx.client.client_id}_{ctx.client.month}_deck.pptx"
    prs.save(str(output_path))
    ctx.export_log.append(str(output_path))
    logger.info(
        "Deck built: {path} ({n} slides)",
        path=output_path.name,
        n=slides_added,
    )
    return output_path


def _group_by_section(slides: list) -> dict[str, list]:
    """Group AnalysisResults by section inferred from slide_id prefix."""
    sections: dict[str, list] = {}
    section_map = {
        "a1": "overview", "a2": "overview", "a3": "overview",
        "a7": "dctr", "dctr": "dctr",
        "a8": "rege", "rege": "rege",
        "a9": "attrition", "att": "attrition",
        "a10": "value", "val": "value",
        "a11": "mailer", "mail": "mailer",
        "ics": "ics",
        "txn": "transaction", "m1": "transaction", "m2": "transaction",
        "m3": "transaction", "m4": "transaction", "m5": "transaction",
        "m6": "transaction", "m7": "transaction",
        "s1": "insights", "s2": "insights", "s3": "insights",
        "s4": "insights", "s5": "insights", "s6": "insights",
        "s7": "insights", "s8": "insights",
    }

    for slide in slides:
        sid = getattr(slide, "slide_id", "")
        prefix = sid.split("-")[0].split(".")[0].lower() if sid else "other"
        section = section_map.get(prefix, prefix)
        sections.setdefault(section, []).append(slide)

    return sections


def _add_divider_slide(prs: Presentation, title: str, subtitle: str) -> None:
    """Add a section divider slide."""
    layout = prs.slide_layouts[_LAYOUT_DIVIDER]
    slide = prs.slides.add_slide(layout)

    for ph in slide.placeholders:
        if ph.placeholder_format.idx == _PH_TITLE:
            ph.text = title
        elif ph.placeholder_format.idx == _PH_SUBTITLE:
            ph.text = subtitle


def _add_chart_slide(prs: Presentation, result) -> None:
    """Add a chart slide with image in the picture placeholder."""
    layout = prs.slide_layouts[_LAYOUT_CHART]
    slide = prs.slides.add_slide(layout)

    title = getattr(result, "title", "")
    slide_id = getattr(result, "slide_id", "")
    chart_path = str(result.chart_path)
    notes = getattr(result, "notes", "")

    for ph in slide.placeholders:
        idx = ph.placeholder_format.idx
        if idx == _PH_TITLE:
            ph.text = title
        elif idx == _PH_SUBTITLE:
            ph.text = slide_id
        elif idx == _PH_PICTURE:
            ph.insert_picture(chart_path)
        elif idx == _PH_TEXT_HEADER:
            ph.text = slide_id
        elif idx == _PH_TEXT_BODY:
            ph.text = notes if notes else ""

    # Add notes to the notes section
    if notes:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = f"{slide_id}: {title}\n\n{notes}"


def _add_text_slide(prs: Presentation, result) -> None:
    """Add a text-only slide for results without charts."""
    layout = prs.slide_layouts[_LAYOUT_BLANK]
    slide = prs.slides.add_slide(layout)

    title = getattr(result, "title", "")
    slide_id = getattr(result, "slide_id", "")
    notes = getattr(result, "notes", "")

    for ph in slide.placeholders:
        if ph.placeholder_format.idx == _PH_TITLE:
            ph.text = f"{slide_id}: {title}"

    # Add notes
    if notes:
        notes_slide = slide.notes_slide
        notes_slide.notes_text_frame.text = notes

    # Add a text box with summary info if there's excel data
    excel_data = getattr(result, "excel_data", None)
    if excel_data:
        # Add summary text box
        from pptx.util import Inches, Pt
        txBox = slide.shapes.add_textbox(
            Inches(1), Inches(2), Inches(10), Inches(4),
        )
        tf = txBox.text_frame
        tf.word_wrap = True
        for sheet_name, df in excel_data.items():
            p = tf.add_paragraph()
            p.text = f"{sheet_name}: {len(df)} rows x {len(df.columns)} columns"
            p.font.size = Pt(14)
