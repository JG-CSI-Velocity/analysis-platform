"""Reg E Branch Analysis -- per-branch opt-in rates, comparison, scatter, pivot.

Slide IDs: A8.4a, A8.4b, A8.4c, A8.13.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import l12m_month_labels
from ars_analysis.analytics.rege._helpers import reg_e_base, rege, total_row
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import ELIGIBLE, HISTORICAL, NEUTRAL
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


def _branch_rates(df: pd.DataFrame, col: str, opts: list[str]) -> pd.DataFrame:
    """Calculate Reg E rates by branch for a DataFrame."""
    if df is None or df.empty or "Branch" not in df.columns:
        return pd.DataFrame()
    rows = []
    for br in sorted(df["Branch"].dropna().unique()):
        bd = df[df["Branch"] == br]
        t, oi, r = rege(bd, col, opts)
        rows.append({"Branch": br, "Total Accounts": t, "Opted In": oi,
                     "Opted Out": t - oi, "Opt-In Rate": r})
    result = pd.DataFrame(rows)
    return total_row(result, "Branch") if not result.empty else result


@register
class RegEBranches(AnalysisModule):
    """Reg E opt-in by Branch -- horizontal bars, vertical bars, scatter, pivot."""

    module_id = "rege.branches"
    display_name = "Reg E Branch Analysis"
    section = "rege"
    required_columns = ("Date Opened", "Debit?", "Business?", "Branch")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Reg E Branches for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._branch_comparison, "A8.4a", ctx)
        results += _safe(self._branch_scatter, "A8.4c", ctx)
        results += _safe(self._branch_vertical, "A8.4b", ctx)
        results += _safe(self._branch_pivot, "A8.13", ctx)
        return results

    # -- A8.4a: Branch Historical vs L12M (horizontal bars) ------------------

    def _branch_comparison(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.4a: Reg E by Branch (horizontal)")
        base, base_l12m, col, opts = reg_e_base(ctx)

        hist = _branch_rates(base, col, opts)
        l12m = _branch_rates(base_l12m, col, opts) if base_l12m is not None else pd.DataFrame()

        # Build comparison table
        comparison = []
        if not hist.empty:
            branches = hist[hist["Branch"] != "TOTAL"]["Branch"].unique()
            for br in branches:
                h = hist[hist["Branch"] == br]
                l_df = l12m[l12m["Branch"] == br] if not l12m.empty else pd.DataFrame()
                if not h.empty:
                    hr = h["Opt-In Rate"].iloc[0]
                    hv = h["Total Accounts"].iloc[0]
                    lr = l_df["Opt-In Rate"].iloc[0] if not l_df.empty else 0
                    lv = l_df["Total Accounts"].iloc[0] if not l_df.empty else 0
                    comparison.append({
                        "Branch": br, "Historical Rate": hr, "L12M Rate": lr,
                        "Change": lr - hr, "Historical Volume": hv, "L12M Volume": lv,
                    })
        comp_df = pd.DataFrame(comparison)
        if not comp_df.empty:
            comp_df = comp_df.sort_values("Historical Rate", ascending=False)

        # Store for A8.4b to reuse
        ctx.results["reg_e_4"] = {"comparison": comp_df, "historical": hist, "l12m": l12m}

        # Chart -- horizontal bar
        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_4a_reg_e_branch.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        if not comp_df.empty:
            with chart_figure(
                figsize=(18, max(10, len(comp_df) * 0.8)), save_path=save_to,
            ) as (fig, ax):
                y_pos = np.arange(len(comp_df))
                w = 0.35

                ax.barh(y_pos + w / 2, comp_df["Historical Rate"] * 100, w,
                        label="Historical", color=HISTORICAL, alpha=0.8)
                ax.barh(y_pos - w / 2, comp_df["L12M Rate"] * 100, w,
                        label="L12M", color=ELIGIBLE, alpha=0.8)

                for i in range(len(comp_df)):
                    hr = comp_df.iloc[i]["Historical Rate"] * 100
                    lr = comp_df.iloc[i]["L12M Rate"] * 100
                    if hr > 0:
                        ax.text(hr + 0.3, y_pos[i] + w / 2, f"{hr:.1f}%", va="center")
                    if lr > 0:
                        ax.text(lr + 0.3, y_pos[i] - w / 2, f"{lr:.1f}%", va="center")

                ax.set_yticks(y_pos)
                ax.set_yticklabels(comp_df["Branch"].tolist())
                ax.set_xlabel("Opt-In Rate (%)")
                ax.set_title(f"Reg E Opt-In by Branch -- {ctx.client.client_name}",
                             fontweight="bold")
                ax.legend()
                ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            chart_path = save_to

        improving = len(comp_df[comp_df["Change"] > 0]) if not comp_df.empty else 0
        notes = f"{len(comparison)} branches. {improving} improving (L12M > Historical)"

        return [AnalysisResult(
            slide_id="A8.4a", title="Reg E by Branch (Historical vs L12M)",
            chart_path=chart_path,
            excel_data={"Comparison": comp_df if not comp_df.empty else hist},
            notes=notes,
        )]

    # -- A8.4c: Branch Scatter (volume vs rate) ------------------------------

    def _branch_scatter(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.4c: Reg E Branch Scatter")
        hist = ctx.results.get("reg_e_4", {}).get("historical")
        if hist is None or hist.empty:
            base, _, col, opts = reg_e_base(ctx)
            hist = _branch_rates(base, col, opts)

        scatter = hist[hist["Branch"] != "TOTAL"].copy() if not hist.empty else pd.DataFrame()
        if scatter.empty or len(scatter) < 2:
            return [AnalysisResult(
                slide_id="A8.4c", title="Reg E Branch Scatter",
                success=False, error="Not enough branches for scatter plot",
            )]

        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_4c_reg_e_scatter.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        avg_vol = scatter["Total Accounts"].mean()
        avg_rate = (scatter["Opted In"].sum() / scatter["Total Accounts"].sum()) * 100

        with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
            ax.scatter(scatter["Total Accounts"], scatter["Opt-In Rate"] * 100,
                       s=300, alpha=0.6, color=HISTORICAL, edgecolor="black", linewidth=2)
            for _, row in scatter.iterrows():
                ax.annotate(row["Branch"],
                            (row["Total Accounts"], row["Opt-In Rate"] * 100),
                            xytext=(6, 6), textcoords="offset points")
            ax.axhline(y=avg_rate, color="red", linestyle="--", alpha=0.5, linewidth=1.5)
            ax.axvline(x=avg_vol, color="red", linestyle="--", alpha=0.5, linewidth=1.5)
            ax.set_xlabel("Total Accounts")
            ax.set_ylabel("Opt-In Rate (%)")
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax.set_title("Branch Volume vs Opt-In Rate", fontweight="bold")
            ax.set_axisbelow(True)
        chart_path = save_to

        hv_lr = len(scatter[
            (scatter["Total Accounts"] > avg_vol)
            & (scatter["Opt-In Rate"] * 100 <= avg_rate)
        ])
        notes = f"Avg volume: {avg_vol:,.0f}. Avg rate: {avg_rate:.1f}%. Priority branches: {hv_lr}"

        return [AnalysisResult(
            slide_id="A8.4c", title="Reg E Branch Scatter",
            chart_path=chart_path, notes=notes,
        )]

    # -- A8.4b: Branch Vertical (sorted by L12M rate) -----------------------

    def _branch_vertical(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.4b: Reg E by Branch (Vertical)")
        comp_df = ctx.results.get("reg_e_4", {}).get("comparison")
        if comp_df is None or comp_df.empty:
            return [AnalysisResult(
                slide_id="A8.4b", title="Reg E Branch Vertical",
                success=False, error="No branch comparison data",
            )]

        chart_data = comp_df.sort_values("L12M Rate", ascending=False).reset_index(drop=True)
        branches = chart_data["Branch"].tolist()
        n = len(branches)

        l12m_rates = chart_data["L12M Rate"] * 100
        hist_rates = chart_data["Historical Rate"] * 100
        l12m_vols = chart_data["L12M Volume"]

        h_wa = ((chart_data["Historical Rate"] * chart_data["Historical Volume"]).sum()
                / chart_data["Historical Volume"].sum() * 100
                if chart_data["Historical Volume"].sum() > 0 else 0)
        l_wa = ((chart_data["L12M Rate"] * chart_data["L12M Volume"]).sum()
                / chart_data["L12M Volume"].sum() * 100
                if chart_data["L12M Volume"].sum() > 0 else 0)

        chart_path = None
        save_to = ctx.paths.charts_dir / "a8_4b_reg_e_branch_vert.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        with chart_figure(figsize=(max(16, n * 1.5), 10), save_path=save_to) as (fig, _):
            ax1 = fig.add_subplot(1, 2, 1)
            ax2 = fig.add_subplot(1, 2, 2)
            x_pos = np.arange(n)

            # Left panel: Volume bars
            ax1.barh(x_pos, l12m_vols, color=NEUTRAL, edgecolor="none", height=0.6)
            for i, v in enumerate(l12m_vols):
                if v > 0:
                    ax1.text(v, x_pos[i], f" {int(v):,}", va="center", fontsize=9)
            ax1.set_yticks(x_pos)
            ax1.set_yticklabels(branches)
            ax1.set_xlabel("Eligible Accounts (L12M)")
            ax1.set_title("Account Volume", fontweight="bold")
            ax1.invert_yaxis()
            ax1.spines["top"].set_visible(False)
            ax1.spines["right"].set_visible(False)

            # Right panel: Rate comparison lines
            ax2.plot(hist_rates, x_pos, "o-", color=HISTORICAL, lw=2.5, ms=8,
                     label="Historical")
            ax2.plot(l12m_rates, x_pos, "o-", color=ELIGIBLE, lw=3, ms=10,
                     label="L12M", zorder=5)
            ax2.axvline(h_wa, color=HISTORICAL, linestyle="--", linewidth=2, alpha=0.5)
            ax2.axvline(l_wa, color=ELIGIBLE, linestyle="--", linewidth=2, alpha=0.5)
            ax2.set_yticks(x_pos)
            ax2.set_yticklabels([])
            ax2.set_xlabel("Opt-In Rate (%)")
            ax2.set_title("Opt-In Rate", fontweight="bold")
            ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
            ax2.invert_yaxis()
            ax2.legend(loc="lower right")
            ax2.spines["top"].set_visible(False)
            ax2.set_axisbelow(True)

            fig.suptitle("Reg E Opt-In by Branch (L12M Focus)", fontweight="bold",
                         fontsize=16)
            fig.tight_layout()
        chart_path = save_to

        improving = int((chart_data["L12M Rate"] > chart_data["Historical Rate"]).sum())
        trend_change = l_wa - h_wa
        notes = (
            f"{n} branches. L12M avg: {l_wa:.1f}%. "
            f"{'Improving' if trend_change > 0 else 'Declining'} ({trend_change:+.1f}pp). "
            f"{improving} of {n} improving"
        )

        return [AnalysisResult(
            slide_id="A8.4b", title="Reg E Branch Vertical",
            chart_path=chart_path, notes=notes,
        )]

    # -- A8.13: Branch x Month Pivot Table -----------------------------------

    def _branch_pivot(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A8.13: Branch x Month Pivot")
        base, base_l12m, col, opts = reg_e_base(ctx)

        if base_l12m is None or base_l12m.empty:
            return [AnalysisResult(
                slide_id="A8.13", title="Branch x Month Pivot",
                success=False, error="No L12M data for pivot",
            )]

        l12m_labels = l12m_month_labels(ctx.end_date)
        df = base_l12m.copy()
        df["Month_Year"] = pd.to_datetime(df["Date Opened"], errors="coerce").dt.strftime("%b%y")

        branches = sorted(df["Branch"].dropna().unique())
        pivot_rows = []

        for br in branches:
            row: dict = {"Branch": br}
            br_total = 0
            br_opted = 0
            for my in l12m_labels:
                seg = df[(df["Branch"] == br) & (df["Month_Year"] == my)]
                t = len(seg)
                oi = len(seg[seg[col].astype(str).str.strip().isin(opts)]) if t > 0 else 0
                row[f"{my} Opens"] = t
                row[f"{my} Opt-In"] = oi
                row[f"{my} Rate"] = oi / t if t > 0 else 0
                br_total += t
                br_opted += oi
            row["Total Opens"] = br_total
            row["Total Opt-In"] = br_opted
            row["Overall Rate"] = br_opted / br_total if br_total > 0 else 0
            pivot_rows.append(row)

        pivot = pd.DataFrame(pivot_rows)
        if not pivot.empty:
            pivot = pivot.sort_values("Overall Rate", ascending=False)

            # Grand total row
            totals: dict = {"Branch": "TOTAL"}
            for my in l12m_labels:
                totals[f"{my} Opens"] = pivot[f"{my} Opens"].sum()
                totals[f"{my} Opt-In"] = pivot[f"{my} Opt-In"].sum()
                t_sum = pivot[f"{my} Opens"].sum()
                oi_sum = pivot[f"{my} Opt-In"].sum()
                totals[f"{my} Rate"] = oi_sum / t_sum if t_sum > 0 else 0
            totals["Total Opens"] = pivot["Total Opens"].sum()
            totals["Total Opt-In"] = pivot["Total Opt-In"].sum()
            totals["Overall Rate"] = (pivot["Total Opt-In"].sum() / pivot["Total Opens"].sum()
                                      if pivot["Total Opens"].sum() > 0 else 0)
            pivot = pd.concat([pivot, pd.DataFrame([totals])], ignore_index=True)

        notes = f"{len(branches)} branches x {len(l12m_labels)} months"
        ctx.results["reg_e_13"] = {"pivot": pivot}

        return [AnalysisResult(
            slide_id="A8.13", title="Branch x Month Pivot",
            excel_data={"Pivot": pivot},
            notes=notes,
        )]
