"""M6: Competitor analysis charts (matplotlib)."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import ACCENT, COLORS, CORAL, GRAY_BASE, TEAL, set_insight_title
from txn_analysis.settings import ChartConfig

# Navy sequential colorscale for heatmaps
_NAVY_CMAP_COLORS = ["#E8E8E8", "#B0C4DE", "#6699CC", "#005EB8", "#051C2C"]


def chart_threat_scatter(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Competitor threat scatter: penetration vs spend, sized by growth."""
    df = result.df
    if df.empty:
        return Figure()

    y_col = "total_spend" if "total_spend" in df.columns else "threat_score"

    with chart_figure(figsize=(10, 6)) as (fig, ax):
        sizes = [max(30, min(400, abs(g) * 10 + 50)) for g in df["growth_rate"]]
        scatter = ax.scatter(
            df["penetration_pct"],
            df[y_col],
            s=sizes,
            c=df["threat_score"],
            cmap="Blues",
            alpha=0.8,
            edgecolors="white",
            linewidth=0.5,
        )
        fig.colorbar(scatter, ax=ax, label="Threat Score", fraction=0.03, pad=0.04)

        # Text labels
        for _, row in df.iterrows():
            ax.annotate(
                str(row["competitor"]),
                xy=(row["penetration_pct"], row[y_col]),
                xytext=(0, 8),
                textcoords="offset points",
                fontsize=8,
                ha="center",
                va="bottom",
            )

        # Quadrant labels
        quadrants = [
            (0.02, 0.98, "Monitor", "#888888", "left", "top"),
            (0.98, 0.98, "High Threat", CORAL, "right", "top"),
            (0.02, 0.02, "Low Priority", GRAY_BASE, "left", "bottom"),
            (0.98, 0.02, "Watch", ACCENT, "right", "bottom"),
        ]
        for qx, qy, label, color, ha, va in quadrants:
            ax.text(
                qx,
                qy,
                label,
                transform=ax.transAxes,
                fontsize=10,
                color=color,
                ha=ha,
                va=va,
                alpha=0.6,
            )

        ax.set_xlabel("Account Penetration (%)", fontsize=10)
        ax.set_ylabel("Threat Score", fontsize=10)
        set_insight_title(ax, "Competitor Threat Assessment")
        fig.tight_layout()

    return fig


def chart_segmentation_bar(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Competitor account segmentation stacked horizontal bar."""
    df = result.df
    if df.empty:
        return Figure()

    segment_colors = {
        "Heavy": CORAL,
        "Balanced": ACCENT,
        "CU-Focused": TEAL,
    }

    with chart_figure(figsize=(10, 6)) as (fig, ax):
        # Get unique competitors
        comp_col = "competitor" if "competitor" in df.columns else None
        if comp_col is None:
            competitors = df.index.unique().tolist()
        else:
            competitors = df[comp_col].unique().tolist()

        y_pos = np.arange(len(competitors))
        left = np.zeros(len(competitors))

        for segment in ["Heavy", "Balanced", "CU-Focused"]:
            seg_data = df[df["segment"] == segment]
            if seg_data.empty:
                continue

            if comp_col:
                values = [
                    seg_data.loc[seg_data[comp_col] == c, "account_count"].sum()
                    for c in competitors
                ]
            else:
                values = [
                    seg_data.loc[seg_data.index == c, "account_count"].sum()
                    for c in competitors
                ]

            color = segment_colors.get(segment, GRAY_BASE)
            ax.barh(y_pos, values, left=left, color=color, label=segment, height=0.6)
            left += np.array(values)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(competitors, fontsize=9)
        ax.set_xlabel("Account Count", fontsize=10)
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=3,
            frameon=False,
        )
        set_insight_title(ax, "Competitor Account Segmentation")
        fig.tight_layout()

    return fig


def chart_competitor_heatmap(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Top 20 competitor spend heatmap by category."""
    df = result.df
    if df.empty:
        return Figure()

    if "category" not in df.columns or "pct_of_competitor_spend" not in df.columns:
        return Figure()

    if "competitor" not in df.columns:
        return Figure()

    pivot = df.pivot_table(
        index="competitor",
        columns="category",
        values="pct_of_competitor_spend",
        fill_value=0,
    )

    n_rows = len(pivot)
    n_cols = len(pivot.columns)
    fig_height = max(4, n_rows * 0.4 + 2)

    with chart_figure(figsize=(max(8, n_cols * 0.8 + 4), fig_height)) as (fig, ax):
        im = ax.imshow(pivot.values, cmap="Blues", aspect="auto")
        fig.colorbar(im, ax=ax, label="% of Spend", fraction=0.03, pad=0.04)

        ax.set_xticks(np.arange(n_cols))
        ax.set_yticks(np.arange(n_rows))
        ax.set_xticklabels(pivot.columns.tolist(), fontsize=8, rotation=-45, ha="right")
        ax.set_yticklabels(pivot.index.tolist(), fontsize=9)

        # Text annotations
        vmax = pivot.values.max() if pivot.values.size > 0 else 1
        for row_idx in range(n_rows):
            for col_idx in range(n_cols):
                val = pivot.values[row_idx, col_idx]
                text_color = "white" if val > vmax * 0.6 else COLORS["dark_text"]
                ax.text(
                    col_idx,
                    row_idx,
                    f"{val:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=text_color,
                )

        set_insight_title(ax, "Competitor Spend by Category")
        fig.tight_layout()

    return fig
