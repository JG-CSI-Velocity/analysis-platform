"""Shared helpers for ARS analysis modules.

Extracts the 5 duplicated helper functions (_report, _fig, _save_chart,
_slide, _save) that appeared identically across dctr.py, reg_e.py,
attrition.py, value.py, and mailer modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

# Figure size presets used across all analysis modules
FIGURE_SIZES = {
    "single": (14, 8),
    "half": (7, 5),
    "wide": (16, 7),
    "square": (10, 10),
    "large": (16, 10),
    "tall": (10, 14),
}


def _report(ctx: dict, msg: str) -> None:
    """Print progress and notify callback if set."""
    print(msg)
    cb = ctx.get("_progress_callback")
    if cb:
        cb(msg)


def _fig(ctx: dict, size: str = "single") -> tuple:
    """Create a matplotlib figure with preset sizing.

    Uses ctx['_make_figure'] if available (from deck_builder),
    otherwise falls back to FIGURE_SIZES presets.
    """
    make_fn = ctx.get("_make_figure")
    if make_fn:
        return make_fn(size)
    figsize = FIGURE_SIZES.get(size, FIGURE_SIZES["single"])
    return plt.subplots(figsize=figsize)


def _save_chart(fig: Any, path: str | Path) -> str:
    """Save a matplotlib figure to PNG and close it."""
    for ax in fig.get_axes():
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(False)
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _slide(ctx: dict, slide_id: str, data: dict, category: str = "General") -> None:
    """Append a slide entry to the pipeline's all_slides list."""
    ctx["all_slides"].append({"id": slide_id, "category": category, "data": data, "include": True})


def _save(
    ctx: dict,
    df: pd.DataFrame,
    sheet: str,
    title: str,
    metrics: dict | None = None,
) -> None:
    """Export a DataFrame to the pipeline Excel workbook."""
    fn = ctx.get("_save_to_excel")
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   Export {sheet}: {e}")


def safe_run(fn: Any, ctx: dict, label: str) -> dict:
    """Run fn(ctx) with error isolation; log and continue on failure."""
    import traceback

    try:
        return fn(ctx)
    except Exception as e:
        _report(ctx, f"   {label} failed: {e}")
        traceback.print_exc()
        return ctx
