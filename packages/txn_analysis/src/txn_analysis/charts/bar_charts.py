"""Shared lollipop chart builder using Plotly (consultant style).

Replaces the original horizontal_bar() with a 2-trace lollipop design:
- Trace 1: thin horizontal stems with None separators (single trace)
- Trace 2: circle dots with color array (single trace)

Top N items get accent color, rest get gray. Insight title computed dynamically.
"""

from __future__ import annotations

import plotly.graph_objects as go

from txn_analysis.charts.theme import ACCENT, GRAY_BASE, insight_title
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
) -> go.Figure:
    """Create a horizontal lollipop chart for top-N ranked data.

    Uses exactly 2 Plotly traces regardless of item count:
    - Stems: single Scatter trace with None breaks between segments
    - Dots: single Scatter trace with per-point color array
    """
    labels = labels[:top_n]
    values = values[:top_n]
    n = len(labels)
    if n == 0:
        return go.Figure()

    accent_n = min(accent_n, n)

    # Reverse so #1 is at top
    labels = list(reversed(labels))
    values = list(reversed(values))

    # Color array: last accent_n (visually top) get accent, rest gray
    colors = [GRAY_BASE] * (n - accent_n) + [ACCENT] * accent_n

    # Build stem segments with None separators
    stem_x: list[float | None] = []
    stem_y: list[str | None] = []
    for label, val in zip(labels, values):
        stem_x.extend([0, val, None])
        stem_y.extend([label, label, None])

    fig = go.Figure()

    # Trace 1: all stems
    fig.add_trace(
        go.Scatter(
            x=stem_x,
            y=stem_y,
            mode="lines",
            line=dict(color=GRAY_BASE, width=1.5),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Trace 2: all dots with value labels
    fig.add_trace(
        go.Scatter(
            x=values,
            y=labels,
            mode="markers+text",
            marker=dict(size=10, color=colors),
            text=[_fmt(v, value_format) for v in values],
            textposition="middle right",
            textfont=dict(size=10, color="#333333"),
            showlegend=False,
            hovertemplate="%{y}: %{text}<extra></extra>",
        )
    )

    fig.update_layout(
        title=insight_title(title, subtitle),
        xaxis=dict(visible=False),
        yaxis=dict(tickfont=dict(size=10, color="#555555")),
        template=config.theme,
        width=config.width,
        height=max(config.height, n * 22),
        margin=dict(l=200, r=100, t=80, b=40),
    )

    return fig
