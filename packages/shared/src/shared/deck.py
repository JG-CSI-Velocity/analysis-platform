"""Shared PPTX deck builder helpers.

Extracts the duplicated _report, _fig, _save_chart, _slide, _save
pattern from ars_analysis-jupyter modules into a single location.
"""

from __future__ import annotations

from typing import Any

from shared.context import PipelineContext


def report(ctx: PipelineContext, msg: str) -> None:
    """Print progress and notify Streamlit callback if set."""
    print(msg)
    if ctx.progress_callback:
        ctx.progress_callback(msg)


def add_slide(
    ctx: PipelineContext,
    slide_id: str,
    data: dict[str, Any],
    category: str = "General",
) -> None:
    """Append a slide entry to the context's slide list."""
    ctx.all_slides.append(
        {
            "id": slide_id,
            "category": category,
            "data": data,
            "include": True,
        }
    )
