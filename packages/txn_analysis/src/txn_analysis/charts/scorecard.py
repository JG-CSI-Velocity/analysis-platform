"""M9: Bullet chart for portfolio scorecard KPIs (matplotlib)."""

from __future__ import annotations

from matplotlib.figure import Figure

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.charts.guards import multi_axes
from txn_analysis.charts.theme import ACCENT, CORAL
from txn_analysis.settings import ChartConfig

# KPIs that have PULSE benchmarks
_BENCHMARK_KPIS = [
    "Avg Spend/Account/Month",
    "Avg Txn/Account/Month",
    "Average Ticket",
]

# Qualitative band shades (poor -> acceptable -> good)
_BAND_COLORS = ["#F0F0F0", "#E0E0E0", "#D0D0D0"]


def chart_scorecard_bullets(result: AnalysisResult, config: ChartConfig) -> Figure:
    """Horizontal bullet charts for 3 KPIs with PULSE benchmarks."""
    df = result.df
    if df.empty:
        return Figure()

    kpi_rows = df[
        (df["metric"].isin(_BENCHMARK_KPIS)) & (df["benchmark"] != "") & (df["benchmark"].notna())
    ]
    if kpi_rows.empty:
        return Figure()

    n_kpis = len(kpi_rows)

    with multi_axes(
        nrows=n_kpis,
        ncols=1,
        figsize=(10, max(3, n_kpis * 2 + 1)),
    ) as (fig, axes):
        # Ensure axes is iterable even if n_kpis == 1
        if n_kpis == 1:
            axes = [axes]

        for idx, ((_, row), ax) in enumerate(zip(kpi_rows.iterrows(), axes)):
            actual = float(row["value"])
            benchmark = float(row["benchmark"])

            bands = [benchmark * 0.70, benchmark * 0.85, benchmark * 1.15]
            max_val = max(actual, benchmark * 1.15) * 1.1

            # Background bands (widest to narrowest)
            band_widths = [max_val, bands[2], bands[1]]
            for bw, bc in zip(band_widths, _BAND_COLORS):
                ax.barh(0, bw, height=0.6, color=bc)

            # Actual value bar
            bar_color = ACCENT if row["status"] in ("Above", "At") else CORAL
            ax.barh(0, actual, height=0.25, color=bar_color)

            # Benchmark target line
            ax.plot(
                [benchmark, benchmark],
                [-0.35, 0.35],
                color="#333333",
                linewidth=2.5,
                zorder=10,
            )

            # Value annotation
            ax.annotate(
                f"{actual:,.1f}",
                xy=(actual, 0),
                xytext=(4, 0),
                textcoords="offset points",
                fontsize=10,
                fontweight="bold",
                va="center",
            )

            ax.set_xlim(0, max_val)
            ax.set_yticks([])
            ax.xaxis.set_visible(False)
            ax.set_title(row["metric"], fontsize=12, fontweight="bold", loc="left")

        above_count = sum(1 for _, r in kpi_rows.iterrows() if r["status"] in ("Above", "At"))
        fig.suptitle(
            f"{above_count} of {n_kpis} KPIs meet PULSE benchmark",
            fontsize=14,
            fontweight="bold",
            x=0.02,
            ha="left",
        )
        fig.tight_layout(rect=[0, 0, 1, 0.93])

    return fig
