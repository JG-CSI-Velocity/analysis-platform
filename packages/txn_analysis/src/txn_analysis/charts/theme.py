"""Consultant-grade Plotly theme, color constants, and formatting utilities.

Registers two Plotly templates:
- 'consultant': M1-M10 analysis style (Georgia serif titles, navy accents)
- 'v4_consultant': V4 storyline style (sans-serif, teal/orange accents)

Default template is 'consultant'.
"""

from __future__ import annotations

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# M1-M10 Color Constants
# ---------------------------------------------------------------------------

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

PALETTE = [ACCENT, CORAL, TEAL, GOLD, ACCENT_SECONDARY, WARM_GRAY]

# ---------------------------------------------------------------------------
# M1-M10 Fonts
# ---------------------------------------------------------------------------

TITLE_FONT = "Georgia, 'Times New Roman', serif"
BODY_FONT = "Arial, Helvetica, sans-serif"

# ---------------------------------------------------------------------------
# V4 Palettes
# ---------------------------------------------------------------------------

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
    "#C73E1D",
    "#2D936C",
    "#8B95A2",
    "#5C6B73",
    "#A23B72",
]

COMPETITOR_COLORS = {
    "big_nationals": "#C73E1D",
    "regionals": "#F18F01",
    "credit_unions": "#048A81",
    "digital_banks": "#A23B72",
    "wallets_p2p": "#5C6B73",
    "bnpl": "#8B95A2",
    "alt_finance": "#2D936C",
}

GENERATION_COLORS = {
    "Gen Z": "#A23B72",
    "Millennial": "#048A81",
    "Gen X": "#F18F01",
    "Boomer": "#2E4057",
    "Silent": "#8B95A2",
}

FONT_FAMILY = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
)

# ---------------------------------------------------------------------------
# Lazy Template Registration
# ---------------------------------------------------------------------------

_REGISTERED = False


def _build_consultant_template() -> go.layout.Template:
    """M1-M10 consultant template (Georgia serif, navy accents)."""
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


def _build_v4_template() -> go.layout.Template:
    """V4 storyline template (sans-serif, teal/orange accents)."""
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family=FONT_FAMILY, size=12, color=COLORS["dark_text"]),
            title=dict(
                font=dict(family=FONT_FAMILY, size=16, color=COLORS["primary"]),
                x=0.02,
                xanchor="left",
                pad=dict(t=8, b=12),
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                linecolor="#E0E0E0",
                showline=False,
                tickfont=dict(size=11),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#EEEEEE",
                griddash="dot",
                gridwidth=0.5,
                zeroline=False,
                showline=False,
                tickfont=dict(size=11),
            ),
            margin=dict(l=60, r=40, t=80, b=60),
            hoverlabel=dict(
                bgcolor="white",
                bordercolor="#CCCCCC",
                font=dict(size=12, family=FONT_FAMILY),
            ),
            colorway=CATEGORY_PALETTE,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font=dict(size=11),
                bgcolor="rgba(0,0,0,0)",
            ),
        )
    )


def ensure_theme() -> None:
    """Register both Plotly templates (idempotent). Default is 'consultant'."""
    global _REGISTERED
    if _REGISTERED:
        return
    import plotly.io as pio

    pio.templates["consultant"] = _build_consultant_template()
    pio.templates["v4_consultant"] = _build_v4_template()
    pio.templates.default = "consultant"
    _REGISTERED = True


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the V4 consultant theme to an existing figure."""
    ensure_theme()
    fig.update_layout(template="v4_consultant")
    return fig


# ---------------------------------------------------------------------------
# M1-M10 Annotation Helpers
# ---------------------------------------------------------------------------


def insight_title(main: str, subtitle: str = "") -> dict:
    """Build a Plotly title dict with insight main + gray subtitle."""
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
    """Add a small source footer annotation at the bottom-left."""
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


# ---------------------------------------------------------------------------
# V4 Formatting Utilities
# ---------------------------------------------------------------------------


def format_currency(value: float) -> str:
    """Format as $X.XM, $X.XK, or $X,XXX depending on magnitude."""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:,.1f}M"
    if abs_val >= 10_000:
        return f"{sign}${abs_val / 1_000:,.1f}K"
    if abs_val >= 1_000:
        return f"{sign}${abs_val:,.0f}"
    return f"{sign}${abs_val:,.2f}"


def format_pct(value: float) -> str:
    """Format as +X.X% or -X.X% with explicit sign."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def _fmt_value(val: float, fmt_spec: str) -> str:
    """Format a value using a Python format spec.

    Handles '$' prefix and suffixes after '}' (e.g. '{:.1f}%').
    """
    spec = fmt_spec
    prefix = ""
    suffix = ""
    if spec.startswith("$"):
        prefix = "$"
        spec = spec[1:]
    if spec.startswith("{:"):
        brace_idx = spec.find("}")
        if brace_idx >= 0:
            suffix = spec[brace_idx + 1 :]
            spec = spec[2:brace_idx]
    return f"{prefix}{float(val):{spec}}{suffix}"


# ---------------------------------------------------------------------------
# Export Utility
# ---------------------------------------------------------------------------


def save_chart(
    fig: go.Figure,
    path: str,
    width: int = 900,
    height: int = 500,
) -> None:
    """Save a figure as PNG for Excel embedding (scale=1)."""
    fig.write_image(path, width=width, height=height, scale=1, engine="kaleido")
