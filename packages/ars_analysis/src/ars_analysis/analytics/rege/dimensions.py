"""Reg E Dimensional Analysis -- age, product, funnels.

Slide IDs: A8.5, A8.6, A8.7, A8.10, A8.11.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import filter_l12m
from ars_analysis.analytics.rege._helpers import (
    ACCT_AGE_ORDER,
    HOLDER_AGE_ORDER,
    categorize_account_age,
    categorize_holder_age,
    reg_e_base,
    rege,
    total_row,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import ELIGIBLE, HISTORICAL, NEGATIVE, POSITIVE
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


# -- Funnel renderer (matches DCTR funnel style) ----------------------------

_FUNNEL_COLORS = ["#2c7fb8", "#ff7f0e", "#41b6c4", "#2ca02c", "#9467bd"]


def _render_funnel(ax, stages: list[dict], title_text: str, subtitle_text: str,
                   metrics_text: str) -> None:
    """Render a proportional funnel chart.

    stages: list of dicts with keys: name, total, color.
    """
    ax.set_facecolor("#f8f9fa")
    max_width = 0.8
    stage_height = 0.15
    y_start = 0.85
    stage_gap = 0.02
    current_y = y_start

    for i, stage in enumerate(stages):
        width = (max_width * (stage["total"] / stages[0]["total"])
                 if stages[0]["total"] > 0 else 0.1)

        rect = mpatches.FancyBboxPatch(
            (0.5 - width / 2, current_y - stage_height), width, stage_height,
            boxstyle="round,pad=0.01", facecolor=stage["color"],
            edgecolor="white", linewidth=3, alpha=0.9,
        )
        ax.add_patch(rect)

        ax.text(0.5, current_y - stage_height / 2, f"{stage['total']:,}",
                ha="center", va="center", fontsize=20, fontweight="bold",
                color="white", zorder=10)

        ax.text(0.5 - width / 2 - 0.05, current_y - stage_height / 2,
                stage["name"], ha="right", va="center", fontsize=14, fontweight="600",
                color="#2c3e50")

        if i > 0 and stages[i - 1]["total"] > 0:
            conv = stage["total"] / stages[i - 1]["total"] * 100
            arrow_y = current_y + stage_gap / 2
            ax.annotate("", xy=(0.5, arrow_y - stage_gap + 0.01),
                        xytext=(0.5, arrow_y - 0.01),
                        arrowprops={"arrowstyle": "->", "lw": 2, "color": "#e74c3c"})
            ax.text(0.45, arrow_y - stage_gap / 2, f"{conv:.1f}%",
                    ha="center", va="center", fontsize=14, fontweight="bold",
                    color="#e74c3c",
                    bbox={"boxstyle": "round,pad=0.3", "facecolor": "white",
                          "edgecolor": "#e74c3c", "alpha": 0.9})

        current_y -= (stage_height + stage_gap)

    ax.text(0.5, 0.98, title_text, ha="center", va="top", fontsize=20,
            fontweight="bold", color="#1e3d59", transform=ax.transAxes)
    ax.text(0.5, 0.93, subtitle_text, ha="center", va="top", fontsize=14,
            style="italic", color="#7f8c8d", transform=ax.transAxes)
    # End-to-end drop-off annotation
    if len(stages) >= 2 and stages[0]["total"] > 0:
        end_to_end = stages[-1]["total"] / stages[0]["total"] * 100
        metrics_text += f"\nOverall Pass-Through: {end_to_end:.1f}%"

    ax.text(0.02, 0.02, metrics_text, transform=ax.transAxes, fontsize=12,
            ha="left", va="bottom",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#ecf0f1",
                  "edgecolor": "#34495e", "linewidth": 1.5})
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")


@register
class RegEDimensions(AnalysisModule):
    """Reg E dimensional analysis -- age, product, funnels."""

    module_id = "rege.dimensions"
    display_name = "Reg E Dimensional Analysis"
    section = "rege"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Reg E Dimensions for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._account_age, "A8.5", ctx)
        results += _safe(self._holder_age, "A8.6", ctx)
        results += _safe(self._product_code, "A8.7", ctx)
        results += _safe(self._funnel_alltime, "A8.10", ctx)
        results += _safe(self._funnel_l12m, "A8.11", ctx)
        return results

    # -- A8.5: By Account Age -----------------------------------------------

    def _account_age(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.5: Reg E by Account Age")
        base, _, col, opts = reg_e_base(ctx)

        df = base.copy()
        df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce")
        df["Age Days"] = (pd.Timestamp.now() - df["Date Opened"]).dt.days
        df["Age Range"] = df["Age Days"].apply(categorize_account_age)

        rows = []
        for age in ACCT_AGE_ORDER:
            ad = df[df["Age Range"] == age]
            if len(ad) > 0:
                t, oi, r = rege(ad, col, opts)
                rows.append({"Account Age": age, "Total Accounts": t, "Opted In": oi,
                             "Opted Out": t - oi, "Opt-In Rate": r})
        result = pd.DataFrame(rows)
        result = total_row(result, "Account Age")

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_5_reg_e_acct_age.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        chart = result[result["Account Age"] != "TOTAL"].copy()
        overall = result[result["Account Age"] == "TOTAL"]["Opt-In Rate"].iloc[0] * 100

        with chart_figure(figsize=(14, 8), save_path=save_to) as (fig, ax):
            x = range(len(chart))
            rates = chart["Opt-In Rate"] * 100
            colors = [NEGATIVE if r < overall else POSITIVE for r in rates]

            bars = ax.bar(x, rates, color=colors, edgecolor="none")
            for bar, rate, vol in zip(bars, rates, chart["Total Accounts"]):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{rate:.1f}%", ha="center", fontsize=10, fontweight="bold")

            ax.axhline(y=overall, color="red", linestyle="--", linewidth=2, alpha=0.7)
            ax.text(len(chart) - 0.5, overall + 0.3, f"Avg: {overall:.1f}%",
                    ha="right", color="red", fontweight="bold")
            ax.set_xticks(list(x))
            ax.set_xticklabels(chart["Account Age"].tolist(), rotation=30, ha="right")
            ax.set_ylabel("Opt-In Rate (%)")
            ax.set_title("Reg E Opt-In by Account Age", fontweight="bold")
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        chart_path = save_to

        newest = chart.iloc[0]["Opt-In Rate"] if not chart.empty else 0
        oldest = chart.iloc[-1]["Opt-In Rate"] if not chart.empty else 0
        trend = "increasing" if oldest > newest else "decreasing"
        notes = f"Rate {trend}s with age. Newest: {newest:.1%}, Oldest: {oldest:.1%}"

        ctx.results["reg_e_5"] = {"data": result}
        return [AnalysisResult(
            slide_id="A8.5", title="Reg E by Account Age",
            chart_path=chart_path,
            excel_data={"Account Age": result},
            notes=notes,
        )]

    # -- A8.6: By Account Holder Age -----------------------------------------

    def _holder_age(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.6: Reg E by Holder Age")
        base, base_l12m, col, opts = reg_e_base(ctx)

        def by_holder_age(df: pd.DataFrame) -> pd.DataFrame:
            if df is None or df.empty:
                return pd.DataFrame()
            d = df.copy()
            if "Account Holder Age" in d.columns:
                d["Holder Age"] = pd.to_numeric(d["Account Holder Age"], errors="coerce")
            elif "Birth Date" in d.columns:
                d["Birth Date"] = pd.to_datetime(d["Birth Date"], errors="coerce")
                d["Holder Age"] = (pd.Timestamp.now() - d["Birth Date"]).dt.days / 365.25
            elif "Age" in d.columns:
                d["Holder Age"] = pd.to_numeric(d["Age"], errors="coerce")
            else:
                return pd.DataFrame()

            d["Age Group"] = d["Holder Age"].apply(categorize_holder_age)
            age_rows = []
            for ag in HOLDER_AGE_ORDER:
                seg = d[d["Age Group"] == ag]
                if len(seg) > 0:
                    t, oi, r = rege(seg, col, opts)
                    age_rows.append({"Age Group": ag, "Total Accounts": t, "Opted In": oi,
                                     "Opted Out": t - oi, "Opt-In Rate": r})
            res = pd.DataFrame(age_rows)
            return total_row(res, "Age Group") if not res.empty else res

        hist = by_holder_age(base)
        l12m_df = by_holder_age(base_l12m)

        if hist.empty:
            return [AnalysisResult(
                slide_id="A8.6", title="Reg E by Holder Age",
                success=False, error="No holder age data (missing age column)",
            )]

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_6_reg_e_holder_age.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        ch = hist[hist["Age Group"] != "TOTAL"].copy()
        cl = l12m_df[l12m_df["Age Group"] != "TOTAL"].copy() if not l12m_df.empty else pd.DataFrame()

        with chart_figure(figsize=(14, 8), save_path=save_to) as (fig, ax):
            x = np.arange(len(ch))
            w = 0.35
            hist_rates = ch["Opt-In Rate"] * 100
            bars_h = ax.bar(x - w / 2, hist_rates, w, label="Historical",
                            color=HISTORICAL, edgecolor="none")
            for bar, rate in zip(bars_h, hist_rates):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{rate:.1f}%", ha="center", fontsize=9, fontweight="bold")

            if not cl.empty:
                l12m_rates = []
                for ag in ch["Age Group"]:
                    match = cl[cl["Age Group"] == ag]
                    l12m_rates.append(match["Opt-In Rate"].iloc[0] * 100 if not match.empty else 0)
                bars_l = ax.bar(x + w / 2, l12m_rates, w, label="L12M",
                                color=ELIGIBLE, edgecolor="none")
                for bar, rate in zip(bars_l, l12m_rates):
                    if rate > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                                f"{rate:.1f}%", ha="center", fontsize=9, fontweight="bold")

            # Reference line for overall rate
            overall_row = ch if ch.empty else hist[hist["Age Group"] == "TOTAL"]
            if not overall_row.empty:
                ov = overall_row["Opt-In Rate"].iloc[0] * 100
                ax.axhline(y=ov, color="red", linestyle="--", linewidth=2, alpha=0.7)
                ax.text(len(ch) - 0.5, ov + 0.3, f"Avg: {ov:.1f}%",
                        ha="right", color="red", fontweight="bold", fontsize=9)

            ax.set_xticks(x)
            ax.set_xticklabels(ch["Age Group"].tolist(), rotation=30, ha="right")
            ax.set_ylabel("Opt-In Rate (%)")
            ax.set_title("Reg E Opt-In by Account Holder Age", fontweight="bold")
            ax.legend()
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        chart_path = save_to

        best = ch.loc[ch["Opt-In Rate"].idxmax()]
        worst = ch.loc[ch["Opt-In Rate"].idxmin()]
        notes = (
            f"Best: {best['Age Group']} ({best['Opt-In Rate']:.1%}). "
            f"Worst: {worst['Age Group']} ({worst['Opt-In Rate']:.1%})"
        )

        ctx.results["reg_e_6"] = {"historical": hist, "l12m": l12m_df}
        return [AnalysisResult(
            slide_id="A8.6", title="Reg E by Holder Age",
            chart_path=chart_path,
            excel_data={"Holder Age": hist},
            notes=notes,
        )]

    # -- A8.7: By Product Code -----------------------------------------------

    def _product_code(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.7: Reg E by Product Code")
        base, _, col, opts = reg_e_base(ctx)

        pc_col = None
        for candidate in ("Product Code", "Prod Code"):
            if candidate in base.columns:
                pc_col = candidate
                break
        if pc_col is None:
            return [AnalysisResult(
                slide_id="A8.7", title="Reg E by Product Code",
                success=False, error="No Product Code column found",
            )]

        rows = []
        for pc in sorted(base[pc_col].dropna().unique()):
            seg = base[base[pc_col] == pc]
            t, oi, r = rege(seg, col, opts)
            rows.append({"Product Code": pc, "Total Accounts": t, "Opted In": oi,
                         "Opted Out": t - oi, "Opt-In Rate": r})
        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values("Total Accounts", ascending=False)
            result = total_row(result, "Product Code")

        # Chart -- top 15
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_7_reg_e_product.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        chart = result[result["Product Code"] != "TOTAL"].head(15).copy()
        chart = chart.sort_values("Opt-In Rate", ascending=True)
        overall = result[result["Product Code"] == "TOTAL"]["Opt-In Rate"].iloc[0] * 100

        with chart_figure(figsize=(14, max(8, len(chart) * 0.6)), save_path=save_to) as (fig, ax):
            ax.barh(range(len(chart)), chart["Opt-In Rate"] * 100,
                   color=HISTORICAL, edgecolor="none")
            for i, (rate, vol) in enumerate(zip(chart["Opt-In Rate"], chart["Total Accounts"])):
                ax.text(rate * 100 + 0.3, i, f"{rate:.1%} (n={int(vol):,})", va="center")
            ax.axvline(x=overall, color="red", linestyle="--", linewidth=2, alpha=0.7)
            ax.set_yticks(range(len(chart)))
            ax.set_yticklabels(chart["Product Code"].tolist())
            ax.set_xlabel("Opt-In Rate (%)")
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax.set_title("Reg E Opt-In by Product Code (Top 15 by Volume)",
                         fontweight="bold")
        chart_path = save_to

        notes = f"{len(rows)} products. Overall: {overall:.1f}%"
        ctx.results["reg_e_7"] = {"data": result}

        return [AnalysisResult(
            slide_id="A8.7", title="Reg E by Product Code",
            chart_path=chart_path,
            excel_data={"Product Code": result},
            notes=notes,
        )]

    # -- A8.10: All-Time Account Funnel with Reg E ---------------------------

    def _funnel_alltime(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.10: All-Time Funnel (with Reg E)")
        base, _, col, opts = reg_e_base(ctx)

        total_open = len(ctx.subsets.open_accounts) if ctx.subsets.open_accounts is not None else 0
        total_eligible = len(ctx.subsets.eligible_data) if ctx.subsets.eligible_data is not None else 0
        total_with_debit = len(ctx.subsets.eligible_with_debit) if ctx.subsets.eligible_with_debit is not None else 0
        personal_w_debit = len(base)
        personal_w_rege = len(base[base[col].isin(opts)])

        stages = [
            {"name": "Open Accounts", "total": total_open, "color": _FUNNEL_COLORS[0]},
            {"name": "Eligible Accounts", "total": total_eligible, "color": _FUNNEL_COLORS[1]},
            {"name": "Eligible w/Debit", "total": total_with_debit, "color": _FUNNEL_COLORS[2]},
            {"name": "Personal w/Debit", "total": personal_w_debit, "color": _FUNNEL_COLORS[3]},
            {"name": "Personal w/Reg E", "total": personal_w_rege, "color": _FUNNEL_COLORS[4]},
        ]

        funnel_df = pd.DataFrame([{"Stage": s["name"], "Count": s["total"]} for s in stages])

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_10_reg_e_funnel.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        rege_rate = personal_w_rege / personal_w_debit * 100 if personal_w_debit > 0 else 0
        through_rate = personal_w_rege / total_open * 100 if total_open > 0 else 0

        with chart_figure(figsize=(12, 10), save_path=save_to) as (fig, ax):
            _render_funnel(
                ax, stages,
                title_text="All-Time Account Eligibility & Reg E Funnel",
                subtitle_text="All-Time Analysis",
                metrics_text=f"Reg E Rate: {rege_rate:.1f}%\nEnd-to-End: {through_rate:.1f}%",
            )
        chart_path = save_to

        notes = (
            f"Open: {total_open:,} -> Reg E: {personal_w_rege:,} "
            f"({rege_rate:.1f}% of personal w/debit)"
        )

        ctx.results["reg_e_10"] = {"funnel": funnel_df}
        return [AnalysisResult(
            slide_id="A8.10", title="All-Time Funnel with Reg E",
            chart_path=chart_path,
            excel_data={"Funnel": funnel_df},
            notes=notes,
        )]

    # -- A8.11: L12M Funnel with Reg E --------------------------------------

    def _funnel_l12m(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.11: L12M Funnel (with Reg E)")
        _, base_l12m, col, opts = reg_e_base(ctx)

        if base_l12m is None or base_l12m.empty:
            return [AnalysisResult(
                slide_id="A8.11", title="L12M Funnel with Reg E",
                success=False, error="No L12M data available",
            )]

        # Compute L12M stages from subsets
        l12m_data = ctx.subsets.last_12_months
        total_l12m = len(l12m_data) if l12m_data is not None else 0

        # Eligible L12M: filter eligible_data by L12M
        elig_l12m = 0
        el12m_df = pd.DataFrame()
        if ctx.subsets.eligible_data is not None and ctx.start_date and ctx.end_date:
            el12m_df = filter_l12m(ctx.subsets.eligible_data, ctx.start_date, ctx.end_date)
            elig_l12m = len(el12m_df)

        # With debit in L12M
        wd_l12m = 0
        if not el12m_df.empty and "Debit?" in el12m_df.columns:
            wd_l12m = int((el12m_df["Debit?"] == "Yes").sum())

        # Personal with debit in L12M
        p_wd_l12m = 0
        if not el12m_df.empty and "Debit?" in el12m_df.columns and "Business?" in el12m_df.columns:
            mask = (el12m_df["Debit?"] == "Yes") & (el12m_df["Business?"] == "No")
            p_wd_l12m = int(mask.sum())

        # Reg E in L12M personal with debit
        rege_l12m = 0
        if col and p_wd_l12m > 0 and not el12m_df.empty:
            mask = (el12m_df["Debit?"] == "Yes") & (el12m_df["Business?"] == "No")
            p_debit_df = el12m_df[mask]
            if col in p_debit_df.columns:
                rege_l12m = int(p_debit_df[col].astype(str).str.strip().isin(opts).sum())

        stages = [
            {"name": "L12M Opens", "total": total_l12m, "color": _FUNNEL_COLORS[0]},
            {"name": "L12M Eligible", "total": elig_l12m, "color": _FUNNEL_COLORS[1]},
            {"name": "L12M w/Debit", "total": wd_l12m, "color": _FUNNEL_COLORS[2]},
            {"name": "L12M Personal w/Debit", "total": p_wd_l12m, "color": _FUNNEL_COLORS[3]},
            {"name": "L12M w/Reg E", "total": rege_l12m, "color": _FUNNEL_COLORS[4]},
        ]

        funnel_df = pd.DataFrame([{"Stage": s["name"], "Count": s["total"]} for s in stages])

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_11_reg_e_l12m_funnel.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        rege_rate = rege_l12m / p_wd_l12m * 100 if p_wd_l12m > 0 else 0
        through_rate = rege_l12m / total_l12m * 100 if total_l12m > 0 else 0

        subtitle = "L12M Analysis"
        if ctx.start_date and ctx.end_date:
            subtitle = f"{ctx.start_date.strftime('%B %Y')} - {ctx.end_date.strftime('%B %Y')}"

        with chart_figure(figsize=(12, 10), save_path=save_to) as (fig, ax):
            _render_funnel(
                ax, stages,
                title_text="L12M Account Eligibility & Reg E Funnel",
                subtitle_text=subtitle,
                metrics_text=f"Reg E Rate: {rege_rate:.1f}%\nEnd-to-End: {through_rate:.1f}%",
            )
        chart_path = save_to

        notes = (
            f"L12M Opens: {total_l12m:,} -> Reg E: {rege_l12m:,} "
            f"({rege_rate:.1f}% of personal w/debit)"
        )

        ctx.results["reg_e_11"] = {"funnel": funnel_df}
        return [AnalysisResult(
            slide_id="A8.11", title="L12M Funnel with Reg E",
            chart_path=chart_path,
            excel_data={"Funnel": funnel_df},
            notes=notes,
        )]
