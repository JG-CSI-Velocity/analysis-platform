"""DCTR Demographic Overlays -- account age, holder age, balance, cross-tabs.

Slide IDs: DCTR-10, DCTR-11, DCTR-12, DCTR-13, DCTR-14, A7.11, A7.12.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.dctr._helpers import (
    AGE_ORDER,
    BALANCE_ORDER,
    HOLDER_AGE_ORDER,
    by_dimension,
    categorize_account_age,
    categorize_balance,
    categorize_holder_age,
    crosstab_dctr,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import TEAL
from ars_analysis.pipeline.context import PipelineContext


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(slide_id=label, title=label, success=False, error=str(exc))]


@register
class DCTROverlays(AnalysisModule):
    """DCTR demographic overlays -- age, balance, and cross-tab analyses."""

    module_id = "dctr.overlays"
    display_name = "DCTR Demographic Overlays"
    section = "dctr"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("DCTR Overlays for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._account_age, "DCTR-10", ctx)
        results += _safe(self._holder_age, "DCTR-11", ctx)
        results += _safe(self._balance_range, "DCTR-12", ctx)
        results += _safe(self._crosstab_holder_balance, "DCTR-13", ctx)
        results += _safe(self._crosstab_acct_balance, "DCTR-14", ctx)
        return results

    # -- DCTR-10 + A7.12: Account Age Breakdown + Chart -----------------------

    def _account_age(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []

        dc = ed.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
        dc["Account Age Days"] = (pd.Timestamp.now() - dc["Date Opened"]).dt.days
        df, ins = by_dimension(dc, "Account Age Days", categorize_account_age, AGE_ORDER, "Account Age")
        if df.empty:
            return []

        ctx.results["dctr_10"] = {"df": df, "insights": ins}

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_account_age.png"
            try:
                dr = df[df["Account Age"] != "TOTAL"]
                if not dr.empty:
                    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
                        x = np.arange(len(dr))
                        vals = dr["DCTR %"].values * 100
                        volumes = dr["Total Accounts"].values

                        ax2 = ax.twinx()
                        ax2.bar(x, volumes, alpha=0.3, color="gray", edgecolor="none", width=0.6)
                        ax2.set_ylabel("Account Volume", fontsize=24, color="gray")
                        ax2.set_ylim(0, max(volumes) * 1.3 if len(volumes) else 100)
                        ax2.tick_params(axis="y", colors="gray", labelsize=20)

                        ax.plot(x, vals, color=TEAL, linewidth=4, marker="o", markersize=12,
                                label="DCTR %", zorder=3)
                        for i, v in enumerate(vals):
                            ax.text(i, v + 2, f"{v:.1f}%", ha="center", va="bottom",
                                    fontsize=20, fontweight="bold", color=TEAL)

                        ax.set_title("Eligible Accounts DCTR by Account Age", fontsize=24, fontweight="bold", pad=25)
                        ax.set_xlabel("Account Age", fontsize=20, fontweight="bold")
                        ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold", color=TEAL)
                        ax.set_xticks(x)
                        ax.set_xticklabels(dr["Account Age"].values, fontsize=18, rotation=45, ha="right")
                        ax.tick_params(axis="y", labelsize=20, colors=TEAL)
                        ax.set_ylim(0, max(vals) * 1.2 if len(vals) else 100)
                        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                        ax.set_axisbelow(True)
                        ax.spines["top"].set_visible(False)
                        ax2.spines["top"].set_visible(False)
                    chart_path = save_to
            except Exception as exc:
                logger.warning("A7.12 chart failed: {err}", err=exc)

        return [AnalysisResult(
            slide_id="DCTR-10",
            title="DCTR by Account Age",
            chart_path=chart_path,
            excel_data={"Account Age": df},
            notes=(
                f"Highest: {ins.get('highest', '?')} ({ins.get('highest_dctr', 0):.1%}) | "
                f"Lowest: {ins.get('lowest', '?')} ({ins.get('lowest_dctr', 0):.1%})"
            ),
        )]

    # -- DCTR-11 + A7.11: Account Holder Age + Chart --------------------------

    def _holder_age(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []
        if "Account Holder Age" not in ed.columns:
            return []

        edc = ed.copy()
        edc["Account Holder Age"] = pd.to_numeric(edc["Account Holder Age"], errors="coerce")
        valid = edc[(edc["Account Holder Age"] >= 18) & (edc["Account Holder Age"] <= 120)].copy()
        df, ins = by_dimension(valid, "Account Holder Age", categorize_holder_age, HOLDER_AGE_ORDER, "Age Group")
        if df.empty:
            return []

        ctx.results["dctr_11"] = {"df": df, "insights": ins}

        chart_path = None
        charts_dir = ctx.paths.charts_dir
        if charts_dir != ctx.paths.base_dir:
            charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = charts_dir / "dctr_holder_age.png"
            try:
                dr = df[df["Age Group"] != "TOTAL"]
                if not dr.empty:
                    import matplotlib.pyplot as plt
                    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
                        x = np.arange(len(dr))
                        vals = dr["DCTR %"].values * 100
                        colors = plt.cm.Blues(np.linspace(0.5, 0.9, len(dr)))
                        bars = ax.bar(x, vals, color=colors, edgecolor="black", linewidth=2, alpha=0.9)
                        for bar, v in zip(bars, vals):
                            ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}%",
                                    ha="center", fontsize=24, fontweight="bold")
                        ax.set_title("Eligible Accounts DCTR by Account Holder Age",
                                     fontsize=24, fontweight="bold", pad=25)
                        ax.set_xlabel("Age Group", fontsize=20, fontweight="bold")
                        ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
                        ax.set_xticks(x)
                        ax.set_xticklabels(dr["Age Group"].values, fontsize=20)
                        ax.tick_params(axis="y", labelsize=20)
                        ax.set_ylim(0, max(vals) * 1.15 if len(vals) else 100)
                        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                        ax.set_axisbelow(True)
                        ax.spines["top"].set_visible(False)
                        ax.spines["right"].set_visible(False)
                    chart_path = save_to
            except Exception as exc:
                logger.warning("A7.11 chart failed: {err}", err=exc)

        return [AnalysisResult(
            slide_id="DCTR-11",
            title="DCTR by Account Holder Age",
            chart_path=chart_path,
            excel_data={"Holder Age": df},
            notes=(
                f"Highest: {ins.get('highest', '?')} ({ins.get('highest_dctr', 0):.1%}) | "
                f"Lowest: {ins.get('lowest', '?')} ({ins.get('lowest_dctr', 0):.1%})"
            ),
        )]

    # -- DCTR-12: Balance Range -----------------------------------------------

    def _balance_range(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []
        if "Avg Bal" not in ed.columns:
            return []

        edc = ed.copy()
        edc["Avg Bal"] = pd.to_numeric(edc["Avg Bal"], errors="coerce")
        valid = edc[edc["Avg Bal"].notna()].copy()
        df, ins = by_dimension(valid, "Avg Bal", categorize_balance, BALANCE_ORDER, "Balance Range")
        if df.empty:
            return []

        ctx.results["dctr_12"] = {"df": df, "insights": ins}
        return [AnalysisResult(
            slide_id="DCTR-12",
            title="DCTR by Balance Range",
            excel_data={"Balance Range": df},
            notes=(
                f"Highest: {ins.get('highest', '?')} ({ins.get('highest_dctr', 0):.1%}) | "
                f"Lowest: {ins.get('lowest', '?')} ({ins.get('lowest_dctr', 0):.1%})"
            ),
        )]

    # -- DCTR-13: Cross-tab Holder Age x Balance ------------------------------

    def _crosstab_holder_balance(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []
        if "Account Holder Age" not in ed.columns or "Avg Bal" not in ed.columns:
            return []

        dc = ed.copy()
        dc["Account Holder Age"] = pd.to_numeric(dc["Account Holder Age"], errors="coerce")
        dc["Avg Bal"] = pd.to_numeric(dc["Avg Bal"], errors="coerce")
        valid = dc[(dc["Account Holder Age"] >= 18) & (dc["Account Holder Age"] <= 120) & dc["Avg Bal"].notna()].copy()

        detail, dpiv, cpiv, ins = crosstab_dctr(
            valid,
            "Account Holder Age", categorize_holder_age, HOLDER_AGE_ORDER, "Age Group",
            "Avg Bal", categorize_balance, BALANCE_ORDER, "Balance Range",
        )
        if detail.empty:
            return []

        ctx.results["dctr_13"] = ins
        excel = {"Detail": detail}
        if not dpiv.empty:
            excel["Pivot"] = dpiv

        return [AnalysisResult(
            slide_id="DCTR-13",
            title="Cross-Tab: Holder Age x Balance",
            excel_data=excel,
            notes=f"{ins.get('segments', 0)} segments",
        )]

    # -- DCTR-14: Cross-tab Account Age x Balance -----------------------------

    def _crosstab_acct_balance(self, ctx: PipelineContext) -> list[AnalysisResult]:
        ed = ctx.subsets.eligible_data
        if ed is None or ed.empty:
            return []
        if "Avg Bal" not in ed.columns:
            return []

        dc = ed.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
        dc["Account Age Days"] = (pd.Timestamp.now() - dc["Date Opened"]).dt.days
        dc["Avg Bal"] = pd.to_numeric(dc["Avg Bal"], errors="coerce")
        valid = dc[dc["Account Age Days"].notna() & dc["Avg Bal"].notna()].copy()

        detail, dpiv, cpiv, ins = crosstab_dctr(
            valid,
            "Account Age Days", categorize_account_age, AGE_ORDER, "Account Age",
            "Avg Bal", categorize_balance, BALANCE_ORDER, "Balance Range",
        )
        if detail.empty:
            return []

        ctx.results["dctr_14"] = ins
        excel = {"Detail": detail}
        if not dpiv.empty:
            excel["Pivot"] = dpiv

        return [AnalysisResult(
            slide_id="DCTR-14",
            title="Cross-Tab: Account Age x Balance",
            excel_data=excel,
            notes=f"{ins.get('segments', 0)} segments",
        )]
