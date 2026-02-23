"""A1: Account Composition -- combined stat code + product code distribution.

Produces a single cohesive slide with stat codes (left, larger) and product codes
(right, 2/3 size).  Eligible codes are highlighted.  Dynamic insight text is
rendered above the charts.
"""

from __future__ import annotations

import textwrap

import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.style import ELIGIBLE, SILVER
from ars_analysis.pipeline.context import PipelineContext

_BUSINESS_LABELS = {
    "Yes": "Business",
    "No": "Personal",
    "Y": "Business",
    "N": "Personal",
    "": "Unknown",
    "Unknown": "Unknown",
}


def _summarize(data: pd.DataFrame, col: str) -> pd.DataFrame:
    """Build summary table for a code column."""
    data[col] = data[col].fillna("Unknown")
    data["Business?"] = data["Business?"].fillna("Unknown")

    grouped = data.groupby([col, "Business?"]).size().reset_index(name="Total Count")
    total = grouped["Total Count"].sum()
    rows: list[dict] = []
    for code in grouped[col].unique():
        cg = grouped[grouped[col] == code]
        ct = cg["Total Count"].sum()
        biz = 0
        pers = 0
        for _, r in cg.iterrows():
            lbl = _BUSINESS_LABELS.get(str(r["Business?"]).strip(), str(r["Business?"]))
            if lbl == "Business":
                biz = r["Total Count"]
            elif lbl == "Personal":
                pers = r["Total Count"]
        rows.append(
            {
                "Code": str(code),
                "Total Count": ct,
                "Percent of Total": ct / total if total else 0,
                "Business Count": biz,
                "Personal Count": pers,
            }
        )
    return pd.DataFrame(rows).sort_values("Total Count", ascending=False).reset_index(drop=True)


def _build_insight(
    stat_summary: pd.DataFrame,
    prod_summary: pd.DataFrame,
    eligible_stats: list[str],
    eligible_prods: list[str],
    total: int,
) -> str:
    """Generate 2-3 sentence insight text -- second/third layer, not obvious."""
    parts: list[str] = []

    # Eligible stat code concentration
    if eligible_stats and not stat_summary.empty:
        elig_mask = stat_summary["Code"].isin([str(s) for s in eligible_stats])
        elig_pct = stat_summary.loc[elig_mask, "Percent of Total"].sum()
        elig_count = stat_summary.loc[elig_mask, "Total Count"].sum()
        non_elig = total - elig_count
        parts.append(
            f"Eligible stat codes represent {elig_pct:.1%} of the portfolio "
            f"({elig_count:,} accounts), leaving {non_elig:,} accounts "
            f"outside the eligible universe."
        )
    elif not stat_summary.empty:
        top = stat_summary.iloc[0]
        parts.append(
            f"Stat code '{top['Code']}' dominates at {top['Percent of Total']:.1%} "
            f"of all {total:,} accounts."
        )

    # Product concentration vs diversity
    if not prod_summary.empty and len(prod_summary) >= 2:
        top3_pct = prod_summary.head(3)["Percent of Total"].sum()
        n_prods = len(prod_summary)
        if top3_pct > 0.80:
            parts.append(
                f"Product mix is highly concentrated -- top 3 of {n_prods} codes "
                f"account for {top3_pct:.1%} of volume."
            )
        else:
            parts.append(
                f"Product mix is diversified across {n_prods} codes, "
                f"with the top 3 covering {top3_pct:.1%}."
            )

    # Business vs personal skew
    total_biz = stat_summary["Business Count"].sum() if not stat_summary.empty else 0
    total_pers = stat_summary["Personal Count"].sum() if not stat_summary.empty else 0
    if total_biz + total_pers > 0:
        pers_pct = total_pers / (total_biz + total_pers)
        if pers_pct > 0.8:
            parts.append(
                f"The portfolio skews heavily personal ({pers_pct:.0%}), "
                f"suggesting consumer-focused program opportunities."
            )
        elif pers_pct < 0.5:
            parts.append(
                f"Business accounts make up {1 - pers_pct:.0%} of the portfolio, "
                f"indicating a strong commercial segment."
            )

    return "  ".join(parts[:3])


