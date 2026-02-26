"""Shared lollipop chart builder using matplotlib.

Replaces the Plotly version with a clean matplotlib implementation:
- ax.hlines() for stems
- ax.scatter() for dots
- ax.annotate() for value labels

Top N items get accent color, rest get gray.
"""

from __future__ import annotations

from matplotlib.figure import Figure

from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import ACCENT, GRAY_BASE, set_insight_title
from txn_analysis.settings import ChartConfig


def _fmt(val: float | int, fmt_spec: str) -> str:
    """Format a value with support for $ prefix and % suffix in format specs."""
    prefix = ""
    if fmt_spec.startswith("$"):
        prefix = "$"
        fmt_spec = fmt_spec[1:]
    return f"{prefix}{float(val):{fmt_spec}}"


def lollipop_chart(
    labels: list[str],
    values: list[float],
    title: str,
    config: ChartConfig,
    value_format: str = "$,.0f",
    top_n: int = 25,
    accent_n: int = 3,
    subtitle: str = "",
) -> Figure:
    """Create a horizontal lollipop chart for top-N ranked data.

    Uses hlines + scatter for a clean consultant-grade look.
    """
    labels = labels[:top_n]
    values = values[:top_n]
    n = len(labels)
    if n == 0:
        return Figure()

    accent_n = min(accent_n, n)

    # Reverse so #1 is at top
    labels = list(reversed(labels))
    values = list(reversed(values))

    # Color array: last accent_n (visually top) get accent, rest gray
    colors = [GRAY_BASE] * (n - accent_n) + [ACCENT] * accent_n

    row_height = 0.35
    fig_height = max(4, n * row_height + 1.5)

    with chart_figure(figsize=(10, fig_height)) as (fig, ax):
        y_positions = list(range(n))

        # Stems
        ax.hlines(
            y=y_positions,
            xmin=0,
            xmax=values,
            color=GRAY_BASE,
            linewidth=1.5,
        )

        # Dots
        ax.scatter(values, y_positions, color=colors, s=80, zorder=5)

        # Value labels
        max_val = max(values) if values else 1
        for i, (val, label) in enumerate(zip(values, labels)):
            ax.annotate(
                _fmt(val, value_format),
                xy=(val, i),
                xytext=(max_val * 0.02, 0),
                textcoords="offset points",
                fontsize=9,
                color="#333333",
                va="center",
            )

        ax.set_yticks(y_positions)
        ax.set_yticklabels(labels, fontsize=9, color="#555555")
        ax.set_xlim(left=0)
        ax.xaxis.set_visible(False)

        set_insight_title(ax, title, subtitle)
        fig.tight_layout()

    return fig
