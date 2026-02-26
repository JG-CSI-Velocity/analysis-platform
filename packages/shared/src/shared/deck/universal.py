"""Universal deck builder -- converts AnalysisResult dict -> PPTX for any pipeline.

Works with any pipeline's output without requiring pipeline-specific configuration.
Groups results by category (from metadata or name prefix), adds title + section
dividers, and assembles chart slides automatically.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from shared.deck.engine import _FALLBACK_TEMPLATE, DeckBuilder, SlideContent
from shared.types import AnalysisResult

logger = logging.getLogger(__name__)

_PIPELINE_LABELS = {
    "ars": "Account Revenue Solution",
    "ics": "ICS Account Analysis",
    "txn": "Transaction Intelligence",
    "attrition": "Attrition Analysis",
}


def build_deck_from_results(
    results: dict[str, AnalysisResult],
    *,
    pipeline: str,
    client_id: str = "",
    client_name: str = "",
    output_dir: Path,
    template_path: Path | None = None,
) -> Path | None:
    """Build a PPTX deck from pipeline analysis results.

    Parameters
    ----------
    results:
        Analysis results keyed by name. Each result's ``charts`` field
        provides the PNG paths to include as slides.
    pipeline:
        Pipeline identifier (e.g. 'txn', 'ics', 'attrition').
    client_id:
        Client identifier for the title slide.
    client_name:
        Client name for the title slide.
    output_dir:
        Where to write the output PPTX.
    template_path:
        Optional PPTX template override. Falls back to the embedded template.

    Returns
    -------
    Path to the generated PPTX, or None if no charts were found.
    """
    if not results:
        logger.info("No results to build deck from")
        return None

    # Collect results that have at least one chart PNG
    chartable = {
        name: r
        for name, r in results.items()
        if r.charts and any(Path(c).exists() for c in r.charts)
    }
    if not chartable:
        logger.info("No results with chart images -- skipping deck build")
        return None

    template = template_path or _FALLBACK_TEMPLATE
    if not template.exists():
        logger.warning("Template not found: %s", template)
        return None

    # Build slides
    slides: list[SlideContent] = []

    # Title slide
    display_name = client_name or client_id or "Client"
    pipeline_label = _PIPELINE_LABELS.get(pipeline, pipeline.upper())
    today = date.today().strftime("%B %Y")
    slides.append(
        SlideContent(
            slide_type="title",
            title=f"{display_name}\n{pipeline_label} | {today}",
            layout_index=1,
        )
    )

    # Group results by category
    grouped = _group_by_category(chartable)

    # Build section dividers + chart slides for each group
    for section_label, section_results in grouped.items():
        # Section divider
        slides.append(
            SlideContent(
                slide_type="section",
                title=section_label,
                layout_index=2,
            )
        )

        # Chart slides for each result in this section
        for name, result in section_results:
            chart_paths = [str(c) for c in result.charts if Path(c).exists()]
            if not chart_paths:
                continue

            title = result.title or result.name

            if len(chart_paths) == 1:
                slides.append(
                    SlideContent(
                        slide_type="screenshot",
                        title=title,
                        images=chart_paths,
                        layout_index=9,
                    )
                )
            elif len(chart_paths) == 2:
                slides.append(
                    SlideContent(
                        slide_type="multi_screenshot",
                        title=title,
                        images=chart_paths,
                        layout_index=6,
                    )
                )
            else:
                # 3+ charts: first pair side-by-side, then singles
                slides.append(
                    SlideContent(
                        slide_type="multi_screenshot",
                        title=title,
                        images=chart_paths[:2],
                        layout_index=6,
                    )
                )
                for extra_path in chart_paths[2:]:
                    slides.append(
                        SlideContent(
                            slide_type="screenshot",
                            title=f"{title} (cont.)",
                            images=[extra_path],
                            layout_index=9,
                        )
                    )

    if len(slides) <= 1:
        logger.info("Only title slide, no chart slides to build")
        return None

    # Build the PPTX
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{client_id}_{pipeline}_deck.pptx" if client_id else f"{pipeline}_deck.pptx"
    output_path = output_dir / filename

    try:
        builder = DeckBuilder(template)
        builder.build(slides, output_path)
        logger.info("Universal deck built: %s (%d slides)", output_path.name, len(slides))
        return output_path
    except Exception as exc:
        logger.error("Universal deck build failed: %s", exc)
        return None


def _group_by_category(
    results: dict[str, AnalysisResult],
) -> dict[str, list[tuple[str, AnalysisResult]]]:
    """Group results into labeled sections for slide ordering.

    Uses metadata["category"] if present, otherwise derives from the result name.
    """
    groups: dict[str, list[tuple[str, AnalysisResult]]] = {}

    for name, result in results.items():
        category = (result.metadata or {}).get("category", "")
        if not category:
            category = _derive_category(name)
        groups.setdefault(category, []).append((name, result))

    return groups


def _derive_category(name: str) -> str:
    """Derive a human-readable category from a result name.

    Handles common naming patterns across pipelines:
    - TXN: 'top_merchants_by_spend' -> 'Merchant Analysis'
    - ICS: 'ics_distribution' -> 'ICS Distribution'
    - Attrition: 'attrition_rates' -> 'Attrition Rates'
    """
    lower = name.lower()

    # TXN patterns
    if "merchant" in lower:
        return "Merchant Analysis"
    if "spend" in lower and "merchant" not in lower:
        return "Spend Patterns"
    if "velocity" in lower or "trend" in lower or "monthly" in lower:
        return "Trends"
    if "segment" in lower or "tier" in lower:
        return "Segments"
    if "generation" in lower or "demographic" in lower or "age" in lower:
        return "Demographics"
    if "balance" in lower:
        return "Balance Analysis"
    if "scorecard" in lower:
        return "Scorecard"
    if "competitor" in lower:
        return "Competitor Analysis"

    # ICS patterns
    if "distribution" in lower:
        return "Distribution"
    if "source" in lower or "referral" in lower:
        return "Source Analysis"
    if "activity" in lower:
        return "Activity"
    if "portfolio" in lower:
        return "Portfolio"

    # Attrition patterns
    if "attrition" in lower or "closure" in lower:
        return "Attrition"
    if "retention" in lower:
        return "Retention"
    if "revenue" in lower or "impact" in lower:
        return "Revenue Impact"

    # Fallback: capitalize the first word
    parts = name.replace("_", " ").strip().split()
    if parts:
        return parts[0].title()
    return "Analysis"
