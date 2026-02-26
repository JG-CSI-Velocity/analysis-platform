"""Color constants, palettes, and formatting utilities for TXN charts.

All Plotly dependencies removed -- matplotlib only.
"""

from __future__ import annotations

from matplotlib.figure import Figure

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

TITLE_FONT = "Georgia"
BODY_FONT = "Arial"

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

FONT_FAMILY = "Arial"

# ---------------------------------------------------------------------------
# Title / Annotation Helpers (matplotlib)
# ---------------------------------------------------------------------------


def set_insight_title(ax, main: str, subtitle: str = "") -> None:
    """Set a two-line title: bold main + gray subtitle."""
    ax.set_title(main, fontsize=16, fontweight="bold", color=COLORS["primary"], loc="left")
    if subtitle:
        ax.text(
            0.0,
            1.02,
            subtitle,
            transform=ax.transAxes,
            fontsize=10,
            color="#8B95A2",
            va="bottom",
        )


def add_source_footer(
    fig: Figure,
    client_name: str = "",
    date_range: str = "",
) -> None:
    """Add a small source footer at the bottom-left of the figure."""
    parts = ["Source:"]
    if client_name:
        parts.append(f"{client_name} transaction data")
    if date_range:
        parts.append(f"({date_range})")

    text = " ".join(parts) if len(parts) > 1 else ""
    if not text:
        return

    fig.text(
        0.02,
        0.01,
        text,
        fontsize=8,
        color="#AAAAAA",
        ha="left",
        va="bottom",
    )


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
