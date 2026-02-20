"""Attrition Impact & Retention Analyses -- A9.9 through A9.13.

A9.9   Debit Card Retention Effect (hero slide)
A9.10  Mailer Program Retention Effect (hero slide)
A9.11  Revenue Impact of Attrition
A9.12  Attrition Velocity (L12M monthly trend)
A9.13  ARS-Eligible vs Non-ARS Comparison

Ported from attrition.py run_attrition_9 through run_attrition_13.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.attrition._helpers import (
    _safe,
    prepare_attrition_data,
    product_col,
)
from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import (
    BAR_ALPHA,
    BAR_EDGE,
    DATA_LABEL_SIZE,
    NEGATIVE,
    NEUTRAL,
    POSITIVE,
    TEAL,
    TICK_SIZE,
    TTM,
)
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# A9.9 -- Debit Card Retention Effect
# ---------------------------------------------------------------------------


def _debit_retention(ctx: PipelineContext) -> list[AnalysisResult]:
    """Do accounts with debit cards close less often?"""
    all_data, _, closed = prepare_attrition_data(ctx)
    if closed.empty or "Debit?" not in all_data.columns:
        return [
            AnalysisResult(
                slide_id="A9.9",
                title="Debit Card Retention",
                success=False,
                error="No closed accounts or no Debit? column",
            )
        ]

    rows = []
    for debit_val, label in [("Yes", "With Debit Card"), ("No", "Without Debit Card")]:
        total = len(all_data[all_data["Debit?"] == debit_val])
        n_closed = len(closed[closed["Debit?"] == debit_val])
        rate = n_closed / total if total > 0 else 0
        rows.append(
            {
                "Debit Status": label,
                "Total": total,
                "Closed": n_closed,
                "Attrition Rate": rate,
            }
        )
    debit_df = pd.DataFrame(rows)

    with_rate = debit_df.iloc[0]["Attrition Rate"]
    without_rate = debit_df.iloc[1]["Attrition Rate"]
    retention_lift = without_rate - with_rate

    save_to = ctx.paths.charts_dir / "a9_9_debit_retention.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        colors = [POSITIVE, NEGATIVE]
        bars = ax.bar(
            debit_df["Debit Status"],
            debit_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, debit_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Debit Card Impact on Account Retention",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda x, p: f"{x:.0f}%"),
        )
        ax.tick_params(labelsize=TICK_SIZE)
        if retention_lift > 0:
            ax.annotate(
                f"{retention_lift:.1%} lower attrition\nwith debit cards",
                xy=(0, with_rate * 100),
                fontsize=18,
                xytext=(0.5, (with_rate + without_rate) / 2 * 100),
                ha="center",
                fontweight="bold",
                color=POSITIVE,
                arrowprops={"arrowstyle": "->", "color": POSITIVE, "lw": 2},
            )
        fig.tight_layout()

    ctx.results["attrition_9"] = {"retention_lift": retention_lift}

    return [
        AnalysisResult(
            slide_id="A9.9",
            title="Debit Card Retention Effect",
            chart_path=save_to,
            notes=f"Retention lift: {retention_lift:.1%}",
        )
    ]


# ---------------------------------------------------------------------------
# A9.10 -- Mailer Program Retention Effect
# ---------------------------------------------------------------------------


def _mailer_retention(ctx: PipelineContext) -> list[AnalysisResult]:
    """Do mailed/responding accounts close less often?"""
    all_data, _, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.10",
                title="Mailer Retention",
                success=False,
                error="No closed accounts",
            )
        ]

    mail_cols = [c for c in all_data.columns if re.match(r"^[A-Z][a-z]{2}\d{2} Mail$", c)]
    resp_cols = [c for c in all_data.columns if re.match(r"^[A-Z][a-z]{2}\d{2} Resp$", c)]

    if not mail_cols:
        return [
            AnalysisResult(
                slide_id="A9.10",
                title="Mailer Retention",
                success=False,
                error="No mailer columns found",
            )
        ]

    all_copy = all_data.copy()
    all_copy["_ever_mailed"] = all_copy[mail_cols].notna().any(axis=1)
    if resp_cols:
        all_copy["_ever_responded"] = all_copy[resp_cols].notna().any(axis=1)
    else:
        all_copy["_ever_responded"] = False

    def _classify(row: pd.Series) -> str:
        if row["_ever_responded"]:
            return "Responded"
        if row["_ever_mailed"]:
            return "Mailed (No Response)"
        return "Never Mailed"

    all_copy["_mail_group"] = all_copy.apply(_classify, axis=1)

    rows = []
    for grp in ["Responded", "Mailed (No Response)", "Never Mailed"]:
        subset = all_copy[all_copy["_mail_group"] == grp]
        total = len(subset)
        n_closed = int(subset["Date Closed"].notna().sum())
        rate = n_closed / total if total > 0 else 0
        rows.append(
            {
                "Group": grp,
                "Total": total,
                "Closed": n_closed,
                "Attrition Rate": rate,
            }
        )
    mail_df = pd.DataFrame(rows)

    resp_rate = mail_df.iloc[0]["Attrition Rate"]
    never_rate = mail_df.iloc[2]["Attrition Rate"]
    lift = never_rate - resp_rate

    save_to = ctx.paths.charts_dir / "a9_10_mailer_retention.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        colors = [POSITIVE, TTM, NEUTRAL]
        bars = ax.bar(
            mail_df["Group"],
            mail_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, mail_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Mailer Program Impact on Retention",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda x, p: f"{x:.0f}%"),
        )
        ax.tick_params(labelsize=TICK_SIZE)
        fig.tight_layout()

    ctx.results["attrition_10"] = {"lift": lift}

    return [
        AnalysisResult(
            slide_id="A9.10",
            title="Mailer Program Retention",
            chart_path=save_to,
            notes=f"Responder lift: {lift:.1%}",
        )
    ]


# ---------------------------------------------------------------------------
# A9.11 -- Revenue Impact of Attrition
# ---------------------------------------------------------------------------


def _revenue_impact(ctx: PipelineContext) -> list[AnalysisResult]:
    """Estimated annual revenue lost from closed accounts."""
    _, _, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.11",
                title="Revenue Impact",
                success=False,
                error="No closed accounts",
            )
        ]

    ic_rate = ctx.client.ic_rate or 0.007

    spend_cols = sorted(
        [c for c in closed.columns if c.endswith(" Spend")],
    )

    closed_copy = closed.copy()
    if spend_cols:
        closed_copy["_last_spend"] = (
            closed_copy[spend_cols].replace(0, np.nan).ffill(axis=1).iloc[:, -1].fillna(0)
        )
    else:
        closed_copy["_last_spend"] = 0

    closed_copy["_est_annual_revenue"] = closed_copy["_last_spend"] * ic_rate * 12

    total_lost = closed_copy["_est_annual_revenue"].sum()
    avg_lost = closed_copy["_est_annual_revenue"].mean()
    n_closed = len(closed_copy)

    # Revenue distribution chart
    bins = [0, 50, 100, 250, 500, 1000, float("inf")]
    labels = ["$0-$50", "$50-$100", "$100-$250", "$250-$500", "$500-$1K", "$1K+"]
    closed_copy["_rev_bin"] = pd.cut(
        closed_copy["_est_annual_revenue"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    )
    rev_dist = (
        closed_copy.groupby("_rev_bin", observed=True)
        .agg(
            Count=("_rev_bin", "size"),
            Total_Revenue=("_est_annual_revenue", "sum"),
        )
        .reset_index()
    )

    save_to = ctx.paths.charts_dir / "a9_11_revenue_impact.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        ax.bar(
            rev_dist["_rev_bin"].astype(str),
            rev_dist["Total_Revenue"],
            color=NEGATIVE,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, (rev, ct) in enumerate(
            zip(rev_dist["Total_Revenue"], rev_dist["Count"]),
        ):
            ax.text(
                i,
                rev + total_lost * 0.02,
                f"${rev:,.0f}\n({ct:,} accts)",
                ha="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )
        ax.set_title(
            "Estimated Annual Revenue Lost by Tier",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Revenue Lost ($)", fontsize=20)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda v, p: f"${v:,.0f}"),
        )
        ax.tick_params(labelsize=TICK_SIZE - 2)
        fig.tight_layout()

    ctx.results["attrition_11"] = {
        "total_lost": total_lost,
        "avg_lost": avg_lost,
    }

    return [
        AnalysisResult(
            slide_id="A9.11",
            title="Revenue Impact of Attrition",
            chart_path=save_to,
            notes=f"Est. ${total_lost:,.0f} annual loss from {n_closed:,} accounts",
        )
    ]


# ---------------------------------------------------------------------------
# A9.12 -- Attrition Velocity (L12M Monthly Trend)
# ---------------------------------------------------------------------------


def _velocity(ctx: PipelineContext) -> list[AnalysisResult]:
    """Monthly closure trend over L12M with moving average."""
    _, _, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.12",
                title="Attrition Velocity",
                success=False,
                error="No closed accounts",
            )
        ]

    if not ctx.start_date or not ctx.end_date:
        return [
            AnalysisResult(
                slide_id="A9.12",
                title="Attrition Velocity",
                success=False,
                error="No date range configured",
            )
        ]

    sd = pd.Timestamp(ctx.start_date)
    ed = pd.Timestamp(ctx.end_date)
    l12m_closed = closed[(closed["Date Closed"] >= sd) & (closed["Date Closed"] <= ed)].copy()

    if l12m_closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.12",
                title="Attrition Velocity",
                success=False,
                error="No L12M closures",
            )
        ]

    l12m_closed["_close_month"] = l12m_closed["Date Closed"].dt.to_period("M")
    monthly = l12m_closed.groupby("_close_month").size().reset_index(name="Closures")
    monthly["Month"] = monthly["_close_month"].dt.to_timestamp()
    monthly = monthly.sort_values("Month")

    if len(monthly) >= 3:
        monthly["MA3"] = monthly["Closures"].rolling(3, min_periods=1).mean()
    else:
        monthly["MA3"] = monthly["Closures"].astype(float)

    total_l12m = int(monthly["Closures"].sum())

    # Trend detection
    trend = ""
    if len(monthly) >= 6:
        half = len(monthly) // 2
        first_half = monthly["Closures"].iloc[:half].mean()
        second_half = monthly["Closures"].iloc[half:].mean()
        if second_half > first_half * 1.1:
            trend = "increasing"
        elif second_half < first_half * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"

    save_to = ctx.paths.charts_dir / "a9_12_velocity.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        month_labels = monthly["Month"].dt.strftime("%b %y")
        x = np.arange(len(monthly))
        ax.bar(
            x,
            monthly["Closures"],
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            label="Monthly Closures",
        )
        ax.plot(
            x,
            monthly["MA3"],
            color=NEGATIVE,
            linewidth=3,
            marker="o",
            markersize=8,
            label="3-Mo Avg",
        )
        for i, c in enumerate(monthly["Closures"]):
            ax.text(
                i,
                c + monthly["Closures"].max() * 0.03,
                str(int(c)),
                ha="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )
        ax.set_xticks(x)
        ax.set_xticklabels(
            month_labels,
            fontsize=TICK_SIZE - 2,
            rotation=45,
            ha="right",
        )
        ax.set_title(
            "Monthly Account Closures (L12M)",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Closures", fontsize=20)
        ax.legend(fontsize=16)
        fig.tight_layout()

    ctx.results["attrition_12"] = {
        "total_l12m": total_l12m,
        "trend": trend,
    }

    notes = f"{total_l12m:,} L12M closures"
    if trend:
        notes += f" (trend: {trend})"

    return [
        AnalysisResult(
            slide_id="A9.12",
            title="Attrition Velocity",
            chart_path=save_to,
            notes=notes,
        )
    ]


# ---------------------------------------------------------------------------
# A9.13 -- ARS-Eligible vs Non-ARS Comparison
# ---------------------------------------------------------------------------


def _ars_comparison(ctx: PipelineContext) -> list[AnalysisResult]:
    """Compare attrition for ARS-eligible vs non-eligible accounts."""
    all_data, _, closed = prepare_attrition_data(ctx)
    if closed.empty:
        return [
            AnalysisResult(
                slide_id="A9.13",
                title="ARS vs Non-ARS",
                success=False,
                error="No closed accounts",
            )
        ]

    esc = ctx.client.eligible_stat_codes
    epc = ctx.client.eligible_prod_codes
    pcol = product_col(all_data)
    if not esc or not epc or pcol is None:
        return [
            AnalysisResult(
                slide_id="A9.13",
                title="ARS vs Non-ARS",
                success=False,
                error="No eligibility config or product column",
            )
        ]

    all_copy = all_data.copy()
    all_copy["_ars_eligible"] = all_copy["Stat Code"].isin(esc) & all_copy[pcol].isin(epc)

    rows = []
    for elig, label in [(True, "ARS-Eligible"), (False, "Non-Eligible")]:
        subset = all_copy[all_copy["_ars_eligible"] == elig]
        total = len(subset)
        n_closed = int(subset["Date Closed"].notna().sum())
        rate = n_closed / total if total > 0 else 0
        rows.append(
            {
                "Group": label,
                "Total": total,
                "Closed": n_closed,
                "Attrition Rate": rate,
            }
        )
    ars_df = pd.DataFrame(rows)

    ars_rate = ars_df.iloc[0]["Attrition Rate"]
    non_rate = ars_df.iloc[1]["Attrition Rate"]
    diff = non_rate - ars_rate

    save_to = ctx.paths.charts_dir / "a9_13_ars_comparison.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        colors = [POSITIVE, NEUTRAL]
        bars = ax.bar(
            ars_df["Group"],
            ars_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, ars_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition: ARS-Eligible vs Non-Eligible",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=20)
        ax.yaxis.set_major_formatter(
            FuncFormatter(lambda x, p: f"{x:.0f}%"),
        )
        ax.tick_params(labelsize=TICK_SIZE)
        fig.tight_layout()

    ctx.results["attrition_13"] = {"diff": diff}

    if diff > 0:
        notes = f"ARS-eligible show {diff:.1%} lower attrition"
    else:
        notes = "Attrition comparison by eligibility status"

    return [
        AnalysisResult(
            slide_id="A9.13",
            title="ARS vs Non-ARS Comparison",
            chart_path=save_to,
            notes=notes,
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class AttritionImpact(AnalysisModule):
    """Attrition impact & retention analyses -- A9.9 through A9.13."""

    module_id = "attrition.impact"
    display_name = "Attrition Impact & Retention"
    section = "attrition"
    required_columns = ("Date Opened", "Date Closed")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info(
            "Attrition Impact for {client}",
            client=ctx.client.client_id,
        )
        results: list[AnalysisResult] = []
        results += _safe(lambda c: _debit_retention(c), "A9.9", ctx)
        results += _safe(lambda c: _mailer_retention(c), "A9.10", ctx)
        results += _safe(lambda c: _revenue_impact(c), "A9.11", ctx)
        results += _safe(lambda c: _velocity(c), "A9.12", ctx)
        results += _safe(lambda c: _ars_comparison(c), "A9.13", ctx)
        return results
