"""Cumulative Reach Analysis -- A17 series.

Counters the objection "ARS isn't impacting enough people" by showing:
- A17.1: Cumulative unique accounts mailed over all mail months
- A17.2: Program penetration rate (unique mailed / total eligible)
- A17.3: Organic activation (debit holders who were NEVER mailed)

Slide IDs: A17.1, A17.2, A17.3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.mailer._helpers import (
    MAILED_SEGMENTS,
    RESPONSE_SEGMENTS,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import POSITIVE, SILVER, TEAL
from ars_analysis.pipeline.context import PipelineContext

NON_RESP_COLOR = "#404040"


# ---------------------------------------------------------------------------
# Computation helpers
# ---------------------------------------------------------------------------


def _cumulative_reach(
    data: pd.DataFrame,
    pairs: list[tuple[str, str, str]],
) -> list[dict]:
    """Compute per-month cumulative unique accounts mailed + responded.

    Returns list of dicts: [{month, new_mailed, cum_mailed, new_responded, cum_responded}]
    """
    seen_mailed: set = set()
    seen_responded: set = set()
    results = []

    for month, resp_col, mail_col in pairs:
        mailed_this = set(data[data[mail_col].isin(MAILED_SEGMENTS)].index)
        responded_this = set(data[data[resp_col].isin(RESPONSE_SEGMENTS)].index)

        new_mailed = mailed_this - seen_mailed
        new_responded = responded_this - seen_responded

        seen_mailed |= mailed_this
        seen_responded |= responded_this

        results.append(
            {
                "month": month,
                "month_ts": parse_month(month),
                "new_mailed": len(new_mailed),
                "cum_mailed": len(seen_mailed),
                "new_responded": len(new_responded),
                "cum_responded": len(seen_responded),
            }
        )

    return results


def _organic_activation(
    data: pd.DataFrame,
    pairs: list[tuple[str, str, str]],
) -> dict:
    """Identify accounts with debit cards that were never mailed.

    Returns dict with counts and rates.
    """
    # Detect debit column
    debit_col = None
    for col in ("Debit?", "Debit", "DC Indicator"):
        if col in data.columns:
            debit_col = col
            break

    if debit_col is None:
        return {"organic": 0, "mailed_resp": 0, "mailed_non_resp": 0, "total_debit": 0}

    has_debit = data[data[debit_col].isin(["Yes", "Y", True, 1])]

    # Build ever-mailed mask
    ever_mailed = pd.Series(False, index=data.index)
    ever_responded = pd.Series(False, index=data.index)
    for _month, resp_col, mail_col in pairs:
        ever_mailed |= data[mail_col].isin(MAILED_SEGMENTS)
        ever_responded |= data[resp_col].isin(RESPONSE_SEGMENTS)

    organic = has_debit[~ever_mailed.loc[has_debit.index]]
    mailed_resp = has_debit[ever_responded.loc[has_debit.index]]
    mailed_non_resp = has_debit[
        ever_mailed.loc[has_debit.index] & ~ever_responded.loc[has_debit.index]
    ]

    return {
        "organic": len(organic),
        "mailed_resp": len(mailed_resp),
        "mailed_non_resp": len(mailed_non_resp),
        "total_debit": len(has_debit),
    }


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_cumulative_reach(
    ax,
    reach_data: list[dict],
) -> str:
    """Draw combo chart: bars (new mailed) + line (cumulative). Returns insight."""
    months = [r["month"] for r in reach_data]
    new_mailed = [r["new_mailed"] for r in reach_data]
    cum_mailed = [r["cum_mailed"] for r in reach_data]
    cum_responded = [r["cum_responded"] for r in reach_data]

    x = np.arange(len(months))

    # Bars: new unique accounts mailed per month
    ax.bar(x, new_mailed, color=SILVER, alpha=0.7, label="New Unique Mailed", zorder=2)

    # Lines: cumulative totals
    ax2 = ax.twinx()
    ax2.plot(
        x,
        cum_mailed,
        marker="o",
        color=TEAL,
        linewidth=2.5,
        markersize=8,
        label="Cumulative Mailed",
        zorder=3,
    )
    ax2.plot(
        x,
        cum_responded,
        marker="s",
        color=POSITIVE,
        linewidth=2.5,
        markersize=8,
        label="Cumulative Responded",
        zorder=3,
    )

    # Endpoint labels
    if cum_mailed:
        ax2.annotate(
            f"{cum_mailed[-1]:,}",
            xy=(x[-1], cum_mailed[-1]),
            xytext=(8, 6),
            textcoords="offset points",
            fontsize=13,
            fontweight="bold",
            color=TEAL,
        )
    if cum_responded:
        ax2.annotate(
            f"{cum_responded[-1]:,}",
            xy=(x[-1], cum_responded[-1]),
            xytext=(8, -12),
            textcoords="offset points",
            fontsize=13,
            fontweight="bold",
            color=POSITIVE,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(months, fontsize=14, rotation=45, ha="right")
    ax.set_ylabel("New Unique Accounts Mailed", fontsize=14)
    ax2.set_ylabel("Cumulative Total", fontsize=14)
    ax.set_title("Cumulative Program Reach", fontsize=20, fontweight="bold")

    # Combine legends
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=13, loc="upper left", frameon=True)

    ax.spines["top"].set_visible(False)
    ax2.spines["top"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)
    ax2.tick_params(axis="both", labelsize=12)

    total_m = cum_mailed[-1] if cum_mailed else 0
    total_r = cum_responded[-1] if cum_responded else 0
    return (
        f"{total_m:,} unique accounts mailed | {total_r:,} responded "
        f"({total_r / total_m:.0%} cumulative response)"
        if total_m > 0
        else ""
    )


def _draw_penetration_kpi(
    ax,
    cum_mailed: int,
    cum_responded: int,
    total_eligible: int,
) -> str:
    """Draw KPI panel showing penetration rate. Returns insight."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    pen_rate = cum_mailed / total_eligible if total_eligible > 0 else 0
    resp_rate = cum_responded / total_eligible if total_eligible > 0 else 0

    # Title
    ax.text(
        0.5,
        0.92,
        "Program Penetration",
        ha="center",
        va="top",
        fontsize=24,
        fontweight="bold",
        color="#1E3D59",
    )

    # Main KPI: penetration rate
    ax.text(
        0.5,
        0.65,
        f"{pen_rate:.1%}",
        ha="center",
        va="center",
        fontsize=60,
        fontweight="bold",
        color=TEAL,
    )
    ax.text(
        0.5,
        0.48,
        "of eligible accounts reached",
        ha="center",
        va="center",
        fontsize=16,
        color="#555555",
    )

    # Sub-KPIs
    ax.text(
        0.2,
        0.28,
        f"{cum_mailed:,}",
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color=TEAL,
    )
    ax.text(0.2, 0.18, "Unique Mailed", ha="center", va="center", fontsize=14, color="#555555")

    ax.text(
        0.5,
        0.28,
        f"{cum_responded:,}",
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color=POSITIVE,
    )
    ax.text(0.5, 0.18, "Unique Responded", ha="center", va="center", fontsize=14, color="#555555")

    ax.text(
        0.8,
        0.28,
        f"{total_eligible:,}",
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color=SILVER,
    )
    ax.text(0.8, 0.18, "Total Eligible", ha="center", va="center", fontsize=14, color="#555555")

    # Response rate note
    ax.text(
        0.5,
        0.05,
        f"Cumulative response rate: {resp_rate:.1%}",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=POSITIVE,
    )

    return f"Penetration: {pen_rate:.1%} | {cum_mailed:,} mailed of {total_eligible:,} eligible"


