"""Auto-generated speaker notes for CSM presentations.

Produces structured talking points that CSMs can read in Presenter View.
Format:
    KEY FINDING: [headline restated]
    - Supporting data point 1
    - Supporting data point 2

    TALKING POINT:
    - Suggested client conversation starters
"""

from __future__ import annotations

from typing import Any


def generate_notes(
    slide_id: str,
    headline: str,
    insights: dict[str, Any],
    kpis: dict[str, str] | None = None,
) -> str:
    """Generate speaker notes from analysis data.

    Args:
        slide_id: The slide identifier (e.g., "DCTR-1").
        headline: The conclusion headline for this slide.
        insights: Raw insights dict from ctx.results.
        kpis: Optional KPI label->value pairs displayed on the slide.

    Returns:
        Multi-line speaker notes string.
    """
    lines: list[str] = [f"KEY FINDING: {headline}", ""]

    # Pull inner insights if nested
    inner = insights.get("insights", insights) if isinstance(insights, dict) else {}

    # Add KPI supporting data
    if kpis:
        for label, value in kpis.items():
            if label.lower() not in ("subtitle", "title"):
                lines.append(f"  - {label}: {value}")
        if len(kpis) > 0:
            lines.append("")

    # Add context from notes field if available
    notes_raw = inner.get("notes", "") if isinstance(inner, dict) else ""
    if notes_raw:
        lines.append(f"CONTEXT: {notes_raw}")
        lines.append("")

    # Add standard talking points
    lines.append("TALKING POINT:")
    lines.append("  - What actions has the credit union taken on this metric since last review?")
    lines.append("  - How does this compare to their strategic goals?")

    return "\n".join(lines)
