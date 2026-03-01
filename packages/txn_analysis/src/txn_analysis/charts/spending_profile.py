"""M20 charts: spending profile summary table + tier-by-segment grouped bar."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.theme import ACCENT, CORAL, TEAL, set_insight_title
from txn_analysis.settings import ChartConfig

_TIER_COLORS = {"Low Spender": TEAL, "Medium Spender": ACCENT, "High Spender": CORAL}


def chart_spending_profile_table(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Render the spending-tier summary as a styled matplotlib table."""
    df = result.df
    if df.empty:
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(12, 2 + 0.4 * len(df)))
    ax.axis("off")

    col_labels = list(df.columns)
    cell_text = []
    for _, row in df.iterrows():
        cells = []
        for col in col_labels:
            val = row[col]
            if isinstance(val, float):
                if val >= 1_000_000:
                    cells.append(f"${val / 1_000_000:,.1f}M")
                elif val >= 1_000:
                    cells.append(f"${val:,.0f}")
                else:
                    cells.append(f"${val:,.2f}")
            else:
                cells.append(str(val))
        cell_text.append(cells)

    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    # Style header row
    for j in range(len(col_labels)):
        cell = table[0, j]
        cell.set_facecolor("#051C2C")
        cell.set_text_props(color="white", fontweight="bold")

    # Alternate row shading
    for i in range(len(cell_text)):
        for j in range(len(col_labels)):
            cell = table[i + 1, j]
            cell.set_facecolor("#F5F7FA" if i % 2 == 0 else "white")

    set_insight_title(ax, "Spending Segment Summary", f"{len(df)} tiers classified")
    fig.tight_layout()
    return fig


def chart_spending_tier_bars(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Grouped bar: tier distribution by ARS segment."""
    crosstab = result.data.get("segment_crosstab")
    if crosstab is None or (hasattr(crosstab, "empty") and crosstab.empty):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "ODD data required for segment breakdown", ha="center", va="center")
        ax.axis("off")
        return fig

    df = crosstab
    if "spending_tier" in df.columns:
        df = df.set_index("spending_tier")

    segments = [c for c in df.columns if c in ("Responder", "Non-Responder", "Control")]
    if not segments:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No segment data found", ha="center", va="center")
        ax.axis("off")
        return fig

    seg_colors = {"Responder": ACCENT, "Non-Responder": CORAL, "Control": TEAL}

    x = np.arange(len(df))
    width = 0.8 / len(segments)

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, seg in enumerate(segments):
        vals = df[seg].values if seg in df.columns else np.zeros(len(df))
        ax.bar(x + i * width, vals, width, label=seg, color=seg_colors.get(seg, "#999"))

    ax.set_xticks(x + width * (len(segments) - 1) / 2)
    ax.set_xticklabels(df.index, fontsize=10)
    ax.set_ylabel("Account Count")
    ax.legend(frameon=False)
    set_insight_title(ax, "Spending Tier by ARS Segment")
    fig.tight_layout()
    return fig