def _draw_organic(
    ax,
    organic_data: dict,
) -> str:
    """Draw grouped bar showing organic vs mailed debit holders. Returns insight."""
    categories = ["Organic\n(Never Mailed)", "Mailed\nResponders", "Mailed\nNon-Resp"]
    values = [
        organic_data["organic"],
        organic_data["mailed_resp"],
        organic_data["mailed_non_resp"],
    ]
    colors = [TEAL, POSITIVE, SILVER]

    x = np.arange(len(categories))
    bars = ax.bar(x, values, color=colors, width=0.6, edgecolor="white", linewidth=1.5)

    # Data labels
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:,}",
            ha="center",
            va="bottom",
            fontsize=18,
            fontweight="bold",
        )

    total = organic_data["total_debit"]
    if total > 0:
        for bar, val in zip(bars, values):
            pct = val / total * 100
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() / 2,
                f"{pct:.0f}%",
                ha="center",
                va="center",
                fontsize=14,
                color="white",
                fontweight="bold",
            )

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=14)
    ax.set_ylabel("Accounts with Debit Card", fontsize=14)
    ax.set_title("Debit Card Holders: How They Got There", fontsize=20, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    org = organic_data["organic"]
    resp = organic_data["mailed_resp"]
    non_resp = organic_data["mailed_non_resp"]
    program_influenced = resp + non_resp
    if total > 0:
        return (
            f"Organic: {org:,} ({org / total:.0%}) | "
            f"Program-influenced: {program_influenced:,} ({program_influenced / total:.0%})"
        )
    return ""


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class CumulativeReach(AnalysisModule):
    """Cumulative Reach Analysis -- A17 series."""

    module_id = "mailer.reach"
    display_name = "Cumulative Program Reach"
    section = "mailer"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Cumulative Reach for {client}", client=ctx.client.client_id)
        pairs = discover_pairs(ctx)

        if not pairs:
            return [
                AnalysisResult(
                    slide_id="A17",
                    title="Cumulative Reach",
                    success=False,
                    error="No mail/response pairs found",
                )
            ]

        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # A17.1 -- Cumulative Members Reached
        reach_data = _cumulative_reach(ctx.data, pairs)
        if reach_data:
            save_to = ctx.paths.charts_dir / "a17_1_cumulative_reach.png"
            with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                insight = _draw_cumulative_reach(ax, reach_data)
            results.append(
                AnalysisResult(
                    slide_id="A17.1",
                    title="Cumulative Program Reach",
                    chart_path=save_to,
                    notes=insight,
                )
            )

            # Store for other modules
            final = reach_data[-1]
            ctx.results["reach_cumulative"] = {
                "cum_mailed": final["cum_mailed"],
                "cum_responded": final["cum_responded"],
                "months": len(reach_data),
            }

        # A17.2 -- Penetration Rate KPI
        n_eligible = len(ctx.subsets.eligible_data) if ctx.subsets else 0
        cum_m = reach_data[-1]["cum_mailed"] if reach_data else 0
        cum_r = reach_data[-1]["cum_responded"] if reach_data else 0

        if n_eligible > 0:
            save_to = ctx.paths.charts_dir / "a17_2_penetration_rate.png"
            with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                insight = _draw_penetration_kpi(ax, cum_m, cum_r, n_eligible)
            results.append(
                AnalysisResult(
                    slide_id="A17.2",
                    title="Program Penetration Rate",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A17.3 -- Organic Activation
        organic_data = _organic_activation(ctx.data, pairs)
        if organic_data["total_debit"] > 0:
            save_to = ctx.paths.charts_dir / "a17_3_organic_activation.png"
            with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                insight = _draw_organic(ax, organic_data)
            results.append(
                AnalysisResult(
                    slide_id="A17.3",
                    title="Organic vs Program Activation",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        if not results:
            return [
                AnalysisResult(
                    slide_id="A17",
                    title="Cumulative Reach",
                    success=False,
                    error="Insufficient data for reach analysis",
                )
            ]

        return results
