"""Impact Synthesis -- S1 through S5.

S1  The Revenue Gap (debit + Reg E gap in dollars)
S2  The Cost of Walking Away (attrition cost + preventable revenue)
S3  The Mailer Program Works (incremental IC + retention value)
S4  Branch Performance Gap (best vs worst branch dollar impact)
S5  The Debit Card Cascade (one activation = 3 revenue streams)
"""

from __future__ import annotations

import numpy as np
from loguru import logger
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.insights._data import (
    _safe,
    get_a3,
    get_attrition_1,
    get_attrition_9,
    get_attrition_10,
    get_attrition_11,
    get_dctr_1,
    get_dctr_9,
    get_market_reach,
    get_pre_post_delta,
    get_reg_e_1,
    get_revenue_attribution,
    get_value_1,
    get_value_2,
)
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

CAPTURE_RATE = 0.25  # Realistic near-term capture assumption


# ---------------------------------------------------------------------------
# S1 -- The Revenue Gap
# ---------------------------------------------------------------------------


def _revenue_gap(ctx: PipelineContext) -> list[AnalysisResult]:
    """You have X accounts without debit and Y without Reg E = $Z/year gap."""
    v1 = get_value_1(ctx)
    v2 = get_value_2(ctx)

    debit_gap = v1["accts_without"] * v1["delta"]
    rege_gap = v2["accts_without"] * v2["delta"]
    total_gap = debit_gap + rege_gap
    realistic = total_gap * CAPTURE_RATE

    if total_gap == 0:
        return [
            AnalysisResult(
                slide_id="S1",
                title="The Revenue Gap",
                success=False,
                error="No gap data from value module",
            )
        ]

    save_to = ctx.paths.charts_dir / "s1_revenue_gap.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
        # Horizontal waterfall
        categories = [
            "Debit Card Gap",
            "Reg E Gap",
            "Total Gap",
            f"Realistic ({CAPTURE_RATE:.0%})",
        ]
        values = [debit_gap, rege_gap, total_gap, realistic]
        colors = [NEGATIVE, NEGATIVE, "#1E3D59", POSITIVE]

        bars = ax.barh(
            categories[::-1],
            [v for v in values[::-1]],
            color=colors[::-1],
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            height=0.5,
        )
        for bar, val in zip(bars, values[::-1]):
            cx = bar.get_width()
            cy = bar.get_y() + bar.get_height() / 2
            ax.text(
                cx + total_gap * 0.02,
                cy,
                f"${val:,.0f}",
                ha="left",
                va="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )

        ax.set_title(
            "The Revenue Gap: Untapped Opportunity",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Annual Revenue ($)", fontsize=20)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax.tick_params(labelsize=TICK_SIZE)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Annotation
        ax.text(
            total_gap * 0.5,
            -0.8,
            f"{v1['accts_without']:,} accounts without debit "
            f"+ {v2['accts_without']:,} without Reg E",
            ha="center",
            fontsize=14,
            color="#666",
            transform=ax.get_xaxis_transform(),
        )
        fig.tight_layout()

    ctx.results["impact_s1"] = {
        "debit_gap": debit_gap,
        "rege_gap": rege_gap,
        "total_gap": total_gap,
        "realistic_capture": realistic,
    }

    return [
        AnalysisResult(
            slide_id="S1",
            title="The Revenue Gap",
            chart_path=save_to,
            notes=(
                f"Debit gap: ${debit_gap:,.0f} | Reg E gap: ${rege_gap:,.0f} | "
                f"Total: ${total_gap:,.0f} | Realistic: ${realistic:,.0f}"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# S2 -- The Cost of Walking Away
# ---------------------------------------------------------------------------


def _cost_of_attrition(ctx: PipelineContext) -> list[AnalysisResult]:
    """Lost X accounts = $Y destroyed. Debit retention saves W accounts = $V."""
    a1 = get_attrition_1(ctx)
    a9 = get_attrition_9(ctx)
    a11 = get_attrition_11(ctx)

    total_lost = a11["total_lost"]
    avg_lost = a11["avg_lost"]
    closed = a1["closed"]
    retention_lift = a9["retention_lift"]

    if total_lost == 0 and closed == 0:
        return [
            AnalysisResult(
                slide_id="S2",
                title="The Cost of Walking Away",
                success=False,
                error="No attrition data",
            )
        ]

    preventable_closures = round(closed * retention_lift) if retention_lift > 0 else 0
    preventable_revenue = preventable_closures * avg_lost if avg_lost > 0 else 0

    save_to = ctx.paths.charts_dir / "s2_attrition_cost.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
        ax.set_visible(False)

        # Left panel: Revenue Destroyed
        ax_left = fig.add_axes([0.02, 0.05, 0.45, 0.90])
        ax_left.set_xlim(0, 10)
        ax_left.set_ylim(0, 10)
        ax_left.axis("off")

        rect_l = FancyBboxPatch(
            (0.5, 1),
            9,
            8,
            boxstyle="round,pad=0.3",
            facecolor=NEGATIVE,
            alpha=0.08,
            edgecolor=NEGATIVE,
            linewidth=2,
        )
        ax_left.add_patch(rect_l)
        ax_left.text(
            5, 8.5, "Revenue Destroyed", fontsize=20, fontweight="bold", color=NEGATIVE, ha="center"
        )
        ax_left.text(
            5,
            6.5,
            f"${total_lost:,.0f}",
            fontsize=36,
            fontweight="bold",
            color=NEGATIVE,
            ha="center",
        )
        ax_left.text(5, 5.2, f"{closed:,} accounts closed", fontsize=16, color="#666", ha="center")
        ax_left.text(
            5, 4.2, f"${avg_lost:,.0f} avg lost per account", fontsize=14, color="#666", ha="center"
        )

        # Right panel: Preventable Opportunity
        ax_right = fig.add_axes([0.52, 0.05, 0.45, 0.90])
        ax_right.set_xlim(0, 10)
        ax_right.set_ylim(0, 10)
        ax_right.axis("off")

        rect_r = FancyBboxPatch(
            (0.5, 1),
            9,
            8,
            boxstyle="round,pad=0.3",
            facecolor=POSITIVE,
            alpha=0.08,
            edgecolor=POSITIVE,
            linewidth=2,
        )
        ax_right.add_patch(rect_r)
        ax_right.text(
            5,
            8.5,
            "Preventable via Debit",
            fontsize=20,
            fontweight="bold",
            color=POSITIVE,
            ha="center",
        )
        ax_right.text(
            5,
            6.5,
            f"${preventable_revenue:,.0f}",
            fontsize=36,
            fontweight="bold",
            color=POSITIVE,
            ha="center",
        )
        ax_right.text(
            5,
            5.2,
            f"{preventable_closures:,} accounts saved",
            fontsize=16,
            color="#666",
            ha="center",
        )
        ax_right.text(
            5,
            4.2,
            f"{retention_lift:.1%} retention lift from debit",
            fontsize=14,
            color="#666",
            ha="center",
        )

    ctx.results["impact_s2"] = {
        "revenue_destroyed": total_lost,
        "preventable_closures": preventable_closures,
        "preventable_revenue": preventable_revenue,
    }

    return [
        AnalysisResult(
            slide_id="S2",
            title="The Cost of Walking Away",
            chart_path=save_to,
            notes=(
                f"${total_lost:,.0f} destroyed | "
                f"${preventable_revenue:,.0f} preventable ({preventable_closures:,} accounts)"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# S3 -- The Mailer Program Works
# ---------------------------------------------------------------------------


def _mailer_roi(ctx: PipelineContext) -> list[AnalysisResult]:
    """Responders spend $X more. Program generates $Y IC + $Z retention = $Total."""
    ra = get_revenue_attribution(ctx)
    ppd = get_pre_post_delta(ctx)
    mr = get_market_reach(ctx)
    a10 = get_attrition_10(ctx)
    a11 = get_attrition_11(ctx)

    incremental = ra["incremental_total"]
    resp_delta = ppd.get("resp_delta", 0)
    non_delta = ppd.get("non_delta", 0)
    true_lift = resp_delta - non_delta  # Diff-in-diff
    n_responders = mr["n_responders"]
    retention_lift = a10["lift"]
    avg_lost = a11["avg_lost"]

    annual_program = incremental * 12
    retention_value = retention_lift * n_responders * avg_lost if n_responders > 0 else 0
    total_roi = annual_program + retention_value

    if incremental == 0 and n_responders == 0:
        return [
            AnalysisResult(
                slide_id="S3",
                title="The Mailer Program Works",
                success=False,
                error="No mailer data",
            )
        ]

    save_to = ctx.paths.charts_dir / "s3_mailer_roi.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
        ax.set_visible(False)

        ax_main = fig.add_axes([0.05, 0.05, 0.90, 0.85])
        ax_main.set_xlim(0, 10)
        ax_main.set_ylim(0, 10)
        ax_main.axis("off")

        ax_main.text(
            5,
            9.5,
            "Mailer Program: Cause and Effect",
            fontsize=24,
            fontweight="bold",
            color="#1E3D59",
            ha="center",
        )

        # Flow: Mailer -> Activation -> Spend Lift -> Revenue + Retention
        boxes = [
            (1.0, 6.5, "Mailer\nProgram", f"{mr['n_mailed']:,}\nmailed", "#3498DB"),
            (3.5, 6.5, "Activation", f"{n_responders:,}\nresponders", TEAL),
            (6.0, 6.5, "Spend Lift", f"+${true_lift:,.0f}\nper account", POSITIVE),
        ]
        for bx, by, title, detail, color in boxes:
            rect = FancyBboxPatch(
                (bx - 0.8, by - 0.8),
                1.6,
                1.6,
                boxstyle="round,pad=0.15",
                facecolor=color,
                alpha=0.15,
                edgecolor=color,
                linewidth=2,
            )
            ax_main.add_patch(rect)
            ax_main.text(
                bx,
                by + 0.3,
                title,
                ha="center",
                va="center",
                fontsize=13,
                fontweight="bold",
                color=color,
            )
            ax_main.text(bx, by - 0.3, detail, ha="center", va="center", fontsize=11, color="#444")

        # Arrows between boxes
        for x1, x2 in [(1.8, 2.7), (4.3, 5.2)]:
            ax_main.annotate(
                "",
                xy=(x2, 6.5),
                xytext=(x1, 6.5),
                arrowprops={"arrowstyle": "->", "color": "#999", "lw": 2},
            )

        # Result boxes at bottom
        results = [
            (3.0, 3.0, "Annual IC Revenue", f"${annual_program:,.0f}", TEAL),
            (7.0, 3.0, "Retention Value", f"${retention_value:,.0f}", POSITIVE),
        ]
        for bx, by, title, val, color in results:
            rect = FancyBboxPatch(
                (bx - 1.2, by - 0.8),
                2.4,
                1.6,
                boxstyle="round,pad=0.15",
                facecolor=color,
                alpha=0.1,
                edgecolor=color,
                linewidth=2,
            )
            ax_main.add_patch(rect)
            ax_main.text(
                bx, by + 0.3, title, ha="center", fontsize=13, fontweight="bold", color=color
            )
            ax_main.text(
                bx, by - 0.3, val, ha="center", fontsize=18, fontweight="bold", color=color
            )

        # Total ROI
        ax_main.text(
            5,
            1.0,
            f"Total Program Value: ${total_roi:,.0f}/year",
            fontsize=22,
            fontweight="bold",
            color="#1E3D59",
            ha="center",
        )

    ctx.results["impact_s3"] = {
        "true_lift": true_lift,
        "annual_program_value": annual_program,
        "retention_value": retention_value,
        "total_program_roi": total_roi,
    }

    return [
        AnalysisResult(
            slide_id="S3",
            title="The Mailer Program Works",
            chart_path=save_to,
            notes=(
                f"Spend lift: +${true_lift:,.0f}/acct | "
                f"IC: ${annual_program:,.0f}/yr | "
                f"Retention: ${retention_value:,.0f} | "
                f"Total: ${total_roi:,.0f}"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# S4 -- Branch Performance Gap
# ---------------------------------------------------------------------------


def _branch_gap(ctx: PipelineContext) -> list[AnalysisResult]:
    """Best branch: X% DCTR. Worst: Y%. Gap = $Z if bottom matched median."""
    d9 = get_dctr_9(ctx)
    d1 = get_dctr_1(ctx)
    v1 = get_value_1(ctx)
    a3 = get_a3(ctx)

    best_dctr = d9.get("best_dctr", 0)
    worst_dctr = d9.get("worst_dctr", 0)
    best_branch = d9.get("best_branch", "")
    worst_branch = d9.get("worst_branch", "")
    total_accounts = a3.get("eligible_accounts", d1.get("total_accounts", 0))
    delta = v1["delta"]

    if best_dctr == 0 and worst_dctr == 0:
        return [
            AnalysisResult(
                slide_id="S4",
                title="Branch Performance Gap",
                success=False,
                error="No branch DCTR data",
            )
        ]

    spread = best_dctr - worst_dctr
    median_dctr = (best_dctr + worst_dctr) / 2
    gap_accounts = round(total_accounts * (median_dctr - worst_dctr))
    gap_revenue = gap_accounts * delta

    save_to = ctx.paths.charts_dir / "s4_branch_gap.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
        labels = [
            f"Best: {best_branch}",
            "Median",
            f"Worst: {worst_branch}",
        ]
        values = [best_dctr * 100, median_dctr * 100, worst_dctr * 100]
        colors = [POSITIVE, TEAL, NEGATIVE]

        bars = ax.barh(
            labels[::-1],
            values[::-1],
            color=colors[::-1],
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            height=0.5,
        )

        for bar, val in zip(bars, values[::-1]):
            cx = bar.get_width()
            cy = bar.get_y() + bar.get_height() / 2
            ax.text(
                cx + 1,
                cy,
                f"{val:.1f}%",
                ha="left",
                va="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )

        ax.set_title(
            "Branch DCTR Gap: $ per Percentage Point",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("DCTR (%)", fontsize=20)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
        ax.tick_params(labelsize=TICK_SIZE)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.text(
            max(values) * 0.5,
            -0.8,
            f"If bottom branches matched median: "
            f"+{gap_accounts:,} debit accounts = +${gap_revenue:,.0f}/year",
            ha="center",
            fontsize=14,
            fontweight="bold",
            color=TEAL,
            transform=ax.get_xaxis_transform(),
        )
        fig.tight_layout()

    ctx.results["impact_s4"] = {
        "branch_gap_revenue": gap_revenue,
        "spread": spread,
    }

    return [
        AnalysisResult(
            slide_id="S4",
            title="Branch Performance Gap",
            chart_path=save_to,
            notes=(
                f"Spread: {spread:.1%} ({best_branch} vs {worst_branch}) | "
                f"Gap revenue: ${gap_revenue:,.0f}"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# S5 -- The Debit Card Cascade
# ---------------------------------------------------------------------------


def _debit_cascade(ctx: PipelineContext) -> list[AnalysisResult]:
    """One debit card = interchange + Reg E eligibility + retention = $Total."""
    v1 = get_value_1(ctx)
    v2 = get_value_2(ctx)
    re1 = get_reg_e_1(ctx)
    a9 = get_attrition_9(ctx)
    a11 = get_attrition_11(ctx)

    stream_1 = v1["delta"]  # Interchange delta per account
    opt_in_rate = re1.get("opt_in_rate", 0)
    stream_2 = v2["delta"] * opt_in_rate  # Reg E delta weighted by probability
    retention_lift = a9["retention_lift"]
    avg_lost = a11["avg_lost"]
    stream_3 = retention_lift * avg_lost  # Retention value per activation
    total_cascade = stream_1 + stream_2 + stream_3

    if total_cascade == 0:
        return [
            AnalysisResult(
                slide_id="S5",
                title="The Debit Card Cascade",
                success=False,
                error="No cascade data",
            )
        ]

    save_to = ctx.paths.charts_dir / "s5_debit_cascade.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 8), save_path=save_to) as (fig, ax):
        # Vertical stacked waterfall
        streams = [
            ("Interchange\nRevenue", stream_1, TEAL),
            ("Reg E\nEligibility", stream_2, "#1E3D59"),
            ("Retention\nValue", stream_3, POSITIVE),
        ]

        x = np.arange(len(streams) + 1)
        bottom = 0
        for i, (label, val, color) in enumerate(streams):
            ax.bar(
                i, val, bottom=bottom, color=color, edgecolor=BAR_EDGE, alpha=BAR_ALPHA, width=0.5
            )
            ax.text(
                i,
                bottom + val / 2,
                f"${val:,.2f}",
                ha="center",
                va="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
                color="white",
            )
            bottom += val

        # Total bar
        ax.bar(
            len(streams),
            total_cascade,
            color="#D4A574",
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        ax.text(
            len(streams),
            total_cascade / 2,
            f"${total_cascade:,.2f}",
            ha="center",
            va="center",
            fontsize=DATA_LABEL_SIZE,
            fontweight="bold",
            color="white",
        )

        labels = [s[0] for s in streams] + ["Total\nper Activation"]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=TICK_SIZE - 2)
        ax.set_title(
            "One Debit Card = Three Revenue Streams",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Annual Value per Account ($)", fontsize=20)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.2f}"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()

    ctx.results["impact_s5"] = {
        "stream_1": stream_1,
        "stream_2": stream_2,
        "stream_3": stream_3,
        "total_cascade": total_cascade,
    }

    return [
        AnalysisResult(
            slide_id="S5",
            title="The Debit Card Cascade",
            chart_path=save_to,
            notes=(
                f"IC: ${stream_1:,.2f} + Reg E: ${stream_2:,.2f} "
                f"+ Retention: ${stream_3:,.2f} = ${total_cascade:,.2f}/activation"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class InsightsSynthesis(AnalysisModule):
    """Impact synthesis -- dollar narratives from upstream module results."""

    module_id = "insights.synthesis"
    display_name = "Impact Story: Synthesis"
    section = "insights"
    required_columns = ()  # Reads ctx.results, not ctx.data columns

    def validate(self, ctx: PipelineContext) -> list[str]:
        """No column requirements -- reads ctx.results from upstream modules."""
        return []

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Impact Synthesis for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(_revenue_gap, "S1", ctx)
        results += _safe(_cost_of_attrition, "S2", ctx)
        results += _safe(_mailer_roi, "S3", ctx)
        results += _safe(_branch_gap, "S4", ctx)
        results += _safe(_debit_cascade, "S5", ctx)
        return results
