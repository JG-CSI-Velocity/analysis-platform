"""DCTR Funnel Analysis -- account funnels and eligible vs non-eligible.

Slide IDs: A7.7, A7.8, A7.9.
"""

from __future__ import annotations

import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import filter_l12m
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE
from ars_analysis.pipeline.context import PipelineContext


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(slide_id=label, title=label, success=False, error=str(exc))]


@register
class DCTRFunnel(AnalysisModule):
    """DCTR funnel analyses -- account eligibility funnels and comparisons."""

    module_id = "dctr.funnel"
    display_name = "DCTR Funnel Analysis"
    section = "dctr"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("DCTR Funnel for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._historical_funnel, "A7.7", ctx)
        results += _safe(self._l12m_funnel, "A7.8", ctx)
        results += _safe(self._eligible_vs_non, "A7.9", ctx)
        return results

    # -- A7.7: Historical Account & Debit Card Funnel -------------------------

    def _historical_funnel(self, ctx: PipelineContext) -> list[AnalysisResult]:
        data = ctx.data
        oa = ctx.subsets.open_accounts
        ed = ctx.subsets.eligible_data
        ewd = ctx.subsets.eligible_with_debit
        if data is None or oa is None or ed is None or ewd is None:
            return []

        ta = len(data)
        to_ = len(oa)
        te = len(ed)
        td = len(ewd)
        if ta == 0:
            return []
        through = td / ta * 100
        dctr_e = td / te * 100 if te else 0

        funnel_df = pd.DataFrame([
            {"Stage": "Total Accounts", "Count": ta, "Pct of Total": 100},
            {"Stage": "Open Accounts", "Count": to_, "Pct of Total": to_ / ta * 100},
            {"Stage": "Eligible Accounts", "Count": te, "Pct of Total": te / ta * 100},
            {"Stage": "With Debit Card", "Count": td, "Pct of Total": through},
        ])

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_funnel.png"
            try:
                chart_path = self._draw_funnel(
                    save_to, ta, to_, te, td, data, oa, ed, ewd,
                    "Historical Account & Debit Card Funnel", "All-Time Analysis",
                    ctx.results,
                )
            except Exception as exc:
                logger.warning("A7.7 chart failed: {err}", err=exc)

        ctx.results["dctr_funnel"] = {"through_rate": through, "dctr_eligible": dctr_e}
        return [AnalysisResult(
            slide_id="A7.7",
            title="Historical Account & Debit Card Funnel",
            chart_path=chart_path,
            excel_data={"Funnel": funnel_df},
            notes=f"{ta:,} -> {to_:,} -> {te:,} -> {td:,} | Through: {through:.1f}%",
        )]

    # -- A7.8: L12M Funnel ---------------------------------------------------

    def _l12m_funnel(self, ctx: PipelineContext) -> list[AnalysisResult]:
        data = ctx.data
        oa = ctx.subsets.open_accounts
        ed = ctx.subsets.eligible_data
        if data is None or ed is None or ctx.start_date is None or ctx.end_date is None:
            return []

        sd, ed_date = ctx.start_date, ctx.end_date

        dc = data.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
        l12m_all = dc[(dc["Date Opened"] >= str(sd)) & (dc["Date Opened"] <= str(ed_date))]

        l12m_open = filter_l12m(oa, sd, ed_date) if oa is not None else pd.DataFrame()
        l12m_elig = filter_l12m(ed, sd, ed_date) if ed is not None else pd.DataFrame()
        l12m_debit = l12m_elig[l12m_elig["Debit?"] == "Yes"] if not l12m_elig.empty else pd.DataFrame()

        ta = len(l12m_all)
        to_ = len(l12m_open)
        te = len(l12m_elig)
        td = len(l12m_debit)
        if ta == 0:
            return []
        through = td / ta * 100
        dctr_e = td / te * 100 if te else 0

        funnel_df = pd.DataFrame([
            {"Stage": "Total TTM Accounts", "Count": ta, "Pct of Total": 100},
            {"Stage": "Open Accounts", "Count": to_, "Pct of Total": to_ / ta * 100},
            {"Stage": "Eligible Accounts", "Count": te, "Pct of Total": te / ta * 100},
            {"Stage": "With Debit Card", "Count": td, "Pct of Total": through},
        ])

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_l12m_funnel.png"
            try:
                chart_path = self._draw_funnel(
                    save_to, ta, to_, te, td, l12m_all, l12m_open, l12m_elig, l12m_debit,
                    "TTM Account & Debit Card Funnel",
                    f"{sd.strftime('%B %Y')} - {ed_date.strftime('%B %Y')}",
                    ctx.results,
                )
            except Exception as exc:
                logger.warning("A7.8 chart failed: {err}", err=exc)

        ctx.results["dctr_l12m_funnel"] = {"through": through, "dctr": dctr_e}
        return [AnalysisResult(
            slide_id="A7.8",
            title="TTM Account & Debit Card Funnel",
            chart_path=chart_path,
            excel_data={"L12M Funnel": funnel_df},
            notes=f"{ta:,} -> {to_:,} -> {te:,} -> {td:,} | Through: {through:.1f}%",
        )]

    # -- A7.9: Eligible vs Non-Eligible DCTR ----------------------------------

    def _eligible_vs_non(self, ctx: PipelineContext) -> list[AnalysisResult]:
        oa = ctx.subsets.open_accounts
        ed = ctx.subsets.eligible_data
        if oa is None or ed is None or oa.empty or ed.empty:
            return []
        if ctx.start_date is None or ctx.end_date is None:
            return []

        sd, ed_date = ctx.start_date, ctx.end_date
        l12m_open = filter_l12m(oa, sd, ed_date)
        l12m_elig = filter_l12m(ed, sd, ed_date)
        if l12m_elig.empty:
            return []

        non_elig = l12m_open[~l12m_open.index.isin(l12m_elig.index)] if not l12m_open.empty else pd.DataFrame()

        e_total = len(l12m_elig)
        e_debit = len(l12m_elig[l12m_elig["Debit?"] == "Yes"])
        e_dctr = (e_debit / e_total * 100) if e_total > 0 else 0

        n_total = len(non_elig)
        n_debit = len(non_elig[non_elig["Debit?"] == "Yes"]) if not non_elig.empty else 0
        n_dctr = (n_debit / n_total * 100) if n_total > 0 else 0

        gap = e_dctr - n_dctr

        comp_df = pd.DataFrame([
            {"Account Type": "Eligible", "Total": e_total, "With Debit": e_debit, "DCTR %": e_dctr / 100},
            {"Account Type": "Non-Eligible", "Total": n_total, "With Debit": n_debit, "DCTR %": n_dctr / 100},
        ])

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_eligible_vs_non.png"
            try:
                with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
                    categories = ["Eligible\nAccounts", "Non-Eligible\nAccounts"]
                    dctr_vals = [e_dctr, n_dctr]
                    colors = [POSITIVE, NEGATIVE]
                    bars = ax.bar(categories, dctr_vals, color=colors, edgecolor="black", linewidth=2, alpha=0.8)
                    for bar, d in zip(bars, dctr_vals):
                        ax.text(bar.get_x() + bar.get_width() / 2, d + 1, f"{d:.1f}%",
                                ha="center", va="bottom", fontsize=24, fontweight="bold")
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title("TTM: Eligible vs Non-Eligible DCTR", fontsize=24, fontweight="bold", pad=20)
                    ax.set_ylim(0, max(dctr_vals) * 1.15 if max(dctr_vals) > 0 else 100)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.tick_params(axis="both", labelsize=20)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.9 chart failed: {err}", err=exc)

        ctx.results["dctr_elig_vs_non"] = {"eligible_dctr": e_dctr, "non_eligible_dctr": n_dctr, "gap": gap}
        return [AnalysisResult(
            slide_id="A7.9",
            title="Eligible vs Non-Eligible DCTR",
            chart_path=chart_path,
            excel_data={"Comparison": comp_df},
            notes=f"Eligible: {e_dctr:.1f}% | Non-Eligible: {n_dctr:.1f}% | Gap: {gap:+.1f}pp",
        )]

    # -- Shared funnel drawing ------------------------------------------------

    @staticmethod
    def _draw_funnel(
        save_to, ta, to_, te, td, data_all, data_open, data_elig, data_debit,
        title: str, subtitle: str, results: dict,
    ):
        """Draw a proportional funnel chart and return the save path."""
        has_biz = "Business?" in data_all.columns and len(data_all[data_all["Business?"] == "Yes"]) > 0

        tp = len(data_all[data_all["Business?"] == "No"]) if has_biz else ta
        tb = ta - tp if has_biz else 0
        op = len(data_open[data_open["Business?"] == "No"]) if has_biz and not data_open.empty else to_
        ob = to_ - op if has_biz else 0
        ep_cnt = len(data_elig[data_elig["Business?"] == "No"]) if has_biz and not data_elig.empty else te
        eb_cnt = te - ep_cnt if has_biz else 0
        dp = len(data_debit[data_debit["Business?"] == "No"]) if has_biz and not data_debit.empty else td
        db_cnt = td - dp if has_biz else 0

        stages = [
            {"name": "Total\nAccounts", "total": ta, "personal": tp, "business": tb, "color": "#1f77b4"},
            {"name": "Open\nAccounts", "total": to_, "personal": op, "business": ob, "color": "#2c7fb8"},
            {"name": "Eligible\nAccounts", "total": te, "personal": ep_cnt, "business": eb_cnt, "color": "#ff7f0e"},
            {"name": "Eligible With\nDebit Card", "total": td, "personal": dp, "business": db_cnt, "color": "#41b6c4"},
        ]

        with chart_figure(figsize=(12, 10), save_path=save_to) as (fig, ax):
            ax.set_facecolor("#f8f9fa")
            max_width = 0.8
            stage_height = 0.15
            y_start = 0.85
            stage_gap = 0.02
            current_y = y_start

            for i, stage in enumerate(stages):
                width = max_width * (stage["total"] / stages[0]["total"]) if stages[0]["total"] > 0 else 0.1

                if has_biz and stage["total"] > 0:
                    p_ratio = stage["personal"] / stage["total"]
                    p_width = width * p_ratio
                    b_width = width * (1 - p_ratio)
                    rect_p = mpatches.FancyBboxPatch(
                        (0.5 - width / 2, current_y - stage_height), p_width, stage_height,
                        boxstyle="round,pad=0.01", facecolor=stage["color"],
                        edgecolor="white", linewidth=2, alpha=0.9)
                    ax.add_patch(rect_p)
                    rgb = mcolors.hex2color(stage["color"])
                    darker = mcolors.rgb2hex(tuple(c * 0.7 for c in rgb))
                    rect_b = mpatches.FancyBboxPatch(
                        (0.5 - width / 2 + p_width, current_y - stage_height), b_width, stage_height,
                        boxstyle="round,pad=0.01", facecolor=darker,
                        edgecolor="white", linewidth=2, alpha=0.9)
                    ax.add_patch(rect_b)
                    if p_width > 0.05:
                        ax.text(0.5 - width / 2 + p_width / 2, current_y - stage_height / 2,
                                f"{stage['personal']:,}", ha="center", va="center",
                                fontsize=20, color="white", fontweight="bold")
                    if b_width > 0.05:
                        ax.text(0.5 - width / 2 + p_width + b_width / 2, current_y - stage_height / 2,
                                f"{stage['business']:,}", ha="center", va="center",
                                fontsize=20, color="white", fontweight="bold")
                    ax.text(0.5 + width / 2 + 0.05, current_y - stage_height / 2,
                            f"Total\n{stage['total']:,}", ha="left", va="center",
                            fontsize=18, fontweight="bold", color="black",
                            bbox={"boxstyle": "round,pad=0.4", "facecolor": "white",
                                  "edgecolor": "black", "alpha": 0.9})
                else:
                    rect = mpatches.FancyBboxPatch(
                        (0.5 - width / 2, current_y - stage_height), width, stage_height,
                        boxstyle="round,pad=0.01", facecolor=stage["color"],
                        edgecolor="white", linewidth=3, alpha=0.9)
                    ax.add_patch(rect)
                    ax.text(0.5, current_y - stage_height / 2, f"{stage['total']:,}",
                            ha="center", va="center", fontsize=28, fontweight="bold",
                            color="white", zorder=10)

                ax.text(0.5 - width / 2 - 0.05, current_y - stage_height / 2,
                        stage["name"], ha="right", va="center",
                        fontsize=20, fontweight="600", color="#2c3e50")

                if i > 0 and stages[i - 1]["total"] > 0:
                    conv = stage["total"] / stages[i - 1]["total"] * 100
                    arrow_y = current_y + stage_gap / 2
                    ax.annotate("", xy=(0.5, arrow_y - stage_gap + 0.01),
                                xytext=(0.5, arrow_y - 0.01),
                                arrowprops={"arrowstyle": "->", "lw": 3, "color": "#e74c3c"})
                    ax.text(0.45, arrow_y - stage_gap / 2, f"{conv:.1f}%",
                            ha="center", va="center", fontsize=18, fontweight="bold",
                            color="#e74c3c",
                            bbox={"boxstyle": "round,pad=0.3", "facecolor": "white",
                                  "edgecolor": "#e74c3c", "alpha": 0.9})

                current_y -= (stage_height + stage_gap)

            ax.text(0.5, 0.98, title, ha="center", va="top", fontsize=28, fontweight="bold",
                    color="#1e3d59", transform=ax.transAxes)
            ax.text(0.5, 0.93, subtitle, ha="center", va="top", fontsize=20, style="italic",
                    color="#7f8c8d", transform=ax.transAxes)

            if has_biz:
                legend_elements = [
                    mpatches.Patch(facecolor="#808080", edgecolor="black", label="Personal (Lighter shade)"),
                    mpatches.Patch(facecolor="#404040", edgecolor="black", label="Business (Darker shade)"),
                ]
                ax.legend(handles=legend_elements, loc="lower right", fontsize=16, frameon=True, fancybox=True)

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

        return save_to
