"""Shared chart theme and export helpers.

Color authority for all pipelines. Individual packages can import these
colors to ensure visual consistency across ARS (matplotlib) and Txn/ICS (Plotly).
"""

from __future__ import annotations

from pathlib import Path

# Consultant-grade color palette (single authority)
COLORS = {
    "primary": "#2E4057",
    "secondary": "#048A81",
    "accent": "#F18F01",
    "positive": "#2D936C",
    "negative": "#C73E1D",
    "neutral": "#8B95A2",
    "light_bg": "#F7F9FC",
    "dark_text": "#2E4057",
}

CATEGORY_PALETTE = [
    "#2E4057",
    "#048A81",
    "#F18F01",
    "#2D936C",
    "#C73E1D",
    "#8B95A2",
    "#5B6770",
    "#D4A76A",
]


def save_chart_png(fig: object, path: Path, scale: int = 1) -> Path:
    """Save a chart figure to PNG. Works with both matplotlib and Plotly.

    Args:
        fig: A matplotlib Figure or Plotly Figure.
        path: Output file path.
        scale: 1 for Excel embedding, 3 for standalone/presentation.

    Returns:
        The saved file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Detect figure type
    fig_type = type(fig).__module__

    if "matplotlib" in fig_type:
        fig.savefig(str(path), dpi=150 * scale, bbox_inches="tight", facecolor="white")
        import matplotlib.pyplot as plt

        plt.close(fig)
    elif "plotly" in fig_type:
        fig.write_image(str(path), scale=scale)
    else:
        raise TypeError(f"Unsupported figure type: {type(fig)}")

    return path
