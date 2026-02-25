"""Dormant Opportunity Analysis -- A20 series.

Identifies high-value accounts without debit cards and accounts with declining
spend, quantifying the untapped revenue potential.

Slide IDs: A20.1 (summary KPIs), A20.2 (at-risk bar), A20.3 (priority scatter).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import NEGATIVE, SILVER, TEAL
from ars_analysis.pipeline.context import PipelineContext

AVG_ANNUAL_IC = 216.0  # PULSE benchmark per active card


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _detect_debit_col(df: pd.DataFrame) -> str | None:
    for col in ("Debit?", "Debit", "DC Indicator"):
        if col in df.columns:
            return col
    return None


def _detect_spend_cols(df: pd.DataFrame) -> list[str]:
    """Find monthly spend columns (MmmYY Spend pattern)."""
    return sorted(
        [c for c in df.columns if c.endswith(" Spend")],
        key=lambda c: c,
    )


def _find_dormant_accounts(df: pd.DataFrame) -> pd.DataFrame | None:
    """Find high-balance accounts without debit cards.

    Returns subset of rows where Debit? != Yes AND balance is in top quartile.
    """
    debit_col = _detect_debit_col(df)
    if debit_col is None:
        return None

    # Balance column detection
    bal_col = None
    for col in ("Avg Bal", "Balance", "Average Balance"):
        if col in df.columns:
            bal_col = col
            break
    if bal_col is None:
        return None

    no_debit = df[~df[debit_col].isin(["Yes", "Y", True, 1])].copy()
    if len(no_debit) == 0:
        return None

    # Top quartile by balance
    q75 = df[bal_col].quantile(0.75)
    high_bal = no_debit[no_debit[bal_col] >= q75]
    if len(high_bal) == 0:
        return None

    return high_bal


def _find_declining_accounts(df: pd.DataFrame) -> pd.DataFrame | None:
    """Find accounts with declining spend (first half vs second half > 20% drop).

    Returns DataFrame with added 'spend_decline' column.
    """
    spend_cols = _detect_spend_cols(df)
    if len(spend_cols) < 4:
        return None

    mid = len(spend_cols) // 2
    first_half = spend_cols[:mid]
    second_half = spend_cols[mid:]

    result = df.copy()
    result["_first_half_avg"] = result[first_half].mean(axis=1)
    result["_second_half_avg"] = result[second_half].mean(axis=1)

    # Avoid division by zero
    mask = result["_first_half_avg"] > 0
    result["spend_decline"] = 0.0
    result.loc[mask, "spend_decline"] = (
        result.loc[mask, "_first_half_avg"] - result.loc[mask, "_second_half_avg"]
    ) / result.loc[mask, "_first_half_avg"]

    declining = result[result["spend_decline"] > 0.20]
    if len(declining) == 0:
        return None

    return declining.drop(columns=["_first_half_avg", "_second_half_avg"])


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_dormant_summary(ax, dormant_df: pd.DataFrame, total_eligible: int) -> str:
    """Draw KPI panel for dormant high-balance accounts. Returns insight."""
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    n_dormant = len(dormant_df)
    pct = n_dormant / total_eligible * 100 if total_eligible > 0 else 0
    opportunity = n_dormant * AVG_ANNUAL_IC

    # Balance detection
    bal_col = None
    for col in ("Avg Bal", "Balance", "Average Balance"):
        if col in dormant_df.columns:
            bal_col = col
            break
    avg_bal = dormant_df[bal_col].mean() if bal_col else 0

    # KPI cards layout
    kpis = [
        ("Dormant High-Balance", f"{n_dormant:,}", "accounts without debit cards"),
        ("% of Eligible", f"{pct:.1f}%", "in top balance quartile"),
        ("Annual IC Opportunity", f"${opportunity:,.0f}", f"at ${AVG_ANNUAL_IC}/card/year"),
        ("Avg Balance", f"${avg_bal:,.0f}", "per dormant account"),
    ]

    for i, (label, value, sub) in enumerate(kpis):
        x = 0.125 + (i % 2) * 0.45
        y = 0.7 - (i // 2) * 0.4
        ax.text(x, y + 0.08, label, fontsize=13, color="#666", ha="center", va="bottom")
        ax.text(x, y, value, fontsize=28, fontweight="bold", color=TEAL, ha="center", va="center")
        ax.text(x, y - 0.06, sub, fontsize=11, color="#999", ha="center", va="top")

    ax.set_title(
        "Dormant Opportunity Summary", fontsize=20, fontweight="bold", pad=20, color="#1E3D59"
    )

    return f"{n_dormant:,} high-balance accounts without debit = ${opportunity:,.0f}/yr opportunity"


def _draw_at_risk(ax, declining_df: pd.DataFrame) -> str:
    """Draw bar chart of at-risk accounts by decline severity. Returns insight."""
    declines = declining_df["spend_decline"] * 100

    # Bucket into severity bands
    bins = [20, 30, 40, 50, 100]
    labels = ["20-30%", "30-40%", "40-50%", "50%+"]
    buckets = pd.cut(declines, bins=bins, labels=labels, right=True)
    counts = buckets.value_counts().reindex(labels, fill_value=0)

    colors = [SILVER, NEGATIVE + "99", NEGATIVE + "CC", NEGATIVE]
    bars = ax.bar(
        counts.index, counts.values, color=colors[: len(counts)], edgecolor="white", linewidth=1.5
    )

    for bar, val in zip(bars, counts.values):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                str(val),
                ha="center",
                va="bottom",
                fontsize=16,
                fontweight="bold",
            )

    ax.set_xlabel("Spend Decline Severity", fontsize=14)
    ax.set_ylabel("Number of Accounts", fontsize=14)
    ax.set_title("At-Risk Members (Declining Spend)", fontsize=20, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.2, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)

    total = len(declining_df)
    severe = int((declines > 40).sum())
    return f"{total:,} accounts declining; {severe:,} with >40% spend drop"


def _draw_priority_matrix(ax, df: pd.DataFrame) -> str:
    """Draw scatter of balance vs spend decline, sized by account age. Returns insight."""
    bal_col = None
    for col in ("Avg Bal", "Balance", "Average Balance"):
        if col in df.columns:
            bal_col = col
            break
    if bal_col is None:
        return ""

    x = df["spend_decline"] * 100
    y = df[bal_col]

    # Size by account age (if Date Opened exists)
    if "Date Opened" in df.columns:
        today = pd.Timestamp.now()
        age_years = (
            today - pd.to_datetime(df["Date Opened"], errors="coerce", format="mixed")
        ).dt.days / 365.25
        sizes = np.clip(age_years * 15, 20, 200)
    else:
        sizes = 60

    # Color by branch
    branch_col = None
    for col in ("Branch", "branch"):
        if col in df.columns:
            branch_col = col
            break

    if branch_col and df[branch_col].nunique() <= 10:
        branches = df[branch_col].astype(str)
        unique_branches = branches.unique()
        cmap = {b: i for i, b in enumerate(unique_branches)}
        colors = [cmap[b] for b in branches]
        ax.scatter(
            x, y, s=sizes, c=colors, cmap="tab10", alpha=0.7, edgecolors="white", linewidth=0.5
        )
        # Legend
        for b in unique_branches[:6]:
            ax.scatter([], [], c=f"C{cmap[b]}", label=b, s=50)
        ax.legend(fontsize=11, loc="upper left", title="Branch", frameon=True)
    else:
        ax.scatter(x, y, s=sizes, c=NEGATIVE, alpha=0.6, edgecolors="white", linewidth=0.5)

    ax.set_xlabel("Spend Decline (%)", fontsize=14)
    ax.set_ylabel("Account Balance ($)", fontsize=14)
    ax.set_title("Targeting Priority Matrix", fontsize=20, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.15, linestyle="--")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=12)
    ax.yaxis.set_major_formatter(lambda x, _: f"${x:,.0f}")

    # Quadrant annotation
    med_x = x.median()
    med_y = y.median()
    high_priority = len(df[(df["spend_decline"] * 100 > med_x) & (df[bal_col] > med_y)])
    return f"{high_priority:,} high-priority targets (high balance + steep decline)"


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class DormantOpportunity(AnalysisModule):
    """Dormant Opportunity Analysis -- A20 series."""

    module_id = "insights.dormant"
    display_name = "Dormant Opportunity"
    section = "insights"
    required_columns = ()

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Dormant opportunity for {client}", client=ctx.client.client_id)

        data = ctx.data
        if data is None or len(data) == 0:
            return [
                AnalysisResult(
                    slide_id="A20",
                    title="Dormant Opportunity",
                    success=False,
                    error="No data available",
                )
            ]

        results: list[AnalysisResult] = []
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
        total_eligible = len(ctx.subsets.eligible_data) if ctx.subsets else len(data)

        # A20.1 -- Dormant Summary
        dormant_df = _find_dormant_accounts(data)
        if dormant_df is not None and len(dormant_df) > 0:
            save_to = ctx.paths.charts_dir / "a20_1_dormant_summary.png"
            with chart_figure(figsize=(14, 8), save_path=save_to) as (_fig, ax):
                insight = _draw_dormant_summary(ax, dormant_df, total_eligible)
            results.append(
                AnalysisResult(
                    slide_id="A20.1",
                    title="Dormant Opportunity Summary",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A20.2 -- At-Risk Identification
        declining_df = _find_declining_accounts(data)
        if declining_df is not None and len(declining_df) > 0:
            save_to = ctx.paths.charts_dir / "a20_2_at_risk.png"
            with chart_figure(figsize=(12, 8), save_path=save_to) as (_fig, ax):
                insight = _draw_at_risk(ax, declining_df)
            results.append(
                AnalysisResult(
                    slide_id="A20.2",
                    title="At-Risk Member Identification",
                    chart_path=save_to,
                    notes=insight,
                )
            )

        # A20.3 -- Priority Matrix (only if we have declining accounts with balance)
        if declining_df is not None and len(declining_df) > 0:
            save_to = ctx.paths.charts_dir / "a20_3_priority_matrix.png"
            with chart_figure(figsize=(14, 10), save_path=save_to) as (_fig, ax):
                insight = _draw_priority_matrix(ax, declining_df)
            if insight:
                results.append(
                    AnalysisResult(
                        slide_id="A20.3",
                        title="Targeting Priority Matrix",
                        chart_path=save_to,
                        notes=insight,
                    )
                )

        if not results:
            return [
                AnalysisResult(
                    slide_id="A20",
                    title="Dormant Opportunity",
                    success=False,
                    error="No dormant or declining accounts found",
                )
            ]

        return results
