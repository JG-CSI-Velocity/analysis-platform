"""M5: Merchant trend charts (matplotlib)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import (
    ACCENT,
    ACCENT_SECONDARY,
    CORAL,
    GRAY_BASE,
    TEAL,
    set_insight_title,
)
from txn_analysis.settings import ChartConfig


def chart_rank_trajectory(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Monthly rank trajectory: top 3 colored, rest gray with direct labels."""
    df = result.df
    if df.empty:
        return Figure()

    month_cols = [c for c in df.columns if len(c) == 7 and c[4:5] == "-"]
    if not month_cols:
        return Figure()

    with chart_figure(figsize=(12, 6)) as (fig, ax):
        top_merchants = df.head(10)
        accent_colors = [ACCENT, CORAL, TEAL]

        for idx, (_, row) in enumerate(top_merchants.iterrows()):
            name = row["merchant_consolidated"]
            ranks = [row[m] if row[m] > 0 else np.nan for m in month_cols]
            is_top3 = idx < 3

            color = accent_colors[idx] if is_top3 else GRAY_BASE
            lw = 2.5 if is_top3 else 1
            alpha = 1.0 if is_top3 else 0.4

            ax.plot(
                month_cols,
                ranks,
                color=color,
                linewidth=lw,
                alpha=alpha,
                marker="o" if is_top3 else None,
                markersize=5 if is_top3 else 0,
            )

            # Direct label at endpoint for top 3
            if is_top3:
                for m in reversed(month_cols):
                    if row[m] > 0:
                        ax.annotate(
                            f"  {name[:20]}",
                            xy=(m, row[m]),
                            fontsize=9,
                            color=color,
                            va="center",
                        )
                        break

        ax.invert_yaxis()
        ax.set_ylabel("Rank", fontsize=11)
        ax.tick_params(axis="x", rotation=-45)
        set_insight_title(
            ax,
            "Merchant Rank Trajectory",
            f"Top 10 merchants across {len(month_cols)} months",
        )
        fig.tight_layout()

    return fig


def chart_growth_leaders(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Growth leaders and decliners as a diverging bar chart."""
    df = result.df
    if df.empty:
        return Figure()

    if "spend_change_pct" not in df.columns:
        return Figure()

    growers = df[df["spend_change_pct"] > 0].head(15)
    decliners = df[df["spend_change_pct"] < 0].tail(15)
    combined = pd.concat([growers, decliners]).sort_values("spend_change_pct")
    n = len(combined)

    if n == 0:
        return Figure()

    row_height = 0.35
    fig_height = max(4, n * row_height + 1.5)

    with chart_figure(figsize=(10, fig_height)) as (fig, ax):
        labels = combined["merchant_consolidated"].tolist()
        values = combined["spend_change_pct"].tolist()
        colors = [ACCENT if v >= 0 else CORAL for v in values]

        y_pos = np.arange(n)
        ax.barh(y_pos, values, color=colors, height=0.6)

        for i, val in enumerate(values):
            offset = 4 if val >= 0 else -4
            ha = "left" if val >= 0 else "right"
            ax.annotate(
                f"{val:+.1f}%",
                xy=(val, i),
                xytext=(offset, 0),
                textcoords="offset points",
                fontsize=8,
                ha=ha,
                va="center",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.axvline(x=0, color="#CCCCCC", linewidth=0.8)
        ax.set_xlabel("Spend Change %", fontsize=10)

        n_growers = len(growers)
        n_decliners = len(decliners)
        set_insight_title(
            ax,
            f"{n_growers} growing, {n_decliners} declining merchants",
            "Month-over-month spend change",
        )
        fig.tight_layout()

    return fig


def chart_cohort_summary(result: AnalysisResult, config: ChartConfig) -> Figure:
    """New vs declining merchants grouped bar by month."""
    df = result.df
    if df.empty:
        return Figure()

    month_col = "year_month" if "year_month" in df.columns else "month"
    cohort_cols = [c for c in df.columns if c not in (month_col,)]
    colors_map = {
        "new_merchants": ACCENT,
        "lost_merchants": CORAL,
        "returning_merchants": ACCENT_SECONDARY,
    }

    with chart_figure(figsize=(10, 5)) as (fig, ax):
        x = np.arange(len(df))
        n_bars = len(cohort_cols)
        total_width = 0.7
        bar_width = total_width / max(n_bars, 1)

        for idx, col in enumerate(cohort_cols):
            if col in df.columns:
                offset = (idx - n_bars / 2 + 0.5) * bar_width
                color = colors_map.get(col, GRAY_BASE)
                ax.bar(
                    x + offset,
                    df[col],
                    width=bar_width,
                    color=color,
                    label=col.replace("_", " ").title(),
                )

        ax.set_xticks(x)
        ax.set_xticklabels(df[month_col].tolist(), rotation=-45, ha="right", fontsize=9)
        ax.set_ylabel("Count", fontsize=10)
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=min(n_bars, 4),
            frameon=False,
        )
        set_insight_title(ax, "New vs Declining Merchants by Month")
        fig.tight_layout()

    return fig
