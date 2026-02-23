"""Branch Performance Scorecard -- A19 series.

Consolidates branch-level metrics from DCTR, Reg E, and Attrition into a
single actionable scorecard.

Slide IDs: A19.1 (heatmap scorecard), A19.2 (opportunity stacked bar).
"""

from __future__ import annotations

import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, POSITIVE, TEAL
from ars_analysis.pipeline.context import PipelineContext

MIN_BRANCHES = 3


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def _build_branch_data(ctx: PipelineContext) -> pd.DataFrame | None:
    """Assemble branch-level metrics from upstream results.

    Returns DataFrame with columns: branch, dctr, rege_rate, attrition_rate, n_accounts.
    Returns None if insufficient data.
    """
    data = ctx.data
    if data is None:
        return None

    # Detect branch column
    branch_col = None
    for col in ("Branch", "branch"):
        if col in data.columns:
            branch_col = col
            break
    if branch_col is None:
        return None

    # Detect debit column
    debit_col = None
    for col in ("Debit?", "Debit", "DC Indicator"):
        if col in data.columns:
            debit_col = col
            break

    # Compute per-branch metrics from raw data
    branches = data[branch_col].dropna().unique()
    if len(branches) < MIN_BRANCHES:
        return None

    rows = []
    for branch in branches:
        branch_data = data[data[branch_col] == branch]
        n_total = len(branch_data)
        if n_total == 0:
            continue

        # DCTR: debit holders / total
        dctr = 0.0
        if debit_col:
            n_debit = len(branch_data[branch_data[debit_col].isin(["Yes", "Y", True, 1])])
            dctr = n_debit / n_total

        # Attrition: closed / total
        attrition = 0.0
        if "Stat Code" in branch_data.columns:
            n_closed = len(branch_data[branch_data["Stat Code"] == "C"])
            attrition = n_closed / n_total

        # Reg E (if available)
        rege_rate = 0.0
        rege_cols = [c for c in data.columns if "Reg E" in c and "Code" in c]
        if rege_cols:
            latest_rege = rege_cols[-1]
            opted_in = branch_data[latest_rege].isin(["Y", "Yes", "Opted-In", "OI", True, 1])
            rege_rate = opted_in.sum() / n_total

        rows.append(
            {
                "branch": str(branch),
                "dctr": dctr,
                "rege_rate": rege_rate,
                "attrition_rate": attrition,
                "n_accounts": n_total,
            }
        )

    if len(rows) < MIN_BRANCHES:
        return None

    return pd.DataFrame(rows).sort_values("dctr", ascending=False)


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_scorecard(ax, branch_df: pd.DataFrame) -> str:
    """Draw heatmap-style scorecard table. Returns insight."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    branches = branch_df["branch"].tolist()
    n = len(branches)

    # Column positions
    col_x = [0.02, 0.25, 0.42, 0.58, 0.75, 0.90]
    headers = ["Branch", "DCTR", "Reg E", "Attrition", "Accounts", "Rank"]

    row_height = min(0.06, 0.80 / (n + 1))
    y_start = 0.92

    # Header row
    for ci, (x, hdr) in enumerate(zip(col_x, headers)):
        ax.text(x, y_start, hdr, fontsize=14, fontweight="bold", color="#1E3D59", va="center")
    ax.plot(
        [0.01, 0.99],
        [y_start - row_height / 2, y_start - row_height / 2],
        color="#1E3D59",
        linewidth=1.5,
    )

    # Compute ranks (composite: high DCTR good, high Reg E good, low attrition good)
    branch_df = branch_df.copy()
    branch_df["dctr_rank"] = branch_df["dctr"].rank(ascending=False)
    branch_df["rege_rank"] = branch_df["rege_rate"].rank(ascending=False)
    branch_df["attr_rank"] = branch_df["attrition_rate"].rank(ascending=True)
    branch_df["composite"] = (
        branch_df["dctr_rank"] + branch_df["rege_rank"] + branch_df["attr_rank"]
    ) / 3
    branch_df["overall_rank"] = branch_df["composite"].rank().astype(int)
    branch_df = branch_df.sort_values("overall_rank")

    # Color helper
    def _rate_color(val, metric):
        if metric == "attrition":
            return POSITIVE if val < 0.10 else NEGATIVE if val > 0.20 else "#555"
        return POSITIVE if val > 0.60 else NEGATIVE if val < 0.30 else "#555"

    # Data rows
    for ri, (_, row) in enumerate(branch_df.iterrows()):
        y = y_start - (ri + 1.5) * row_height

        ax.text(col_x[0], y, row["branch"][:18], fontsize=12, va="center", color="#333")
        ax.text(
            col_x[1],
            y,
            f"{row['dctr']:.1%}",
            fontsize=12,
            va="center",
            fontweight="bold",
            color=_rate_color(row["dctr"], "dctr"),
        )
        ax.text(
            col_x[2],
            y,
            f"{row['rege_rate']:.1%}",
            fontsize=12,
            va="center",
            fontweight="bold",
            color=_rate_color(row["rege_rate"], "rege"),
        )
        ax.text(
            col_x[3],
            y,
            f"{row['attrition_rate']:.1%}",
            fontsize=12,
            va="center",
            fontweight="bold",
            color=_rate_color(row["attrition_rate"], "attrition"),
        )
        ax.text(col_x[4], y, f"{row['n_accounts']:,}", fontsize=12, va="center", color="#555")
        ax.text(
            col_x[5],
            y,
            f"#{row['overall_rank']}",
            fontsize=13,
            va="center",
            fontweight="bold",
            color=TEAL,
        )

        # Alternating row background
        if ri % 2 == 0:
            ax.add_patch(
                mpatches.Rectangle(
                    (0.01, y - row_height / 2),
                    0.98,
                    row_height,
                    facecolor="#F0F4F8",
                    edgecolor="none",
                )
            )

    ax.set_title(
        "Branch Performance Scorecard", fontsize=20, fontweight="bold", pad=20, color="#1E3D59"
    )

    best = branch_df.iloc[0]
    worst = branch_df.iloc[-1]
    return (
        f"Best: {best['branch']} (DCTR {best['dctr']:.0%}) | "
        f"Needs attention: {worst['branch']} (DCTR {worst['dctr']:.0%})"
    )


def _draw_opportunity_bars(ax, branch_df: pd.DataFrame, ic_rate: float) -> str:
    """Draw stacked bar of dollar opportunity per branch. Returns insight."""
    branches = branch_df["branch"].tolist()
    n_accounts = branch_df["n_accounts"].values

    # Opportunity = accounts NOT doing X * estimated value per account
    # DCTR gap: (1 - dctr) * n_accounts * avg_annual_ic
    avg_annual_ic = 216.0  # PULSE benchmark
    dctr_gap = (1 - branch_df["dctr"].values) * n_accounts * avg_annual_ic * ic_rate

    # Attrition cost: attrition_rate * n_accounts * replacement_cost
    replacement_cost = 562.50
    attr_cost = branch_df["attrition_rate"].values * n_accounts * (replacement_cost / 12)

    y = np.arange(len(branches))

    ax.barh(y, dctr_gap, height=0.6, label="IC Opportunity (DCTR Gap)", color=TEAL, alpha=0.8)
    ax.barh(
        y, attr_cost, height=0.6, left=dctr_gap, label="Attrition Cost", color=NEGATIVE, alpha=0.6
    )

    ax.set_yticks(y)
    ax.set_yticklabels(branches, fontsize=12)
    ax.set_xlabel("Annual Dollar Impact ($)", fontsize=14)
    ax.set_title("Branch Opportunity Map", fontsize=20, fontweight="bold")
    ax.legend(fontsize=13, loc="lower right", frameon=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)
    ax.xaxis.set_major_formatter(lambda x, _: f"${x:,.0f}")

    total = dctr_gap.sum() + attr_cost.sum()
    return f"Total branch opportunity: ${total:,.0f}/year"


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class BranchScorecard(AnalysisModule):
    """Branch Performance Scorecard -- A19 series."""

    module_id = "insights.branch_scorecard"
    display_name = "Branch Performance Scorecard"
    section = "insights"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Branch Scorecard for {client}", client=ctx.client.client_id)

        branch_df = _build_branch_data(ctx)
        if branch_df is None or len(branch_df) < MIN_BRANCHES:
            return [
                AnalysisResult(
                    slide_id="A19",
                    title="Branch Scorecard",
                    success=False,
                    error=f"Fewer than {MIN_BRANCHES} branches; scorecard not meaningful",
                )
            ]

        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # A19.1 -- Scorecard Heatmap
        save_to = ctx.paths.charts_dir / "a19_1_branch_scorecard.png"
        with chart_figure(figsize=(16, max(8, len(branch_df) * 0.6 + 2)), save_path=save_to) as (
            _fig,
            ax,
        ):
            insight = _draw_scorecard(ax, branch_df)
        results.append(
            AnalysisResult(
                slide_id="A19.1",
                title="Branch Performance Scorecard",
                chart_path=save_to,
                notes=insight,
            )
        )

        # A19.2 -- Opportunity Map
        ic_rate = ctx.client.ic_rate or 0.0015
        save_to = ctx.paths.charts_dir / "a19_2_opportunity_map.png"
        with chart_figure(figsize=(14, max(8, len(branch_df) * 0.6 + 2)), save_path=save_to) as (
            _fig,
            ax,
        ):
            insight = _draw_opportunity_bars(ax, branch_df, ic_rate)
        results.append(
            AnalysisResult(
                slide_id="A19.2",
                title="Branch Opportunity Map",
                chart_path=save_to,
                notes=insight,
            )
        )

        return results
