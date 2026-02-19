"""Mail Campaign Insights -- A12 per-month Spend & Swipes analysis.

Slide IDs: A12.{month}.Swipes, A12.{month}.Spend (2 per mail month).
Ported from mailer_insights.py (402 lines).
"""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.mailer._helpers import (
    SEGMENT_COLORS,
    TH_SEGMENTS,
    discover_metric_cols,
    discover_pairs,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.pipeline.context import PipelineContext

# ---------------------------------------------------------------------------
# Metric calculations
# ---------------------------------------------------------------------------


def _calc_nu_metrics(
    data: pd.DataFrame,
    resp_col: str,
    mail_col: str,
    metric_cols: list[str],
) -> dict:
    """Calculate NU 5+ responder vs non-responder averages."""
    nu_resp = data[data[resp_col] == "NU 5+"]
    nu_non = data[
        ((data[resp_col] == "NU 1-4") | (data[resp_col].isna()))
        & (data[mail_col] == "NU")
    ]

    n_resp = len(nu_resp)
    n_non = len(nu_non)

    avg_resp = (
        nu_resp[metric_cols].mean()
        if n_resp > 0
        else pd.Series(0.0, index=metric_cols)
    )
    avg_non = (
        nu_non[metric_cols].mean()
        if n_non > 0
        else pd.Series(0.0, index=metric_cols)
    )

    return {
        "num_resp": n_resp,
        "num_non_resp": n_non,
        "avg_resp": avg_resp,
        "avg_non_resp": avg_non,
    }


def _calc_th_metrics(
    data: pd.DataFrame,
    resp_col: str,
    mail_col: str,
    metric_cols: list[str],
) -> dict:
    """Calculate TH segment responder averages + TNR (non-responders)."""
    result: dict = {}

    for seg in TH_SEGMENTS:
        seg_data = data[(data[mail_col] == seg) & (data[resp_col] == seg)]
        if not seg_data.empty:
            result[seg] = {
                "count": len(seg_data),
                "avg": seg_data[metric_cols].mean(),
            }

    # TH Non-Responders
    tnr = data[
        (data[mail_col].isin(TH_SEGMENTS)) & (~data[resp_col].isin(TH_SEGMENTS))
    ]
    if not tnr.empty:
        result["TNR"] = {"count": len(tnr), "avg": tnr[metric_cols].mean()}

    return result


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


def _draw_nu_chart(
    ax, dates: list, nu_metrics: dict, metric_type: str, month: str,
) -> str:
    """Draw NU responder vs non-responder trend line chart. Returns insight."""
    avg_r = nu_metrics["avg_resp"]
    avg_n = nu_metrics["avg_non_resp"]

    ax.plot(
        dates, avg_r.values, marker="o", color=SEGMENT_COLORS["NU 5+"],
        linewidth=2.5, markersize=8, label="NU 5+ Responders",
    )
    ax.plot(
        dates, avg_n.values, marker="s", color=SEGMENT_COLORS["Non-Responders"],
        linestyle="--", linewidth=2, markersize=6, alpha=0.8,
        label="NU Non-Responders",
    )

    ax.set_title(
        f"{month} -- Non-User {metric_type} per Account",
        fontsize=18, fontweight="bold",
    )
    ax.set_xlabel("Month", fontsize=14)
    ax.set_ylabel(f"Average {metric_type}", fontsize=14)

    if metric_type == "Spend":
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    else:
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.tick_params(axis="both", labelsize=14)
    for lbl in ax.xaxis.get_majorticklabels():
        lbl.set_rotation(45)
        lbl.set_ha("right")
    ax.legend(fontsize=14, loc="upper left", frameon=True, fancybox=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.3, linestyle="--")

    latest_r = avg_r.iloc[-1] if len(avg_r) > 0 else 0
    latest_n = avg_n.iloc[-1] if len(avg_n) > 0 else 0
    delta = latest_r - latest_n
    if metric_type == "Spend":
        return f"NU 5+: ${latest_r:,.0f}/acct | Non-Resp: ${latest_n:,.0f}/acct | delta ${delta:,.0f}"
    return f"NU 5+: {latest_r:,.0f}/acct | Non-Resp: {latest_n:,.0f}/acct | delta {delta:,.0f}"


def _draw_th_chart(
    ax, dates: list, th_metrics: dict, metric_type: str, month: str,
) -> str:
    """Draw TH segment trend line chart. Returns insight."""
    for seg in TH_SEGMENTS:
        if seg in th_metrics:
            avg = th_metrics[seg]["avg"]
            ax.plot(
                dates, avg.values, marker="o", color=SEGMENT_COLORS[seg],
                linewidth=2.5, markersize=8, label=seg,
            )

    if "TNR" in th_metrics:
        avg_tnr = th_metrics["TNR"]["avg"]
        ax.plot(
            dates, avg_tnr.values, marker="s",
            color=SEGMENT_COLORS["Non-Responders"],
            linestyle="--", linewidth=2, markersize=6, alpha=0.8,
            label="TH Non-Resp",
        )

    ax.set_title(
        f"{month} -- Threshold {metric_type} per Account",
        fontsize=18, fontweight="bold",
    )
    ax.set_xlabel("Month", fontsize=14)
    ax.set_ylabel(f"Average {metric_type}", fontsize=14)

    if metric_type == "Spend":
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    else:
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.tick_params(axis="both", labelsize=14)
    for lbl in ax.xaxis.get_majorticklabels():
        lbl.set_rotation(45)
        lbl.set_ha("right")
    ax.legend(fontsize=14, loc="upper left", frameon=True, fancybox=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.3, linestyle="--")

    latest_vals = {}
    for seg in TH_SEGMENTS:
        if seg in th_metrics:
            latest_vals[seg] = th_metrics[seg]["avg"].iloc[-1]

    tnr_val = th_metrics["TNR"]["avg"].iloc[-1] if "TNR" in th_metrics else 0

    if latest_vals:
        best_seg = max(latest_vals, key=latest_vals.get)
        best_val = latest_vals[best_seg]
        if metric_type == "Spend":
            return f"Best: {best_seg} (${best_val:,.0f}/acct) | TNR: ${tnr_val:,.0f}/acct"
        return f"Best: {best_seg} ({best_val:,.0f}/acct) | TNR: {tnr_val:,.0f}/acct"
    return "No threshold responders found"


# ---------------------------------------------------------------------------
# Per-month analysis
# ---------------------------------------------------------------------------


def _month_analysis(
    ctx: PipelineContext,
    month: str,
    resp_col: str,
    mail_col: str,
    spend_cols: list[str],
    swipe_cols: list[str],
) -> list[AnalysisResult]:
    """Run A12 analysis for one mail month -- up to 2 slides (Swipes + Spend)."""
    logger.info("A12 {month}", month=month)
    data = ctx.data
    results: list[AnalysisResult] = []

    spend_dates = [parse_month(c) for c in spend_cols]
    swipe_dates = [parse_month(c) for c in swipe_cols]

    nu_spend = _calc_nu_metrics(data, resp_col, mail_col, spend_cols)
    nu_swipe = _calc_nu_metrics(data, resp_col, mail_col, swipe_cols)
    th_spend = _calc_th_metrics(data, resp_col, mail_col, spend_cols)
    th_swipe = _calc_th_metrics(data, resp_col, mail_col, swipe_cols)

    # Store per-month metrics
    ctx.results[f"a12_{month.lower()}"] = {
        "month": month,
        "nu_resp": nu_spend["num_resp"],
        "nu_non_resp": nu_spend["num_non_resp"],
        "th_counts": {
            k: v["count"] for k, v in th_spend.items() if k != "TNR"
        },
    }

    # -- Swipes chart (side-by-side NU | TH) --
    if swipe_cols:
        save_to = ctx.paths.charts_dir / f"a12_{month.lower()}_swipes.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        with chart_figure(figsize=(20, 8), save_path=save_to) as (fig, ax):
            ax.remove()
            ax_nu = fig.add_subplot(1, 2, 1)
            ax_th = fig.add_subplot(1, 2, 2)
            nu_insight = _draw_nu_chart(ax_nu, swipe_dates, nu_swipe, "Swipes", month)
            th_insight = _draw_th_chart(ax_th, swipe_dates, th_swipe, "Swipes", month)
            fig.tight_layout()

        results.append(AnalysisResult(
            slide_id=f"A12.{month}.Swipes",
            title=f"Mail Campaign Swipes -- {month}",
            chart_path=save_to,
            notes=f"NU: {nu_insight} | TH: {th_insight}",
        ))

    # -- Spend chart (side-by-side NU | TH) --
    if spend_cols:
        save_to = ctx.paths.charts_dir / f"a12_{month.lower()}_spend.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        with chart_figure(figsize=(20, 8), save_path=save_to) as (fig, ax):
            ax.remove()
            ax_nu = fig.add_subplot(1, 2, 1)
            ax_th = fig.add_subplot(1, 2, 2)
            nu_insight = _draw_nu_chart(ax_nu, spend_dates, nu_spend, "Spend", month)
            th_insight = _draw_th_chart(ax_th, spend_dates, th_spend, "Spend", month)
            fig.tight_layout()

        results.append(AnalysisResult(
            slide_id=f"A12.{month}.Spend",
            title=f"Mail Campaign Spend -- {month}",
            chart_path=save_to,
            notes=f"NU: {nu_insight} | TH: {th_insight}",
        ))

    return results


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class MailerInsights(AnalysisModule):
    """Mail Campaign Insights -- per-month spend & swipes trends."""

    module_id = "mailer.insights"
    display_name = "Mail Campaign Insights"
    section = "mailer"
    required_columns = ()  # Dynamic -- depends on MmmYY columns existing

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Mailer Insights for {client}", client=ctx.client.client_id)
        pairs = discover_pairs(ctx)
        if not pairs:
            return [AnalysisResult(
                slide_id="A12", title="Mail Campaign Insights",
                success=False, error="No mail/response column pairs found",
            )]

        spend_cols, swipe_cols = discover_metric_cols(ctx)
        if not spend_cols and not swipe_cols:
            return [AnalysisResult(
                slide_id="A12", title="Mail Campaign Insights",
                success=False, error="No Spend or Swipes columns found",
            )]

        results: list[AnalysisResult] = []
        for month, resp_col, mail_col in pairs:
            try:
                results += _month_analysis(
                    ctx, month, resp_col, mail_col, spend_cols, swipe_cols,
                )
            except Exception as exc:
                logger.warning("A12.{month} failed: {err}", month=month, err=exc)
                results.append(AnalysisResult(
                    slide_id=f"A12.{month}", title=f"A12 {month}",
                    success=False, error=str(exc),
                ))

        return results
