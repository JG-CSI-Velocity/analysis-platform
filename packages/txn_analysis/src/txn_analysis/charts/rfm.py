"""M25: RFM segmentation charts (matplotlib)."""

from __future__ import annotations

from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import chart_figure
from txn_analysis.charts.theme import (
    ACCENT,
    format_currency,
    set_insight_title,
)
from txn_analysis.settings import ChartConfig

# Segment color mapping (Champions = best -> Lost = worst)
_SEGMENT_COLORS = {
    "Champions": "#2D936C",
    "Loyal": "#048A81",
    "Potential Loyal": "#2E4057",
    "Recent": "#F18F01",
    "Need Attention": "#C73E1D",
    "At-Risk Champions": "#A23B72",
    "At-Risk": "#C73E1D",
    "About to Lose": "#8B95A2",
    "Hibernating": "#5C6B73",
    "Lost": "#AAAAAA",
}


def chart_rfm_segments(result: AnalysisResult, config: ChartConfig) -> Figure:
    """RFM segment distribution -- horizontal bars."""
    df = result.df
    if df.empty or "Segment" not in df.columns:
        return Figure()

    data = df.sort_values("Accounts", ascending=True)
    n = len(data)
    row_height = 0.4
    fig_height = max(4, n * row_height + 2)

    with chart_figure(figsize=(10, fig_height)) as (fig, ax):
        y_pos = list(range(n))
        segments = data["Segment"].tolist()
        accounts = data["Accounts"].astype(int).tolist()
        pcts = data["% of Total"].tolist()
        colors = [_SEGMENT_COLORS.get(s, ACCENT) for s in segments]

        ax.barh(y_pos, accounts, color=colors, height=0.6)

        for i, (acct, pct) in enumerate(zip(accounts, pcts)):
            ax.annotate(
                f"{acct:,} ({pct:.0f}%)",
                xy=(acct, i),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=9,
                va="center",
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(segments, fontsize=10)
        ax.xaxis.set_visible(False)

        total = result.metadata.get("total_accounts", sum(accounts))
        top_seg = segments[-1] if segments else ""
        set_insight_title(
            ax,
            f"{top_seg} dominates -- {total:,} cardholders scored",
            "RFM segments ranked by account count",
        )
        fig.tight_layout()

    return fig


def chart_rfm_heatmap(result: AnalysisResult, config: ChartConfig) -> Figure:
    """RFM heatmap: Recency x Frequency grid colored by avg monetary value."""
    heatmap_data = result.data.get("heatmap")
    if heatmap_data is None or heatmap_data.empty:
        return Figure()

    with chart_figure(figsize=(8, 7)) as (fig, ax):
        # Pivot to grid
        grid = heatmap_data.pivot_table(
            index="Recency Score",
            columns="Frequency Score",
            values="Avg Monetary",
            fill_value=0,
        )
        counts = heatmap_data.pivot_table(
            index="Recency Score",
            columns="Frequency Score",
            values="Count",
            fill_value=0,
        )

        # Sort: high recency at top
        grid = grid.sort_index(ascending=False)
        counts = counts.sort_index(ascending=False)

        im = ax.imshow(grid.values, cmap="YlGnBu", aspect="auto")

        # Annotate cells
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                val = grid.values[i, j]
                cnt = int(counts.values[i, j])
                text_color = "white" if val > grid.values.max() * 0.6 else "black"
                ax.text(
                    j,
                    i,
                    f"{format_currency(val)}\n({cnt})",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color,
                    fontweight="bold",
                )

        ax.set_xticks(range(grid.shape[1]))
        ax.set_xticklabels(grid.columns.tolist(), fontsize=10)
        ax.set_yticks(range(grid.shape[0]))
        ax.set_yticklabels(grid.index.tolist(), fontsize=10)
        ax.set_xlabel("Frequency Score", fontsize=11)
        ax.set_ylabel("Recency Score", fontsize=11)

        fig.colorbar(im, ax=ax, label="Avg Spend ($)", shrink=0.8)

        set_insight_title(
            ax,
            "RFM Heatmap -- Spend by Recency x Frequency",
            "Higher scores = more recent / more frequent | Cell = avg spend (count)",
        )
        fig.tight_layout()

    return fig