@register
class StatCodeDistribution(AnalysisModule):
    """Combined stat code + product code distribution with eligible highlighting."""

    module_id = "overview.stat_codes"
    display_name = "Account Composition"
    section = "overview"
    required_columns = ("Stat Code", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A1: Account Composition for {client}", client=ctx.client.client_id)
        data = ctx.data.copy()
        total = len(data)

        # Summaries
        stat_summary = _summarize(data.copy(), "Stat Code")

        has_product = "Product Code" in data.columns
        prod_summary = _summarize(data.copy(), "Product Code") if has_product else pd.DataFrame()

        # Eligible lists from config
        eligible_stats = [str(s) for s in (ctx.client.eligible_stat_codes or [])]
        eligible_prods = (
            [str(p) for p in (ctx.client.eligible_prod_codes or [])] if has_product else []
        )

        # Insight text
        insight = _build_insight(stat_summary, prod_summary, eligible_stats, eligible_prods, total)

        # Store summaries for product_codes module to reuse
        ctx.results["a1"] = {
            "stat_summary": stat_summary,
            "prod_summary": prod_summary,
            "insight": insight,
        }

        # Chart
        chart_path = None
        if ctx.paths.charts_dir != ctx.paths.base_dir:
            ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = ctx.paths.charts_dir / "a1_account_composition.png"
            try:
                chart_path = _render_combined(
                    stat_summary,
                    prod_summary,
                    eligible_stats,
                    eligible_prods,
                    insight,
                    save_to,
                )
            except Exception as exc:
                logger.warning("A1 chart failed: {err}", err=exc)

        # Notes
        top_stat = stat_summary.iloc[0]["Code"] if len(stat_summary) > 0 else "N/A"
        top_stat_pct = stat_summary.iloc[0]["Percent of Total"] if len(stat_summary) > 0 else 0

        excel_data = {"Stat Codes": stat_summary}
        if not prod_summary.empty:
            excel_data["Product Codes"] = prod_summary

        notes = (
            f"Top stat code '{top_stat}': {top_stat_pct:.1%}. "
            f"{len(stat_summary)} stat codes, {len(prod_summary)} product codes. "
            f"Total: {total:,}"
        )

        logger.info("A1 complete -- {n} stat codes", n=len(stat_summary))
        return [
            AnalysisResult(
                slide_id="A1",
                title="Account Composition",
                chart_path=chart_path,
                excel_data=excel_data,
                notes=notes,
            )
        ]


def _render_combined(
    stat_summary: pd.DataFrame,
    prod_summary: pd.DataFrame,
    eligible_stats: list[str],
    eligible_prods: list[str],
    insight: str,
    save_path,
) -> str | None:
    """Render combined stat + product chart.

    Layout (when product codes exist):
        Left half:  Stat Code bar chart (full height)
        Right half: Insight text (top 1/3) + Product Code bar chart (bottom 2/3)

    Both halves are the same overall shape so the slide looks cohesive.
    """
    from pathlib import Path

    has_product = not prod_summary.empty
    style_path = str(Path(__file__).parent.parent.parent / "charts" / "ars.mplstyle")

    fig_w = 18
    fig_h = 10
    fig = None
    try:
        with plt.style.context(style_path):
            fig = plt.figure(figsize=(fig_w, fig_h), dpi=150)

            if has_product:
                # 3 rows x 2 cols: left spans all 3 rows, right top = text (1 row),
                # right bottom = product chart (2 rows)
                gs = fig.add_gridspec(
                    3,
                    2,
                    height_ratios=[1, 1, 1],
                    width_ratios=[1, 1],
                    hspace=0.20,
                    wspace=0.30,
                    left=0.06,
                    right=0.96,
                    top=0.95,
                    bottom=0.06,
                )
                ax_stat = fig.add_subplot(gs[:, 0])
                ax_text = fig.add_subplot(gs[0, 1])
                ax_prod = fig.add_subplot(gs[1:, 1])
            else:
                # No product codes -- just stat code full width
                fig, ax_stat = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
                ax_text = None
                ax_prod = None

            # -- Stat code chart (left, full height) --
            _draw_bar(ax_stat, stat_summary, eligible_stats, "Stat Code Distribution", top_n=10)

            # -- Insight text panel (right top 1/3) --
            if ax_text is not None:
                ax_text.axis("off")
                wrapped = textwrap.fill(insight, width=55)
                ax_text.text(
                    0.05,
                    0.5,
                    wrapped,
                    transform=ax_text.transAxes,
                    fontsize=12,
                    color="#334155",
                    va="center",
                    ha="left",
                    style="italic",
                    linespacing=1.6,
                )

            # -- Product code chart (right bottom 2/3) --
            if ax_prod is not None and has_product:
                _draw_bar(
                    ax_prod, prod_summary, eligible_prods, "Product Code Distribution", top_n=8
                )

            fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
        fig = None
        return save_path
    finally:
        if fig is not None:
            plt.close(fig)


def _draw_bar(
    ax,
    summary: pd.DataFrame,
    eligible: list[str],
    title: str,
    top_n: int = 10,
) -> None:
    """Draw horizontal bar chart with eligible codes highlighted."""
    top = summary.head(top_n).sort_values("Total Count", ascending=True).reset_index(drop=True)
    codes = top["Code"].astype(str).tolist()
    counts = top["Total Count"].tolist()
    pcts = top["Percent of Total"].tolist()

    # Color: eligible = ELIGIBLE green, other = SILVER
    colors = [ELIGIBLE if c.strip() in eligible else SILVER for c in codes]

    ax.barh(codes, counts, color=colors, edgecolor="black", linewidth=0.8, height=0.7)

    for i, (cnt, pct) in enumerate(zip(counts, pcts)):
        ax.text(
            cnt + max(counts) * 0.015,
            i,
            f"{cnt:,.0f} ({pct:.1%})",
            va="center",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_xlabel("Account Count", fontsize=14, fontweight="bold")
    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:,.0f}"))
    ax.tick_params(axis="y", labelsize=13)
    ax.tick_params(axis="x", labelsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)

    # Legend for eligible highlight
    if eligible:
        from matplotlib.patches import Patch

        ax.legend(
            handles=[
                Patch(facecolor=ELIGIBLE, edgecolor="black", linewidth=0.8, label="Eligible"),
                Patch(facecolor=SILVER, edgecolor="black", linewidth=0.8, label="Other"),
            ],
            fontsize=10,
            loc="lower right",
        )
