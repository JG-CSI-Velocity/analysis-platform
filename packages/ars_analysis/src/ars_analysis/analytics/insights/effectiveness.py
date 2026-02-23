"""Effectiveness Proof Analysis -- A18 series.

Counters the objection "ARS is ineffective" by showing:
- A18.1: DCTR progression over time (with program start marker if available)
- A18.2: Cumulative value delivered timeline
- A18.3: Industry benchmarks comparison (CU vs PULSE data)

Slide IDs: A18.1, A18.2, A18.3.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.ticker as mticker
import numpy as np
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.insights._data import get_dctr_1, get_dctr_3, get_reg_e_1
from ars_analysis.analytics.mailer._helpers import (
    RESPONSE_SEGMENTS,
    discover_metric_cols,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE, SILVER, TEAL
from ars_analysis.pipeline.context import PipelineContext

_BENCHMARKS_PATH = Path(__file__).parents[4] / "config" / "benchmarks.json"


# ---------------------------------------------------------------------------
# Benchmark loader
# ---------------------------------------------------------------------------


def _load_benchmarks() -> dict:
    """Load industry benchmarks from config/benchmarks.json."""
    # Try multiple paths (installed vs dev layout)
    for candidate in [
        _BENCHMARKS_PATH,
        Path("config/benchmarks.json"),
        Path(__file__).parents[5] / "config" / "benchmarks.json",
    ]:
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)
    logger.warning("benchmarks.json not found; using defaults")
    return {
        "debit_penetration_rate": 0.805,
        "active_card_rate": 0.663,
        "member_acquisition_cost": 562.50,
        "direct_mail_response_rate": 0.045,
    }


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_dctr_progression(
    ax,
    ctx: PipelineContext,
) -> str:
    """Draw DCTR trend line using available data. Returns insight."""
    # Try to get historical and L12M DCTR from upstream results
    dctr_1 = get_dctr_1(ctx)
    dctr_3 = get_dctr_3(ctx)

    hist_dctr = dctr_1.get("overall_dctr", 0) * 100
    l12m_dctr = dctr_3.get("dctr", 0) * 100

    if hist_dctr == 0 and l12m_dctr == 0:
        return ""

    # Build what we have: at minimum historical vs L12M
    labels = ["Historical", "L12M"]
    values = [hist_dctr, l12m_dctr]

    colors = []
    for v in values:
        colors.append(POSITIVE if v >= hist_dctr else NEGATIVE)

    bars = ax.bar(
        labels, values, color=[TEAL, POSITIVE], width=0.5, edgecolor="white", linewidth=1.5
    )

    # Data labels
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=20,
            fontweight="bold",
        )

    # Delta annotation
    delta = l12m_dctr - hist_dctr
    sign = "+" if delta >= 0 else ""
    delta_color = POSITIVE if delta >= 0 else NEGATIVE
    ax.annotate(
        f"{sign}{delta:.1f}pp",
        xy=(1, l12m_dctr),
        xytext=(1.4, (hist_dctr + l12m_dctr) / 2),
        fontsize=18,
        fontweight="bold",
        color=delta_color,
        arrowprops={"arrowstyle": "->", "color": delta_color, "lw": 2},
    )

    ax.set_title("DCTR Progression", fontsize=20, fontweight="bold")
    ax.set_ylabel("Debit Card Transaction Rate (%)", fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=14)

    return f"Historical: {hist_dctr:.1f}% -> L12M: {l12m_dctr:.1f}% ({sign}{delta:.1f}pp)"


def _draw_cumulative_value(
    ax,
    ctx: PipelineContext,
) -> str:
    """Draw cumulative IC value from activations over time. Returns insight."""
    pairs = discover_pairs(ctx)
    spend_cols, _ = discover_metric_cols(ctx)

    if not pairs or not spend_cols:
        return ""

    data = ctx.data
    ic_rate = ctx.client.ic_rate or 0.0015

    # For each mail month, count new activations and compute incremental IC
    monthly_ic = []
    seen_responded: set = set()

    for month, resp_col, _mail_col in pairs:
        responded = set(data[data[resp_col].isin(RESPONSE_SEGMENTS)].index)
        new_resp = responded - seen_responded
        seen_responded |= responded

        # Avg spend of new responders (use latest available spend column)
        if new_resp and spend_cols:
            latest_spend_col = spend_cols[-1]
            avg_spend = data.loc[list(new_resp), latest_spend_col].mean()
        else:
            avg_spend = 0

        monthly_ic_value = len(new_resp) * avg_spend * ic_rate
        monthly_ic.append(
            {
                "month": month,
                "month_ts": parse_month(month),
                "new_activations": len(new_resp),
                "monthly_ic": monthly_ic_value,
            }
        )

    if not monthly_ic:
        return ""

    # Cumulative
    cum_ic = np.cumsum([m["monthly_ic"] for m in monthly_ic])
    months = [m["month"] for m in monthly_ic]
    x = np.arange(len(months))

    ax.fill_between(x, cum_ic, alpha=0.3, color=POSITIVE)
    ax.plot(x, cum_ic, marker="o", color=POSITIVE, linewidth=2.5, markersize=8)

    # Endpoint label
    if len(cum_ic) > 0:
        ax.annotate(
            f"${cum_ic[-1]:,.0f}",
            xy=(x[-1], cum_ic[-1]),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=16,
            fontweight="bold",
            color=POSITIVE,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=14, rotation=45, ha="right")
    ax.set_ylabel("Cumulative Incremental IC Revenue ($)", fontsize=14)
    ax.set_title("Cumulative Value Delivered", fontsize=20, fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    total_ic = cum_ic[-1] if len(cum_ic) > 0 else 0
    total_act = sum(m["new_activations"] for m in monthly_ic)
    return f"${total_ic:,.0f} cumulative IC from {total_act:,} activations"


def _draw_benchmarks(
    ax,
    ctx: PipelineContext,
    benchmarks: dict,
) -> str:
    """Draw horizontal bar comparison of CU vs industry benchmarks. Returns insight."""
    dctr_1 = get_dctr_1(ctx)
    dctr_3 = get_dctr_3(ctx)
    reg_e = get_reg_e_1(ctx)

    cu_dctr = dctr_3.get("dctr", dctr_1.get("overall_dctr", 0))
    cu_rege = reg_e.get("opt_in_rate", 0)
    bench_active = benchmarks.get("active_card_rate", 0.663)

    # Build comparison data
    metrics = []
    if cu_dctr > 0:
        metrics.append(("DCTR", cu_dctr * 100, bench_active * 100))
    if cu_rege > 0:
        metrics.append(("Reg E Opt-In", cu_rege * 100, 50.0))  # Industry avg ~50%

    if not metrics:
        return ""

    labels = [m[0] for m in metrics]
    cu_vals = [m[1] for m in metrics]
    bench_vals = [m[2] for m in metrics]

    y = np.arange(len(labels))
    height = 0.35

    ax.barh(y - height / 2, cu_vals, height, label="Your Credit Union", color=TEAL)
    ax.barh(y + height / 2, bench_vals, height, label="Industry Benchmark", color=SILVER)

    # Data labels
    for yi, (cv, bv) in enumerate(zip(cu_vals, bench_vals)):
        ax.text(
            cv,
            yi - height / 2,
            f" {cv:.1f}%",
            va="center",
            fontsize=14,
            fontweight="bold",
            color=TEAL,
        )
        ax.text(
            bv,
            yi + height / 2,
            f" {bv:.1f}%",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#555",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=16)
    ax.set_xlabel("Rate (%)", fontsize=14)
    ax.set_title("Your Performance vs Industry Benchmarks", fontsize=20, fontweight="bold")
    ax.legend(fontsize=14, loc="lower right", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    # Source footnote
    source = benchmarks.get("source", "Industry data")
    ax.text(
        0.99,
        0.01,
        f"Source: {source}",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=10,
        color="#999999",
        fontstyle="italic",
    )

    insights = []
    for label, cv, bv in metrics:
        delta = cv - bv
        sign = "+" if delta >= 0 else ""
        insights.append(f"{label}: {sign}{delta:.1f}pp vs benchmark")
    return " | ".join(insights)


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class EffectivenessProof(AnalysisModule):
    """Effectiveness Proof Analysis -- A18 series."""

    module_id = "insights.effectiveness"
    display_name = "Effectiveness Proof"
    section = "insights"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Effectiveness proof for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # A18.1 -- DCTR Progression
        save_to = ctx.paths.charts_dir / "a18_1_dctr_progression.png"
        with chart_figure(figsize=(12, 8), save_path=save_to) as (_fig, ax):
            insight = _draw_dctr_progression(ax, ctx)
        if insight:
            results.append(
                AnalysisResult(
                    slide_id="A18.1",
                    title="DCTR Progression",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A18.2 -- Cumulative Value Delivered
        save_to = ctx.paths.charts_dir / "a18_2_cumulative_value.png"
        with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
            insight = _draw_cumulative_value(ax, ctx)
        if insight:
            results.append(
                AnalysisResult(
                    slide_id="A18.2",
                    title="Cumulative Value Delivered",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A18.3 -- Industry Benchmarks
        benchmarks = _load_benchmarks()
        save_to = ctx.paths.charts_dir / "a18_3_benchmarks.png"
        with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
            insight = _draw_benchmarks(ax, ctx, benchmarks)
        if insight:
            results.append(
                AnalysisResult(
                    slide_id="A18.3",
                    title="Industry Benchmark Comparison",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        if not results:
            return [
                AnalysisResult(
                    slide_id="A18",
                    title="Effectiveness Proof",
                    success=False,
                    error="Insufficient upstream data for effectiveness analysis",
                )
            ]

        return results
