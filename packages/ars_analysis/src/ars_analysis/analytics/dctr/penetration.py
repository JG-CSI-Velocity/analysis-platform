"""DCTR Penetration -- core historical, L12M, P/B, and summary analyses.

Slide IDs: DCTR-1 through DCTR-8, A7.1, A7.2, A7.3, A7 combo.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import (
    analyze_historical_dctr,
    filter_l12m,
    l12m_month_labels,
    l12m_monthly,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import (
    BUSINESS,
    ELIGIBLE,
    HISTORICAL,
    PERSONAL,
    TTM,
)
from ars_analysis.pipeline.context import PipelineContext


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run analysis function, catch errors, return failed result on exception."""
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(
            slide_id=label, title=label, success=False, error=str(exc),
        )]


@register
class DCTRPenetration(AnalysisModule):
    """Core DCTR penetration rates -- historical, L12M, P/B splits, summary."""

    module_id = "dctr.penetration"
    display_name = "DCTR Penetration"
    section = "dctr"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("DCTR Penetration for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._historical, "DCTR-1", ctx)
        results += _safe(self._open_vs_eligible, "DCTR-2", ctx)
        results += _safe(self._l12m, "DCTR-3", ctx)
        results += _safe(self._personal_business, "DCTR-4/5", ctx)
        results += _safe(self._pb_l12m, "DCTR-6/7", ctx)
        results += _safe(self._summary, "DCTR-8", ctx)
        return results

    # -- DCTR-1: Historical DCTR (Eligible) ----------------------------------

    def _historical(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []
        yearly, decade, ins = analyze_historical_dctr(ed, "Eligible")
        ctx.results["dctr_1"] = {"yearly": yearly, "decade": decade, "insights": ins}
        return [AnalysisResult(
            slide_id="DCTR-1",
            title="Historical Debit Card Take Rate",
            excel_data={"Yearly": yearly, "Decade": decade},
            notes=(
                f"Overall: {ins['overall_dctr']:.1%} | "
                f"Recent: {ins['recent_dctr']:.1%} | "
                f"Accounts: {ins['total_accounts']:,}"
            ),
        )]

    # -- DCTR-2: Open vs Eligible + Chart (A7.1) -----------------------------

    def _open_vs_eligible(self, ctx: PipelineContext) -> list[AnalysisResult]:
        oa = ctx.subsets.open_accounts
        ed = ctx.subsets.eligible_data
        if oa is None or ed is None or oa.empty or ed.empty:
            return []

        _, _, open_ins = analyze_historical_dctr(oa, "Open")
        hist_ins = ctx.results.get("dctr_1", {}).get("insights", {})
        if not hist_ins:
            return []

        comparison = pd.DataFrame([
            {"Account Group": "All Open", "Total Accounts": len(oa),
             "With Debit": open_ins["with_debit_count"], "DCTR %": open_ins["overall_dctr"]},
            {"Account Group": "Eligible Only", "Total Accounts": hist_ins["total_accounts"],
             "With Debit": hist_ins["with_debit_count"], "DCTR %": hist_ins["overall_dctr"]},
        ])
        diff = hist_ins["overall_dctr"] - open_ins["overall_dctr"]

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_open_vs_eligible.png"
            try:
                od = open_ins["overall_dctr"] * 100
                ed_v = hist_ins["overall_dctr"] * 100
                with chart_figure(figsize=(10, 6), save_path=save_to) as (fig, ax):
                    bars = ax.bar(
                        ["All Open\nAccounts", "Eligible\nAccounts"],
                        [od, ed_v], color=[ELIGIBLE, PERSONAL],
                        width=0.5, edgecolor="black", linewidth=2, alpha=0.8,
                    )
                    for bar, v, c in zip(bars, [od, ed_v],
                                         [open_ins["with_debit_count"], hist_ins["with_debit_count"]]):
                        ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}%",
                                ha="center", fontweight="bold", fontsize=22)
                        ax.text(bar.get_x() + bar.get_width() / 2, v / 2, f"{c:,}\naccounts",
                                ha="center", fontweight="bold", fontsize=18, color="white")
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title("DCTR: Open vs Eligible Accounts", fontsize=24, fontweight="bold", pad=20)
                    ax.set_ylim(0, max(od, ed_v) * 1.15)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.tick_params(axis="both", labelsize=18)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.1 chart failed: {err}", err=exc)

        ctx.results["dctr_2"] = {
            "comparison": comparison,
            "insights": {
                "open_dctr": open_ins["overall_dctr"],
                "eligible_dctr": hist_ins["overall_dctr"],
                "difference": diff,
                "open_total": len(oa),
                "eligible_total": hist_ins["total_accounts"],
            },
            "chart_path": str(chart_path) if chart_path else None,
        }
        return [AnalysisResult(
            slide_id="DCTR-2",
            title="DCTR: Open vs Eligible",
            chart_path=chart_path,
            excel_data={"Comparison": comparison},
            notes=f"Open: {open_ins['overall_dctr']:.1%} | Eligible: {hist_ins['overall_dctr']:.1%} | Gap: {diff:+.1%}",
        )]

    # -- DCTR-3: Last 12 Months + Chart (A7.3) -------------------------------

    def _l12m(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty or ctx.start_date is None or ctx.end_date is None:
            return []

        el12 = filter_l12m(ed, ctx.start_date, ctx.end_date)
        if el12.empty:
            ctx.results["dctr_3"] = {"insights": {"total_accounts": 0, "dctr": 0}}
            return []

        months = l12m_month_labels(ctx.end_date)
        monthly, l12m_ins = l12m_monthly(el12, months)
        overall = ctx.results.get("dctr_1", {}).get("insights", {}).get("overall_dctr", 0)
        comp = l12m_ins["dctr"] - overall

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_hist_vs_l12m.png"
            try:
                hd = overall * 100
                ld = l12m_ins["dctr"] * 100
                ht = ctx.results.get("dctr_1", {}).get("insights", {}).get("total_accounts", 0)
                lt = l12m_ins["total_accounts"]
                with chart_figure(figsize=(10, 6), save_path=save_to) as (fig, ax):
                    bars = ax.bar(
                        ["Historical\n(All Time)", "Trailing Twelve Months"],
                        [hd, ld], color=[HISTORICAL, TTM],
                        width=0.5, edgecolor="black", linewidth=2, alpha=0.8,
                    )
                    for bar, v, c in zip(bars, [hd, ld], [ht, lt]):
                        ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}%",
                                ha="center", fontweight="bold", fontsize=22)
                        ax.text(bar.get_x() + bar.get_width() / 2, v / 2, f"{c:,}\naccounts",
                                ha="center", fontweight="bold", fontsize=18, color="white")
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title("Historical vs Recent DCTR", fontsize=24, fontweight="bold", pad=20)
                    ax.set_ylim(0, max(hd, ld) * 1.15)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.tick_params(axis="both", labelsize=18)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.3 chart failed: {err}", err=exc)

        l12m_ins["comparison_to_overall"] = comp
        ctx.results["dctr_3"] = {"monthly": monthly, "insights": l12m_ins, "chart_path": str(chart_path) if chart_path else None}
        return [AnalysisResult(
            slide_id="DCTR-3",
            title="Last 12 Months DCTR",
            chart_path=chart_path,
            excel_data={"Monthly": monthly},
            notes=f"L12M: {l12m_ins['dctr']:.1%} ({l12m_ins['total_accounts']:,} accts) | vs Overall: {comp:+.1%}",
        )]

    # -- DCTR-4/5: Personal & Business Historical + Chart (A7.2) ---------------

    def _personal_business(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ep = ctx.subsets.eligible_personal
        eb = ctx.subsets.eligible_business
        if ep is None or ep.empty:
            return []

        p_yr, p_dec, p_ins = analyze_historical_dctr(ep, "Personal")
        ctx.results["dctr_4"] = {"yearly": p_yr, "decade": p_dec, "insights": p_ins}

        has_biz = eb is not None and len(eb) > 0
        if has_biz:
            b_yr, b_dec, b_ins = analyze_historical_dctr(eb, "Business")
            ctx.results["dctr_5"] = {"yearly": b_yr, "decade": b_dec, "insights": b_ins}
        else:
            b_ins = {"total_accounts": 0, "overall_dctr": 0, "with_debit_count": 0}
            ctx.results["dctr_5"] = {"yearly": pd.DataFrame(), "decade": pd.DataFrame(), "insights": b_ins}

        # Chart A7.2
        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_personal_vs_business.png"
            try:
                overall = ctx.results.get("dctr_1", {}).get("insights", {}).get("overall_dctr", 0) * 100
                if has_biz:
                    cats = ["Personal", "Business"]
                    vals = [p_ins["overall_dctr"] * 100, b_ins["overall_dctr"] * 100]
                    colors = [PERSONAL, BUSINESS]
                    cts = [p_ins["with_debit_count"], b_ins["with_debit_count"]]
                else:
                    cats = ["Personal"]
                    vals = [p_ins["overall_dctr"] * 100]
                    colors = [PERSONAL]
                    cts = [p_ins["with_debit_count"]]

                with chart_figure(save_path=save_to) as (fig, ax):
                    bars = ax.bar(cats, vals, color=colors, edgecolor="black", linewidth=2, alpha=0.9, width=0.5)
                    for bar, v, c in zip(bars, vals, cts):
                        ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}%",
                                ha="center", fontweight="bold", fontsize=22)
                        if v > 10:
                            ax.text(bar.get_x() + bar.get_width() / 2, v / 2, f"{c:,}\naccts",
                                    ha="center", fontsize=18, fontweight="bold", color="white")
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title("Personal vs Business DCTR", fontsize=24, fontweight="bold", pad=20)
                    ax.set_ylim(0, max(vals) * 1.15)
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.tick_params(axis="both", labelsize=18)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.set_axisbelow(True)
                    ax.text(0.02, 0.98, f"Overall: {overall:.1f}%", transform=ax.transAxes,
                            fontsize=18, va="top",
                            bbox={"boxstyle": "round,pad=0.3", "facecolor": "#eee", "alpha": 0.8})
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.2 chart failed: {err}", err=exc)

        results = [AnalysisResult(
            slide_id="DCTR-4",
            title="Personal DCTR",
            chart_path=chart_path,
            excel_data={"Yearly": p_yr, "Decade": p_dec},
            notes=f"Personal: {p_ins.get('overall_dctr', 0):.1%} | Business: {b_ins.get('overall_dctr', 0):.1%}",
        )]
        if has_biz:
            results.append(AnalysisResult(
                slide_id="DCTR-5",
                title="Business DCTR",
                excel_data={"Yearly": ctx.results["dctr_5"]["yearly"], "Decade": ctx.results["dctr_5"]["decade"]},
                notes=f"Business: {b_ins.get('overall_dctr', 0):.1%}",
            ))
        return results

    # -- DCTR-6/7: Personal & Business L12M Monthly ---------------------------

    def _pb_l12m(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ep = ctx.subsets.eligible_personal
        eb = ctx.subsets.eligible_business
        if ep is None or ep.empty or ctx.start_date is None or ctx.end_date is None:
            return []

        months = l12m_month_labels(ctx.end_date)
        epl = filter_l12m(ep, ctx.start_date, ctx.end_date)
        pl_monthly, pl_ins = l12m_monthly(epl, months)
        ctx.results["dctr_6"] = {"monthly": pl_monthly, "insights": pl_ins}

        results = [AnalysisResult(
            slide_id="DCTR-6",
            title="Personal L12M DCTR",
            excel_data={"Monthly": pl_monthly},
            notes=f"Personal L12M: {pl_ins['dctr']:.1%} ({pl_ins['total_accounts']:,} accts)",
        )]

        if eb is not None and not eb.empty:
            ebl = filter_l12m(eb, ctx.start_date, ctx.end_date)
            bl_monthly, bl_ins = l12m_monthly(ebl, months)
            ctx.results["dctr_7"] = {"monthly": bl_monthly, "insights": bl_ins}
            results.append(AnalysisResult(
                slide_id="DCTR-7",
                title="Business L12M DCTR",
                excel_data={"Monthly": bl_monthly},
                notes=f"Business L12M: {bl_ins['dctr']:.1%} ({bl_ins['total_accounts']:,} accts)",
            ))

        return results

    # -- DCTR-8: Comprehensive Summary ----------------------------------------

    def _summary(self, ctx: PipelineContext) -> list[AnalysisResult]:
        r = ctx.results
        rows: list[dict] = []

        def _add(label: str, cat: str, ins_key: str, total_k: str = "total_accounts",
                 wd_k: str = "with_debit_count", dctr_k: str = "overall_dctr") -> None:
            ins = r.get(ins_key, {}).get("insights", {})
            if not ins:
                return
            ta = ins.get(total_k, 0)
            if ta == 0:
                return
            wd = ins.get(wd_k, ins.get("with_debit", 0))
            dc = ins.get(dctr_k, ins.get("dctr", 0))
            rows.append({
                "Account Type": label, "Category": cat,
                "Total Accounts": ta, "With Debit": wd,
                "Without Debit": ta - wd, "DCTR %": dc,
            })

        _add("Eligible Accounts", "Overall", "dctr_1")

        # Open accounts from dctr_2
        d2 = r.get("dctr_2", {}).get("insights", {})
        if d2:
            ot = d2.get("open_total", 0)
            od = d2.get("open_dctr", 0)
            if ot > 0:
                ow = int(od * ot)
                rows.append({
                    "Account Type": "Open Accounts (All)", "Category": "Overall",
                    "Total Accounts": ot, "With Debit": ow,
                    "Without Debit": ot - ow, "DCTR %": od,
                })

        # L12M
        d3 = r.get("dctr_3", {}).get("insights", {})
        if d3.get("total_accounts", 0) > 0:
            ta = d3["total_accounts"]
            wd = d3["with_debit"]
            dc = d3["dctr"]
            rows.append({
                "Account Type": "Trailing Twelve Months (All)", "Category": "Time Period",
                "Total Accounts": ta, "With Debit": wd,
                "Without Debit": ta - wd, "DCTR %": dc,
            })

        _add("Personal (Historical)", "Account Type", "dctr_4")
        _add("Business (Historical)", "Account Type", "dctr_5")

        for k, lbl in [("dctr_6", "Personal (TTM)"), ("dctr_7", "Business (TTM)")]:
            ins = r.get(k, {}).get("insights", {})
            if ins.get("total_accounts", 0) > 0:
                ta = ins["total_accounts"]
                wd = ins["with_debit"]
                dc = ins["dctr"]
                rows.append({
                    "Account Type": lbl, "Category": "Time Period",
                    "Total Accounts": ta, "With Debit": wd,
                    "Without Debit": ta - wd, "DCTR %": dc,
                })

        summary = pd.DataFrame(rows)
        ctx.results["dctr_8"] = {"summary": summary}
        return [AnalysisResult(
            slide_id="DCTR-8",
            title="Comprehensive DCTR Summary",
            excel_data={"Summary": summary},
            notes=f"{len(rows)} categories summarized",
        )]
