"""Consultant-grade Plotly theme and color constants.

Single source of truth for all chart colors, fonts, and layout defaults.
Registers a 'consultant' template lazily via ensure_theme().
"""

from __future__ import annotations

import plotly.graph_objects as go

# -- Color constants (the ONE authority) ------------------------------------

NAVY = "#051C2C"
ACCENT = "#005EB8"
ACCENT_SECONDARY = "#0090D4"
TEAL = "#4ABFBF"
CORAL = "#E4573D"
GOLD = "#F3C13A"
WARM_GRAY = "#A2AAAD"
LIGHT_GRAY = "#E8E8E8"
NEAR_BLACK = "#222222"
GRAY_BASE = "#C4C4C4"

# Ordered palette for multi-series charts (consultant-safe)
PALETTE = [ACCENT, CORAL, TEAL, GOLD, ACCENT_SECONDARY, WARM_GRAY]

# -- Fonts ------------------------------------------------------------------

TITLE_FONT = "Georgia, 'Times New Roman', serif"
BODY_FONT = "Arial, Helvetica, sans-serif"

# -- Lazy template registration ---------------------------------------------

_REGISTERED = False


def ensure_theme() -> None:
    """Register the 'consultant' Plotly template (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return
    import plotly.io as pio

    pio.templates["consultant"] = _build_template()
    pio.templates.default = "consultant"
    _REGISTERED = True


def _build_template() -> go.layout.Template:
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family=BODY_FONT, size=11, color="#555555"),
            title=dict(
                font=dict(family=TITLE_FONT, size=18, color=NAVY),
                x=0.02,
                xanchor="left",
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(gridcolor=LIGHT_GRAY, gridwidth=0.5, zeroline=False),
            margin=dict(l=200, r=40, t=80, b=60),
            hoverlabel=dict(bgcolor="white", bordercolor=GRAY_BASE),
            colorway=PALETTE,
            showlegend=False,
        )
    )


# -- Annotation helpers -----------------------------------------------------


def insight_title(main: str, subtitle: str = "") -> dict:
    """Build a Plotly title dict with insight main + gray subtitle.

    Usage:
        fig.update_layout(title=insight_title("Top 5 capture 62% of spend"))
    """
    if subtitle:
        text = (
            f"{main}<br><span style='font-size:12px;"
            f"color:#888888;font-family:{BODY_FONT}'>"
            f"{subtitle}</span>"
        )
    else:
        text = main
    return dict(
        text=text,
        font=dict(family=TITLE_FONT, size=18, color=NAVY),
        x=0.02,
        xanchor="left",
    )


def add_source_footer(
    fig: go.Figure,
    client_name: str = "",
    date_range: str = "",
) -> go.Figure:
    """Add a small source footer annotation at the bottom-left of a chart."""
    parts = ["Source:"]
    if client_name:
        parts.append(f"{client_name} transaction data")
    if date_range:
        parts.append(date_range)
    text = " ".join(parts) if len(parts) > 1 else ""

    if not text:
        return fig

    fig.add_annotation(
        text=text,
        xref="paper",
        yref="paper",
        x=0,
        y=-0.12,
        showarrow=False,
        font=dict(family=BODY_FONT, size=9, color="#AAAAAA"),
        xanchor="left",
    )
    return fig
