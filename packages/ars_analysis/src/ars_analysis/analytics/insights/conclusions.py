"""Impact Conclusions -- S6 through S8.

S6  Combined Opportunity Map (all dollar opportunities in one view)
S7  What If: +5 Points of DCTR (scenario analysis)
S8  Executive Summary (three actions, three payoffs, one total)
"""

from __future__ import annotations

import numpy as np
from loguru import logger
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.insights._data import (
    _safe,
    get_attrition_9,
    get_attrition_11,
    get_dctr_1,
    get_dctr_9,
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

CAPTURE_RATE = 0.25  # Near-term realistic capture


# ---------------------------------------------------------------------------
# S6 -- Combined Opportunity Map
# ---------------------------------------------------------------------------


def _opportunity_map(ctx: PipelineContext) -> list[AnalysisResult]:
    """Every dollar opportunity in one view. Addressable vs realistic."""
    v1 = get_value_1(ctx)
    v2 = get_value_2(ctx)
    a9 = get_attrition_9(ctx)
    a11 = get_attrition_11(ctx)
    ra = get_revenue_attribution(ctx)

    # Four buckets at max scenario
    debit_max = v1["pot_100"]
    rege_max = v2["pot_100"]
    retention_max = a9["retention_lift"] * a11.get("total_lost", 0) if a11["total_lost"] > 0 else 0
    mailer_max = ra["incremental_total"] * 12

    total_addressable = debit_max + rege_max + retention_max + mailer_max

    # Realistic scenario
    debit_real = v1.get("pot_l12m", debit_max * CAPTURE_RATE)
    rege_real = v2.get("pot_l12m", rege_max * CAPTURE_RATE)
    retention_real = retention_max * CAPTURE_RATE
    mailer_real = mailer_max  # Program already running

    total_realistic = debit_real + rege_real + retention_real + mailer_real

    if total_addressable == 0:
        return [
            AnalysisResult(
                slide_id="S6",
                title="Combined Opportunity Map",
                success=False,
                error="No opportunity data",
            )
        ]

    save_to = ctx.paths.charts_dir / "s6_opportunity_map.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(16, 8), save_path=save_to) as (fig, ax):
        categories = ["Addressable (Max)", "Realistic (Near-Term)"]
        buckets = [
            ("Debit Cards", TEAL),
            ("Reg E Opt-In", "#1E3D59"),
            ("Retention", POSITIVE),
            ("Mailer Program", "#D4A574"),
        ]
        addressable_vals = [debit_max, rege_max, retention_max, mailer_max]
        realistic_vals = [debit_real, rege_real, retention_real, mailer_real]

        y = np.arange(2)
        left_a = 0
        left_r = 0
        for i, ((label, color), a_val, r_val) in enumerate(
            zip(buckets, addressable_vals, realistic_vals),
        ):
            ax.barh(
                1,
                a_val,
                left=left_a,
                height=0.4,
                color=color,
                edgecolor=BAR_EDGE,
                alpha=BAR_ALPHA,
                label=label if i < 4 else "",
            )
            ax.barh(0, r_val, left=left_r, height=0.4, color=color, edgecolor=BAR_EDGE, alpha=0.65)
            left_a += a_val
            left_r += r_val

        # Total labels
        ax.text(
            total_addressable + total_addressable * 0.02,
            1,
            f"${total_addressable:,.0f}",
            va="center",
            fontsize=DATA_LABEL_SIZE,
            fontweight="bold",
            color="#1E3D59",
        )
        ax.text(
            total_realistic + total_addressable * 0.02,
            0,
            f"${total_realistic:,.0f}",
            va="center",
            fontsize=DATA_LABEL_SIZE,
            fontweight="bold",
            color=POSITIVE,
        )

        ax.set_yticks(y)
        ax.set_yticklabels(categories[::-1], fontsize=TICK_SIZE)
        ax.set_title(
            "Combined Opportunity Map",
            fontsize=24,
            fontweight="bold",
            pad=15,
        )
        ax.set_xlabel("Annual Revenue ($)", fontsize=20)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
        ax.tick_params(labelsize=TICK_SIZE - 2)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=14, loc="lower right")
        fig.tight_layout()

    ctx.results["impact_s6"] = {
        "total_addressable": total_addressable,
        "total_realistic": total_realistic,
    }

    return [
        AnalysisResult(
            slide_id="S6",
            title="Combined Opportunity Map",
            chart_path=save_to,
            notes=(f"Addressable: ${total_addressable:,.0f} | Realistic: ${total_realistic:,.0f}"),
        )
    ]


