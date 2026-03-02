"""DCTR Branch Analysis -- per-branch breakdowns, trends, heatmaps.

Slide IDs: DCTR-9 (a/b/c/d), DCTR-15, DCTR-16, A7.10a, A7.10b, A7.10c, A7.13.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import (
    branch_dctr,
    categorize_account_age,
    dctr,
    debit_mask,
    filter_l12m,
    l12m_month_labels,
    simplify_account_age,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE, TEAL
from ars_analysis.pipeline.context import PipelineContext


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(slide_id=label, title=label, success=False, error=str(exc))]


@register
class DCTRBranches(AnalysisModule):
    """DCTR branch analyses -- per-branch breakdowns, trends, and heatmaps."""

    module_id = "dctr.branches"
    display_name = "DCTR Branch Analysis"
    section = "dctr"
    required_columns = ("Date Opened", "Debit?", "Branch")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("DCTR Branches for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._branch_dctr_tables, "DCTR-9", ctx)
        results += _safe(self._branch_age_crosstab, "DCTR-15", ctx)
        results += _safe(self._branch_l12m_table, "DCTR-16", ctx)
        results += _safe(self._branch_trend, "A7.10a", ctx)
        results += _safe(self._branch_l12m_bars, "A7.10b", ctx)
        results += _safe(self._heatmap, "A7.13", ctx)
        return results

    # -- DCTR-9: Branch DCTR Tables + Top 10 Chart ----------------------------

    def _branch_dctr_tables(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []

        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
        br_all, br_ins = branch_dctr(ed, bm)
        ctx.results["dctr_9"] = {"all": br_ins}

        # Top 10 horizontal bar chart
        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir and not br_all.empty:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_branch_top10.png"
            try:
                dr = br_all[br_all["Branch"] != "TOTAL"].head(10).iloc[::-1]
                with chart_figure(save_path=save_to) as (fig, ax):
                    ax.barh(
                        dr["Branch"].astype(str),
                        dr["DCTR %"] * 100,
                        color=TEAL,
                        edgecolor="black",
                        linewidth=1.5,
                        alpha=0.9,
                    )
                    ax.set_xlabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title(
                        "Branch Debit Card Take Rate -- Top 10",
                        fontsize=24,
                        fontweight="bold",
                        pad=20,
                    )
                    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.tick_params(axis="both", labelsize=18)
                    for i, (d_val, t) in enumerate(zip(dr["DCTR %"], dr["Total Accounts"])):
                        ax.text(
                            d_val * 100 + 0.5,
                            i,
                            f"{d_val:.1%} ({int(t):,})",
                            va="center",
                            fontsize=18,
                            fontweight="bold",
                        )
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.set_axisbelow(True)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.10c chart failed: {err}", err=exc)

        return [
            AnalysisResult(
                slide_id="DCTR-9",
                title="Branch DCTR Overview",
                chart_path=chart_path,
                excel_data={"Branch All": br_all},
                notes=(
                    f"Best: {br_ins.get('best_branch', '?')} ({br_ins.get('best_dctr', 0):.1%}) | "
                    f"Worst: {br_ins.get('worst_branch', '?')} ({br_ins.get('worst_dctr', 0):.1%})"
                ),
            )
        ]

    # -- DCTR-15: Cross-tab Branch x Account Age ------------------------------

    def _branch_age_crosstab(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []

        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
        dc = ed.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce", format="mixed")
        dc["Account Age Days"] = (pd.Timestamp.now() - dc["Date Opened"]).dt.days
        if bm:
            str_bm = {str(k): v for k, v in bm.items()}
            mapped = dc["Branch"].astype(str).map(str_bm)
            dc["Branch Name"] = mapped.where(mapped.notna(), dc["Branch"])
        else:
            dc["Branch Name"] = dc["Branch"]
        valid = dc[dc["Account Age Days"].notna()].copy()
        valid["Simple Age"] = (
            valid["Account Age Days"].apply(categorize_account_age).apply(simplify_account_age)
        )

        simple_order = ["New (0-1 year)", "Recent (1-5 years)", "Mature (5+ years)"]
        rows = []
        for branch in sorted(valid["Branch Name"].unique()):
            bd = valid[valid["Branch Name"] == branch]
            for ac in simple_order:
                seg = bd[bd["Simple Age"] == ac]
                if len(seg) > 0:
                    t, w, d = dctr(seg)
                    rows.append(
                        {
                            "Branch": branch,
                            "Age Category": ac,
                            "Total Accounts": t,
                            "With Debit": w,
                            "DCTR %": d,
                        }
                    )

        detail = pd.DataFrame(rows)
        if detail.empty:
            return []

        pivot = detail.pivot_table(index="Branch", columns="Age Category", values="DCTR %")
        pivot = pivot.reindex(columns=simple_order)

        new_data = detail[detail["Age Category"] == "New (0-1 year)"]
        best_new = new_data.loc[new_data["DCTR %"].idxmax()] if not new_data.empty else None
        ctx.results["dctr_15"] = {
            "branches": len(detail["Branch"].unique()),
            "best_new_branch": best_new["Branch"] if best_new is not None else None,
        }

        return [
            AnalysisResult(
                slide_id="DCTR-15",
                title="Branch x Account Age Cross-Tab",
                excel_data={"Detail": detail, "Pivot": pivot},
                notes=f"{len(detail['Branch'].unique())} branches x 3 age categories",
            )
        ]

    # -- DCTR-16: Branch L12M Monthly Table -----------------------------------

    def _branch_l12m_table(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty or ctx.end_date is None:
            return []

        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
        months = l12m_month_labels(ctx.end_date)

        dc = ed.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce", format="mixed")
        dc["Month_Year"] = dc["Date Opened"].dt.strftime("%b%y")
        if bm:
            str_bm = {str(k): v for k, v in bm.items()}
            mapped = dc["Branch"].astype(str).map(str_bm)
            dc["Branch Name"] = mapped.where(mapped.notna(), dc["Branch"])
        else:
            dc["Branch Name"] = dc["Branch"]

        all_branches = sorted(dc["Branch Name"].unique())
        rows = []
        for branch in all_branches:
            bd = dc[dc["Branch Name"] == branch]
            row: dict = {"Branch": branch}
            te = td = 0
            for month in months:
                md = bd[bd["Month_Year"] == month]
                elig = len(md)
                debits = int(debit_mask(md).sum())
                te += elig
                td += debits
                row[month] = f"{(debits / elig * 100):.1f}%" if elig > 0 else ""
            row["12M Debits"] = td
            row["12M Eligible"] = te
            row["12M Take Rate"] = f"{(td / te * 100):.1f}%" if te > 0 else "0.0%"
            rows.append(row)

        table = pd.DataFrame(rows)
        grand_d = sum(r["12M Debits"] for r in rows)
        grand_e = sum(r["12M Eligible"] for r in rows)
        grand_r = (grand_d / grand_e * 100) if grand_e > 0 else 0

        ctx.results["dctr_16"] = {"grand_rate": grand_r, "branches": len(all_branches)}

        return [
            AnalysisResult(
                slide_id="DCTR-16",
                title="Branch L12M Monthly Performance",
                excel_data={"Branch L12M": table},
                notes=f"{len(all_branches)} branches | Overall: {grand_r:.1f}%",
            )
        ]

    # -- A7.10a: Branch Trend (Historical vs L12M) ----------------------------

    def _branch_trend(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty or ctx.start_date is None or ctx.end_date is None:
            return []

        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
        el12 = filter_l12m(ed, ctx.start_date, ctx.end_date)

        hist_df, _ = branch_dctr(ed, bm)
        l12m_df, _ = branch_dctr(el12, bm)

        if hist_df.empty or l12m_df.empty:
            return []

        hd = hist_df[hist_df["Branch"] != "TOTAL"][
            ["Branch", "DCTR %", "Total Accounts"]
        ].rename(
            columns={"DCTR %": "Historical DCTR", "Total Accounts": "Hist Volume"}
        )
        ld = l12m_df[l12m_df["Branch"] != "TOTAL"][
            ["Branch", "DCTR %", "Total Accounts"]
        ].rename(
            columns={"DCTR %": "L12M DCTR", "Total Accounts": "L12M Volume"}
        )
        merged = hd.merge(ld, on="Branch", how="outer").fillna(0)
        merged["Change pp"] = (
            (merged["L12M DCTR"] - merged["Historical DCTR"]) * 100
        )
        merged["Historical DCTR %"] = merged["Historical DCTR"] * 100
        merged["L12M DCTR %"] = merged["L12M DCTR"] * 100

        # Sort by L12M Volume descending so largest branch appears first (left)
        merged = merged.sort_values("L12M Volume", ascending=False)

        improving = int((merged["Change pp"] > 0).sum())
        avg_change = merged["Change pp"].mean()

        export = merged[
            [
                "Branch",
                "Historical DCTR %",
                "L12M DCTR %",
                "Change pp",
                "Hist Volume",
                "L12M Volume",
            ]
        ].copy()

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_branch_trend.png"
            try:
                n = len(merged)
                fig_w = max(14, n * 1.2 + 2)
                with chart_figure(
                    figsize=(fig_w, 10), save_path=save_to
                ) as (fig, ax):
                    x = np.arange(n)

                    # Primary axis: vertical bars for eligible accounts
                    ax.bar(
                        x,
                        merged["L12M Volume"],
                        color="#B0C4DE",
                        edgecolor="#4A6FA5",
                        alpha=0.7,
                        width=0.6,
                        label="Eligible Accounts",
                        zorder=1,
                    )
                    ax.set_ylabel(
                        "Eligible Accounts", fontsize=20, fontweight="bold"
                    )
                    ax.set_xticks(x)
                    ax.set_xticklabels(
                        merged["Branch"].values,
                        fontsize=16,
                        fontweight="bold",
                        rotation=45,
                        ha="right",
                    )
                    ax.yaxis.set_major_formatter(
                        FuncFormatter(lambda v, p: f"{int(v):,}")
                    )
                    ax.tick_params(axis="y", labelsize=16)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.set_axisbelow(True)

                    # Secondary right axis: DCTR rate dot-line overlays
                    ax2 = ax.twinx()
                    ax2.plot(
                        x,
                        merged["Historical DCTR %"].values,
                        "o--",
                        color="black",
                        linewidth=2.5,
                        markersize=10,
                        label="Historical DCTR",
                        zorder=3,
                    )
                    ax2.plot(
                        x,
                        merged["L12M DCTR %"].values,
                        "o-",
                        color="#1B4F72",
                        linewidth=3.5,
                        markersize=12,
                        label="TTM DCTR",
                        zorder=4,
                    )
                    ax2.set_ylabel(
                        "DCTR (%)", fontsize=20, fontweight="bold"
                    )
                    ax2.yaxis.set_major_formatter(
                        FuncFormatter(lambda v, p: f"{int(v)}%")
                    )
                    ax2.tick_params(axis="y", labelsize=16)

                    ax.set_title(
                        "Branch DCTR: Volume & Rates",
                        fontsize=24,
                        fontweight="bold",
                        pad=20,
                    )

                    # Combined legend at bottom center
                    handles1, labels1 = ax.get_legend_handles_labels()
                    handles2, labels2 = ax2.get_legend_handles_labels()
                    ax.legend(
                        handles1 + handles2,
                        labels1 + labels2,
                        loc="upper center",
                        bbox_to_anchor=(0.5, -0.15),
                        ncol=3,
                        fontsize=14,
                    )

                    # Change indicators above each bar
                    bar_max = merged["L12M Volume"].max()
                    for i, (_, row) in enumerate(merged.iterrows()):
                        chg = row["Change pp"]
                        clr = (
                            "#27AE60"
                            if chg > 0
                            else "#E74C3C"
                            if chg < 0
                            else "#666666"
                        )
                        sign = "+" if chg > 0 else ""
                        ax.text(
                            i,
                            row["L12M Volume"] + bar_max * 0.01,
                            f"{sign}{chg:.1f}pp",
                            ha="center",
                            fontsize=14,
                            color=clr,
                            fontweight="bold",
                        )

                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.10a chart failed: {err}", err=exc)

        ctx.results["dctr_branch_trend"] = {
            "improving": improving,
            "total": len(merged),
            "avg_change": avg_change,
        }
        return [
            AnalysisResult(
                slide_id="A7.10a",
                title="Branch DCTR: Volume & Rates",
                chart_path=chart_path,
                excel_data={"Branch Trend": export},
                notes=(
                    f"{improving}/{len(merged)} branches improving"
                    f" | Avg: {avg_change:+.1f}pp"
                ),
            )
        ]

    # -- A7.10b: Branch L12M Vertical Bars ------------------------------------

    def _branch_l12m_bars(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty or ctx.start_date is None or ctx.end_date is None:
            return []

        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
        el12 = filter_l12m(ed, ctx.start_date, ctx.end_date)
        l12m_df, l12m_ins = branch_dctr(el12, bm)
        if l12m_df.empty:
            return []

        dr = l12m_df[l12m_df["Branch"] != "TOTAL"].sort_values("DCTR %", ascending=False)

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir and not dr.empty:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_branch_l12m.png"
            try:
                with chart_figure(figsize=(14, 8), save_path=save_to) as (fig, ax):
                    x = np.arange(len(dr))
                    ax.bar(
                        x,
                        dr["DCTR %"] * 100,
                        color=TEAL,
                        edgecolor="black",
                        linewidth=1.5,
                        alpha=0.9,
                    )
                    for i, (d_val, t) in enumerate(zip(dr["DCTR %"], dr["Total Accounts"])):
                        ax.text(
                            i,
                            d_val * 100 + 1,
                            f"{d_val:.1%}",
                            ha="center",
                            fontsize=16,
                            fontweight="bold",
                        )
                    ax.set_xticks(x)
                    ax.set_xticklabels(dr["Branch"].values, rotation=45, ha="right", fontsize=16)
                    ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                    ax.set_title(
                        "Branch DCTR -- Trailing Twelve Months",
                        fontsize=24,
                        fontweight="bold",
                        pad=20,
                    )
                    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                    ax.tick_params(axis="y", labelsize=18)
                    ax.spines["top"].set_visible(False)
                    ax.spines["right"].set_visible(False)
                    ax.set_axisbelow(True)
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.10b chart failed: {err}", err=exc)

        return [
            AnalysisResult(
                slide_id="A7.10b",
                title="Branch DCTR -- TTM",
                chart_path=chart_path,
                excel_data={"Branch L12M": dr},
                notes=f"{len(dr)} branches | Best: {l12m_ins.get('best_branch', '?')} ({l12m_ins.get('best_dctr', 0):.1%})",
            )
        ]

    # -- A7.13: Monthly DCTR Heatmap by Branch --------------------------------

    def _heatmap(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty or ctx.end_date is None:
            return []

        bm = getattr(ctx.settings, "branch_mapping", None) if ctx.settings else None
        months = l12m_month_labels(ctx.end_date)

        dc = ed.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce", format="mixed")
        dc["Month_Year"] = dc["Date Opened"].dt.strftime("%b%y")
        if bm:
            str_bm = {str(k): v for k, v in bm.items()}
            mapped = dc["Branch"].astype(str).map(str_bm)
            dc["Branch Name"] = mapped.where(mapped.notna(), dc["Branch"])
        else:
            dc["Branch Name"] = dc["Branch"]

        branches = sorted(dc["Branch Name"].unique())
        if not branches or not months:
            return []

        heat_data = []
        for branch in branches:
            bd = dc[dc["Branch Name"] == branch]
            row: dict = {"Branch": branch}
            for month in months:
                md = bd[bd["Month_Year"] == month]
                t = len(md)
                w = int(debit_mask(md).sum())
                row[month] = (w / t * 100) if t > 0 else np.nan
            heat_data.append(row)

        heat_df = pd.DataFrame(heat_data).set_index("Branch")

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_heatmap.png"
            try:
                n_b = len(branches)
                n_m = len(months)
                fig_h = max(8, n_b * 0.6 + 2)
                with chart_figure(figsize=(max(14, n_m * 1.2), fig_h), save_path=save_to) as (
                    fig,
                    ax,
                ):
                    from matplotlib.colors import TwoSlopeNorm

                    cmap = LinearSegmentedColormap.from_list(
                        "dctr_div", [NEGATIVE, "#FADBD8", "white", "#D5F5E3", POSITIVE]
                    )
                    data_vals = heat_df.values
                    valid_vals = data_vals[~np.isnan(data_vals)]
                    avg_dctr = np.nanmean(valid_vals) if len(valid_vals) else 50
                    vmin = max(0, np.nanmin(valid_vals) - 2) if len(valid_vals) else 0
                    vmax = min(100, np.nanmax(valid_vals) + 2) if len(valid_vals) else 100
                    # Ensure avg is strictly between vmin and vmax for TwoSlopeNorm
                    avg_clamped = max(vmin + 0.01, min(avg_dctr, vmax - 0.01))
                    norm = TwoSlopeNorm(vmin=vmin, vcenter=avg_clamped, vmax=vmax)

                    im = ax.imshow(data_vals, cmap=cmap, aspect="auto", norm=norm)
                    ax.set_xticks(range(n_m))
                    ax.set_xticklabels(months, rotation=45, ha="right", fontsize=16)
                    ax.set_yticks(range(n_b))
                    ax.set_yticklabels(branches, fontsize=16)

                    # Find global min/max for emphasis
                    global_max = np.nanmax(valid_vals) if len(valid_vals) else 0
                    global_min = np.nanmin(valid_vals) if len(valid_vals) else 0

                    for i in range(n_b):
                        for j in range(n_m):
                            v = data_vals[i, j]
                            if not np.isnan(v):
                                txt_color = (
                                    "black" if abs(v - avg_dctr) < (vmax - vmin) * 0.3 else "white"
                                )
                                fw = "900" if v == global_max or v == global_min else "bold"
                                ax.text(
                                    j,
                                    i,
                                    f"{v:.0f}",
                                    ha="center",
                                    va="center",
                                    fontsize=14,
                                    fontweight=fw,
                                    color=txt_color,
                                )

                    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
                    cbar.set_label("DCTR %", fontsize=16, fontweight="bold")
                    cbar.ax.axhline(y=avg_dctr, color="black", linewidth=2)
                    ax.set_title(
                        "Monthly DCTR Heatmap by Branch (TTM)",
                        fontsize=22,
                        fontweight="bold",
                        pad=15,
                    )
                chart_path = save_to
            except Exception as exc:
                logger.warning("A7.13 heatmap failed: {err}", err=exc)

        return [
            AnalysisResult(
                slide_id="A7.13",
                title="Monthly DCTR Heatmap by Branch",
                chart_path=chart_path,
                excel_data={"Heatmap": heat_df.reset_index()},
                notes=f"{len(branches)} branches x {len(months)} months",
            )
        ]
