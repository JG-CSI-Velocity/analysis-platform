"""Attrition Rate Analyses -- A9.1, A9.2, A9.3.

A9.1  Overall Attrition Rate (annual closures bar chart)
A9.2  Closure Duration Analysis (how long before closing)
A9.3  Open vs Closed Comparison (side-by-side metrics)

Ported from attrition.py run_attrition_1/2/3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.attrition._helpers import (
    DURATION_ORDER,
    _safe,
    prepare_attrition_data,
)
from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    DATA_LABEL_SIZE,
    NEGATIVE,
    POSITIVE,
    TEAL,
    TICK_SIZE,
)
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# A9.1 -- Overall Attrition Rate
# ---------------------------------------------------------------------------


def _overall(ctx: PipelineContext) -> list[AnalysisResult]:
    """Overall attrition rate with annual closures bar chart."""
    all_data, open_accts, closed = prepare_attrition_data(ctx)
    total = len(all_data)
    n_closed = len(closed)
    if total == 0:
        return [
            AnalysisResult(
                slide_id="A9.1",
                title="Overall Attrition Rate",
                success=False,
                error="No data",
            )
        ]

    overall_rate = n_closed / total

    # Annual closures trend
    yearly = None
    if n_closed > 0:
        closed_yr = closed.dropna(subset=["Date Closed"]).copy()
        closed_yr["_close_year"] = closed_yr["Date Closed"].dt.year
        yearly = closed_yr.groupby("_close_year").size().reset_index(name="Closures")
        yearly.columns = ["Year", "Closures"]
        yearly = yearly.sort_values("Year")

    # L12M rate
    l12m_rate = 0.0
    if ctx.start_date and ctx.end_date and n_closed > 0:
        sd = pd.Timestamp(ctx.start_date)
        ed = pd.Timestamp(ctx.end_date)
        l12m_closed = closed[(closed["Date Closed"] >= sd) & (closed["Date Closed"] <= ed)]
        l12m_open_start = len(
            all_data[(all_data["Date Closed"].isna()) | (all_data["Date Closed"] >= sd)]
        )
        if l12m_open_start > 0:
            l12m_rate = len(l12m_closed) / l12m_open_start

    # Chart
    chart_path = None
    if yearly is not None and len(yearly) > 1:
        save_to = ctx.paths.charts_dir / "a9_1_overall_attrition.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
        with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
            ax.bar(
                yearly["Year"].astype(str),
                yearly["Closures"],
                color=NEGATIVE,
                edgecolor=BAR_EDGE,
                alpha=BAR_ALPHA,
            )
            for i, (_, row) in enumerate(yearly.iterrows()):
                ax.text(
                    i,
                    row["Closures"] + yearly["Closures"].max() * 0.02,
                    f"{row['Closures']:,.0f}",
                    ha="center",
                    fontsize=DATA_LABEL_SIZE,
                    fontweight="bold",
                )
            ax.set_title(
                "Account Closures by Year",
                fontsize=24,
                fontweight="bold",
                pad=15,
            )
            ax.set_ylabel("Closures", fontsize=20)
            ax.tick_params(labelsize=TICK_SIZE)
            fig.tight_layout()
        chart_path = save_to

    ctx.results["attrition_1"] = {
        "overall_rate": overall_rate,
        "l12m_rate": l12m_rate,
        "total": total,
        "closed": n_closed,
    }

    return [
        AnalysisResult(
            slide_id="A9.1",
            title="Overall Attrition Rate",
            chart_path=chart_path,
            notes=(f"{overall_rate:.1%} overall ({n_closed:,}/{total:,}), L12M: {l12m_rate:.1%}"),
        )
    ]


# ---------------------------------------------------------------------------
# A9.2 -- Closure Duration Analysis
# ---------------------------------------------------------------------------


def _duration(ctx: PipelineContext) -> list[AnalysisResult]:
    """How long closed accounts remained open before closing."""
    _, _, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.2",
                title="Closure Duration",
                success=False,
                error="No closed accounts",
            )
        ]

    valid = closed.dropna(subset=["_duration_cat"])
    if valid.empty:
        return [
            AnalysisResult(
                slide_id="A9.2",
                title="Closure Duration",
                success=False,
                error="No duration data",
            )
        ]

    dur = valid.groupby("_duration_cat").size().reset_index(name="Count")
    dur.columns = ["Duration", "Count"]
    dur["Duration"] = pd.Categorical(
        dur["Duration"],
        categories=DURATION_ORDER,
        ordered=True,
    )
    dur = dur.sort_values("Duration").dropna(subset=["Duration"])
    dur["Pct"] = dur["Count"] / dur["Count"].sum()

    first_year_cats = {"0-1 Month", "1-3 Months", "3-6 Months", "6-12 Months"}
    first_year_pct = dur[dur["Duration"].isin(first_year_cats)]["Pct"].sum()

    save_to = ctx.paths.charts_dir / "a9_2_closure_duration.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        bars = ax.barh(
            dur["Duration"].astype(str),
            dur["Count"],
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for bar, pct in zip(bars, dur["Pct"]):
            w = bar.get_width()
            ax.text(
                w + dur["Count"].max() * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{int(w):,} ({pct:.0%})",
                va="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Account Lifespan Before Closure",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Closed Accounts", fontsize=20)
        ax.tick_params(labelsize=TICK_SIZE)
        ax.invert_yaxis()
        fig.tight_layout()

    ctx.results["attrition_2"] = {"first_year_pct": first_year_pct}

    return [
        AnalysisResult(
            slide_id="A9.2",
            title="Closure Duration Analysis",
            chart_path=save_to,
            notes=f"{first_year_pct:.0%} of closures within first year",
        )
    ]


# ---------------------------------------------------------------------------
# A9.3 -- Open vs Closed Comparison
# ---------------------------------------------------------------------------


def _open_vs_closed(ctx: PipelineContext) -> list[AnalysisResult]:
    """Side-by-side comparison of open vs closed accounts."""
    all_data, open_accts, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.3",
                title="Open vs Closed",
                success=False,
                error="No closed accounts",
            )
        ]

    metrics: dict[str, dict] = {}
    for label, df in [("Open", open_accts), ("Closed", closed)]:
        m: dict = {"Count": len(df)}
        if "Avg Bal" in df.columns:
            m["Avg Balance"] = df["Avg Bal"].mean()
        else:
            m["Avg Balance"] = 0
        metrics[label] = m

    plot_metrics = ["Avg Balance"]
    open_vals = [metrics["Open"].get(k, 0) for k in plot_metrics]
    closed_vals = [metrics["Closed"].get(k, 0) for k in plot_metrics]

    save_to = ctx.paths.charts_dir / "a9_3_open_vs_closed.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        x = np.arange(len(plot_metrics))
        w = 0.35
        b1 = ax.bar(
            x - w / 2,
            open_vals,
            w,
            label="Open",
            color=POSITIVE,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        b2 = ax.bar(
            x + w / 2,
            closed_vals,
            w,
            label="Closed",
            color=NEGATIVE,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for bars in [b1, b2]:
            for bar in bars:
                h = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h,
                    f"${h:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=DATA_LABEL_SIZE,
                    fontweight="bold",
                )
        ax.set_xticks(x)
        ax.set_xticklabels(plot_metrics, fontsize=TICK_SIZE)
        ax.set_title(
            "Open vs Closed Account Comparison",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.legend(fontsize=16)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"${v:,.0f}"))
        fig.tight_layout()

    return [
        AnalysisResult(
            slide_id="A9.3",
            title="Open vs Closed Comparison",
            chart_path=save_to,
            notes=(f"Open: {len(open_accts):,} | Closed: {len(closed):,}"),
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class AttritionRates(AnalysisModule):
    """Core attrition rate analyses -- A9.1, A9.2, A9.3."""

    module_id = "attrition.rates"
    display_name = "Attrition Rates"
    section = "attrition"
    required_columns = ("Date Opened", "Date Closed")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Attrition Rates for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(lambda c: _overall(c), "A9.1", ctx)
        results += _safe(lambda c: _duration(c), "A9.2", ctx)
        results += _safe(lambda c: _open_vs_closed(c), "A9.3", ctx)
        return results