# ---------------------------------------------------------------------------
# S7 -- What If: +5 Points of DCTR
# ---------------------------------------------------------------------------


def _what_if_dctr(ctx: PipelineContext) -> list[AnalysisResult]:
    """5pp DCTR lift = X accounts = cascade revenue. Best branch proof point."""
    d1 = get_dctr_1(ctx)
    d9 = get_dctr_9(ctx)
    v1 = get_value_1(ctx)
    v2 = get_value_2(ctx)
    re1 = get_reg_e_1(ctx)
    a9 = get_attrition_9(ctx)
    a11 = get_attrition_11(ctx)

    current_dctr = d1.get("overall_dctr", 0)
    total_accounts = d1.get("total_accounts", 0)
    best_dctr = d9.get("best_dctr", 0)
    delta_ic = v1["delta"]
    delta_rege = v2["delta"]
    opt_in = re1.get("opt_in_rate", 0)
    retention_lift = a9["retention_lift"]
    avg_lost = a11["avg_lost"]

    if total_accounts == 0:
        return [
            AnalysisResult(
                slide_id="S7",
                title="What If: +5 Points of DCTR",
                success=False,
                error="No DCTR data",
            )
        ]

    target_dctr = current_dctr + 0.05
    new_accounts = round(total_accounts * 0.05)
    ic_gain = new_accounts * delta_ic
    rege_gain = new_accounts * delta_rege * opt_in
    retention_gain = new_accounts * retention_lift * avg_lost
    total_gain = ic_gain + rege_gain + retention_gain

    save_to = ctx.paths.charts_dir / "s7_what_if.png"
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
            "What If: +5 Percentage Points of DCTR",
            fontsize=24,
            fontweight="bold",
            color="#1E3D59",
            ha="center",
        )

        # Before/After columns
        col_x = [2.5, 7.5]
        headers = ["Current State", "With +5pp DCTR"]
        header_colors = [NEGATIVE, POSITIVE]

        for x, header, color in zip(col_x, headers, header_colors):
            ax_main.text(x, 8.5, header, fontsize=18, fontweight="bold", color=color, ha="center")

        rows = [
            ("DCTR", f"{current_dctr:.1%}", f"{target_dctr:.1%}"),
            ("New Debit Accounts", "-", f"+{new_accounts:,}"),
            ("IC Revenue Gain", "-", f"+${ic_gain:,.0f}"),
            ("Reg E Revenue Gain", "-", f"+${rege_gain:,.0f}"),
            ("Retention Value", "-", f"+${retention_gain:,.0f}"),
        ]

        for i, (label, before, after) in enumerate(rows):
            y = 7.2 - i * 1.2
            ax_main.text(0.3, y, label, fontsize=14, color="#666", va="center")
            ax_main.text(
                2.5,
                y,
                before,
                fontsize=16,
                fontweight="bold",
                color="#666",
                ha="center",
                va="center",
            )
            ax_main.text(
                7.5,
                y,
                after,
                fontsize=16,
                fontweight="bold",
                color=POSITIVE,
                ha="center",
                va="center",
            )

        # Total row
        ax_main.plot([0.3, 9.7], [1.5, 1.5], color="#999", linewidth=1.5)
        ax_main.text(
            0.3,
            1.0,
            "Total Annual Gain",
            fontsize=16,
            fontweight="bold",
            color="#1E3D59",
            va="center",
        )
        ax_main.text(
            7.5,
            1.0,
            f"+${total_gain:,.0f}",
            fontsize=22,
            fontweight="bold",
            color=POSITIVE,
            ha="center",
            va="center",
        )

        if best_dctr > target_dctr:
            ax_main.text(
                5,
                0.0,
                f"Your best branch ({d9.get('best_branch', '')}) "
                f"already exceeds this target at {best_dctr:.1%}",
                fontsize=12,
                color=TEAL,
                ha="center",
                style="italic",
            )

    ctx.results["impact_s7"] = {
        "new_debit_accounts": new_accounts,
        "total_annual_gain": total_gain,
    }

    return [
        AnalysisResult(
            slide_id="S7",
            title="What If: +5 Points of DCTR",
            chart_path=save_to,
            notes=(
                f"+{new_accounts:,} accounts = "
                f"${ic_gain:,.0f} IC + ${rege_gain:,.0f} Reg E "
                f"+ ${retention_gain:,.0f} retention = ${total_gain:,.0f}/year"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# S8 -- Executive Summary
# ---------------------------------------------------------------------------


def _executive_summary(ctx: PipelineContext) -> list[AnalysisResult]:
    """Three actions. Three payoffs. Combined total."""
    v1 = get_value_1(ctx)
    v2 = get_value_2(ctx)
    ra = get_revenue_attribution(ctx)

    action_1 = v1.get("pot_l12m", 0)  # Debit card opportunity
    action_2 = v2.get("pot_l12m", 0)  # Reg E opportunity
    action_3 = ra["incremental_total"] * 12  # Mailer annual
    combined = action_1 + action_2 + action_3

    if combined == 0:
        return [
            AnalysisResult(
                slide_id="S8",
                title="Executive Summary",
                success=False,
                error="No opportunity data",
            )
        ]

    save_to = ctx.paths.charts_dir / "s8_executive_summary.png"
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
            "Three Actions. Three Payoffs. One Goal.",
            fontsize=24,
            fontweight="bold",
            color="#1E3D59",
            ha="center",
        )

        d1 = get_dctr_1(ctx)
        re1 = get_reg_e_1(ctx)

        actions = [
            (
                "Activate Debit Cards",
                f"Current DCTR: {d1.get('overall_dctr', 0):.0%}",
                f"${action_1:,.0f}/year",
                TEAL,
            ),
            (
                "Increase Reg E Opt-In",
                f"Current Rate: {re1.get('opt_in_rate', 0):.0%}",
                f"${action_2:,.0f}/year",
                "#1E3D59",
            ),
            (
                "Expand Mailer Program",
                "Proven Incremental IC",
                f"${action_3:,.0f}/year",
                POSITIVE,
            ),
        ]

        for i, (action, metric, payoff, color) in enumerate(actions):
            y = 7.5 - i * 2.2
            rect = FancyBboxPatch(
                (0.5, y - 0.7),
                9,
                1.6,
                boxstyle="round,pad=0.15",
                facecolor=color,
                alpha=0.08,
                edgecolor=color,
                linewidth=2,
            )
            ax_main.add_patch(rect)

            ax_main.text(0.8, y + 0.3, f"{i + 1}.", fontsize=20, fontweight="bold", color=color)
            ax_main.text(1.5, y + 0.3, action, fontsize=16, fontweight="bold", color=color)
            ax_main.text(1.5, y - 0.2, metric, fontsize=13, color="#666")
            ax_main.text(
                9.2, y, payoff, fontsize=20, fontweight="bold", color=color, ha="right", va="center"
            )

        # Combined total
        rect_total = FancyBboxPatch(
            (2.0, 0.2),
            6,
            1.2,
            boxstyle="round,pad=0.15",
            facecolor="#D4A574",
            alpha=0.15,
            edgecolor="#D4A574",
            linewidth=3,
        )
        ax_main.add_patch(rect_total)
        ax_main.text(
            5,
            0.8,
            f"Combined Opportunity: ${combined:,.0f}/year",
            fontsize=22,
            fontweight="bold",
            color="#1E3D59",
            ha="center",
        )

    ctx.results["impact_s8"] = {
        "action_1": action_1,
        "action_2": action_2,
        "action_3": action_3,
        "combined": combined,
    }

    return [
        AnalysisResult(
            slide_id="S8",
            title="Executive Summary",
            chart_path=save_to,
            notes=(
                f"Debit: ${action_1:,.0f} + Reg E: ${action_2:,.0f} "
                f"+ Mailer: ${action_3:,.0f} = ${combined:,.0f}/year"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class InsightsConclusions(AnalysisModule):
    """Impact conclusions -- opportunity map, scenario, executive summary."""

    module_id = "insights.conclusions"
    display_name = "Impact Story: Conclusions"
    section = "insights"
    required_columns = ()

    def validate(self, ctx: PipelineContext) -> list[str]:
        """No column requirements -- reads ctx.results from upstream modules."""
        return []

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info(
            "Impact Conclusions for {client}",
            client=ctx.client.client_id,
        )
        results: list[AnalysisResult] = []
        results += _safe(_opportunity_map, "S6", ctx)
        results += _safe(_what_if_dctr, "S7", ctx)
        results += _safe(_executive_summary, "S8", ctx)
        return results
