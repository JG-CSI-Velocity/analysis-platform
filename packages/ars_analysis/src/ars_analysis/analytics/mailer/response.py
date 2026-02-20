"""Mailer Response & Demographics -- A13 + A14.

Slide IDs:
  A13.{month}  -- per-month summary (donut + hbar composite)
  A13.Agg      -- all-time aggregate summary
  A13.5        -- responder count trend (stacked bar)
  A13.6        -- response rate trend (line chart)
  A14.2        -- responder account age distribution

Ported from mailer_response.py (916 lines).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.mailer._helpers import (
    AGE_SEGMENTS,
    MAILED_SEGMENTS,
    RESPONSE_SEGMENTS,
    SEGMENT_COLORS,
    VALID_RESPONSES,
    _safe,
    analyze_month,
    discover_pairs,
    format_title,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.pipeline.context import PipelineContext

BAR_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6"]


# ---------------------------------------------------------------------------
# Chart rendering helpers
# ---------------------------------------------------------------------------


def _render_summary_chart(
    seg_details: dict,
    save_path,
    month_title: str,
) -> bool:
    """Render combined donut + hbar chart for one month. Returns success."""
    active = [s for s in RESPONSE_SEGMENTS if s in seg_details]
    if not active:
        return False

    resp_counts = [seg_details[s]["responders"] for s in active]
    rates = [seg_details[s]["rate"] for s in active]
    mailed_counts = [seg_details[s]["mailed"] for s in active]
    colors = [SEGMENT_COLORS.get(s, "#888") for s in active]
    total = sum(resp_counts)

    with chart_figure(figsize=(18, 8), save_path=save_path) as (fig, ax):
        ax.remove()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        # -- Left: Donut --
        if total > 0:
            wedges, texts, autotexts = ax1.pie(
                resp_counts,
                labels=active,
                autopct="%1.0f%%",
                colors=colors,
                startangle=90,
                pctdistance=0.78,
                textprops={"fontsize": 14, "fontweight": "bold"},
            )
            for at in autotexts:
                at.set_fontsize(13)
                at.set_fontweight("bold")
            import matplotlib.pyplot as plt

            centre = plt.Circle((0, 0), 0.50, fc="white")
            ax1.add_artist(centre)
            ax1.text(
                0,
                0,
                f"{total:,}\nTotal",
                ha="center",
                va="center",
                fontsize=16,
                fontweight="bold",
            )
        else:
            ax1.text(
                0.5,
                0.5,
                "No Responders",
                ha="center",
                va="center",
                fontsize=16,
                transform=ax1.transAxes,
            )
            ax1.axis("off")
        ax1.set_title("Response Share", fontsize=18, fontweight="bold", pad=15)

        # -- Right: Horizontal bar (response rates) --
        y = np.arange(len(active))
        bars = ax2.barh(
            y,
            rates,
            color=colors,
            edgecolor="none",
            height=0.65,
            alpha=0.90,
        )
        max_rate = max(rates) if rates else 1
        for bar, rate, resp, mailed in zip(bars, rates, resp_counts, mailed_counts):
            bar_cy = bar.get_y() + bar.get_height() / 2
            if bar.get_width() > max_rate * 0.25:
                ax2.text(
                    bar.get_width() * 0.5,
                    bar_cy,
                    f"{resp}/{mailed}",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="white",
                )
                ax2.text(
                    bar.get_width() + max_rate * 0.02,
                    bar_cy,
                    f"{rate:.1f}%",
                    ha="left",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                )
            else:
                x_off = bar.get_width() + max_rate * 0.02
                ax2.text(
                    x_off,
                    bar_cy,
                    f"{resp}/{mailed} ({rate:.1f}%)",
                    ha="left",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                )
        ax2.set_yticks(y)
        ax2.set_yticklabels(active, fontsize=14, fontweight="bold")
        ax2.set_xlabel("Response Rate (%)", fontsize=14, fontweight="bold")
        ax2.set_xlim(0, max_rate * 1.45 if max_rate > 0 else 1)
        ax2.invert_yaxis()
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        fig.suptitle(month_title, fontsize=20, fontweight="bold", y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.93])

    return True


# ---------------------------------------------------------------------------
# Per-month combined summaries
# ---------------------------------------------------------------------------


def _monthly_summaries(ctx: PipelineContext) -> list[AnalysisResult]:
    """One composite summary slide per mail month."""
    logger.info("A13 monthly summaries for {client}", client=ctx.client.client_id)
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A13",
                title="Mailer Summaries",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data
    results: list[AnalysisResult] = []
    all_monthly: dict = {}

    for month, resp_col, mail_col in pairs:
        seg_details, total_mailed, total_resp, overall_rate = analyze_month(
            data,
            resp_col,
            mail_col,
        )
        if not seg_details:
            results.append(
                AnalysisResult(
                    slide_id=f"A13.{month}",
                    title=f"A13 {month}",
                    success=False,
                    error=f"No data for {month}",
                )
            )
            continue

        month_title = f"ARS Response -- {format_title(month)} Mailer Summary"
        save_to = ctx.paths.charts_dir / f"a13_{month.lower()}_summary.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        ok = _render_summary_chart(seg_details, save_to, month_title)

        # Build Excel data
        rows = [
            {
                "Segment": s,
                "Mailed": d["mailed"],
                "Responders": d["responders"],
                "Rate %": round(d["rate"], 2),
            }
            for s, d in seg_details.items()
        ]

        results.append(
            AnalysisResult(
                slide_id=f"A13.{month}",
                title=month_title,
                chart_path=save_to if ok else None,
                excel_data={"Response": pd.DataFrame(rows)},
                notes=(
                    f"Mailed: {total_mailed:,} | Responded: {total_resp:,} | "
                    f"Rate: {overall_rate:.1f}%"
                ),
            )
        )

        all_monthly[month] = {
            "seg_details": seg_details,
            "total_mailed": total_mailed,
            "total_resp": total_resp,
            "overall_rate": overall_rate,
        }

    ctx.results["monthly_summaries"] = all_monthly
    return results


# ---------------------------------------------------------------------------
# All-time aggregate
# ---------------------------------------------------------------------------


def _aggregate_summary(ctx: PipelineContext) -> list[AnalysisResult]:
    """All-time aggregate summary combining all mail months."""
    logger.info("A13 aggregate summary")
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A13.Agg",
                title="All-Time Summary",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data
    combined: dict = {}
    for _, resp_col, mail_col in pairs:
        seg_d, _, _, _ = analyze_month(data, resp_col, mail_col)
        for seg, stats in seg_d.items():
            if seg not in combined:
                combined[seg] = {"mailed": 0, "responders": 0}
            combined[seg]["mailed"] += stats["mailed"]
            combined[seg]["responders"] += stats["responders"]

    for seg in combined:
        m = combined[seg]["mailed"]
        combined[seg]["rate"] = combined[seg]["responders"] / m * 100 if m > 0 else 0

    total_m = sum(d["mailed"] for d in combined.values())
    total_r = sum(d["responders"] for d in combined.values())
    overall = total_r / total_m * 100 if total_m > 0 else 0

    title = "ARS Response -- All-Time Mailer Summary"
    save_to = ctx.paths.charts_dir / "a13_aggregate_summary.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    ok = _render_summary_chart(combined, save_to, title)

    rows = [
        {
            "Segment": s,
            "Total Mailed": d["mailed"],
            "Total Responders": d["responders"],
            "Rate %": round(d["rate"], 2),
        }
        for s, d in combined.items()
    ]

    ctx.results["aggregate_summary"] = {
        "combined": combined,
        "total_mailed": total_m,
        "total_resp": total_r,
        "overall_rate": overall,
    }

    return [
        AnalysisResult(
            slide_id="A13.Agg",
            title=title,
            chart_path=save_to if ok else None,
            excel_data={"AllTime": pd.DataFrame(rows)},
            notes=(
                f"{len(pairs)} campaigns | Mailed: {total_m:,} | "
                f"Responded: {total_r:,} | Rate: {overall:.1f}%"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# A13.5 -- Responder count trend (stacked bar)
# ---------------------------------------------------------------------------


def _count_trend(ctx: PipelineContext) -> list[AnalysisResult]:
    """Stacked bar chart of responder counts per month by segment."""
    logger.info("A13.5 count trend")
    pairs = discover_pairs(ctx)
    if len(pairs) < 2:
        return [
            AnalysisResult(
                slide_id="A13.5",
                title="Responder Count Trend",
                success=False,
                error="Need 2+ months for trend",
            )
        ]

    data = ctx.data
    months: list[str] = []
    counts: dict[str, list[int]] = {seg: [] for seg in MAILED_SEGMENTS}
    totals: list[int] = []

    for month, resp_col, mail_col in pairs:
        months.append(month)
        month_total = 0
        for seg in MAILED_SEGMENTS:
            seg_data = data[data[mail_col] == seg]
            valid = VALID_RESPONSES[seg]
            n_resp = len(seg_data[seg_data[resp_col].isin(valid)])
            counts[seg].append(n_resp)
            month_total += n_resp
        totals.append(month_total)

    save_to = ctx.paths.charts_dir / "a13_5_count_trend.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        x = np.arange(len(months))
        bar_width = 0.6
        bottom = np.zeros(len(months))

        for seg in MAILED_SEGMENTS:
            if any(c > 0 for c in counts[seg]):
                label = "NU 5+" if seg == "NU" else seg
                color = SEGMENT_COLORS.get(seg, "#888")
                ax.bar(
                    x,
                    counts[seg],
                    bar_width,
                    bottom=bottom,
                    color=color,
                    edgecolor="white",
                    linewidth=0.5,
                    label=label,
                )
                bottom += np.array(counts[seg])

        for i, total in enumerate(totals):
            ax.text(
                i,
                total + max(totals) * 0.01,
                f"Total: {total:,}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(months, fontsize=14, fontweight="bold", rotation=45, ha="right")
        ax.set_ylabel("Count of Responders", fontsize=16, fontweight="bold")
        ax.legend(fontsize=12, loc="upper left")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylim(0, max(totals) * 1.12)

    latest = totals[-1]
    notes = f"{len(months)} months | Latest: {latest:,} responders"

    return [
        AnalysisResult(
            slide_id="A13.5",
            title="Responder Count Trend",
            chart_path=save_to,
            notes=notes,
        )
    ]


# ---------------------------------------------------------------------------
# A13.6 -- Response rate trend (line chart)
# ---------------------------------------------------------------------------


def _rate_trend(ctx: PipelineContext) -> list[AnalysisResult]:
    """Response rate trend across months per campaign type."""
    logger.info("A13.6 rate trend")
    pairs = discover_pairs(ctx)
    if len(pairs) < 2:
        return [
            AnalysisResult(
                slide_id="A13.6",
                title="Response Rate Trend",
                success=False,
                error="Need 2+ months for trend",
            )
        ]

    data = ctx.data
    months: list[str] = []
    trend: dict[str, list[float]] = {seg: [] for seg in MAILED_SEGMENTS}

    for month, resp_col, mail_col in pairs:
        months.append(month)
        for seg in MAILED_SEGMENTS:
            seg_data = data[data[mail_col] == seg]
            n = len(seg_data)
            valid = VALID_RESPONSES[seg]
            r = len(seg_data[seg_data[resp_col].isin(valid)])
            trend[seg].append(r / n * 100 if n > 0 else 0)

    save_to = ctx.paths.charts_dir / "a13_6_rate_trend.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        x = np.arange(len(months))
        for seg in MAILED_SEGMENTS:
            if trend[seg] and len(trend[seg]) == len(months):
                color = SEGMENT_COLORS.get(seg, "#888")
                label = "NU 5+" if seg == "NU" else seg
                ax.plot(
                    x,
                    trend[seg],
                    marker="o",
                    color=color,
                    linewidth=2.5,
                    markersize=8,
                    label=label,
                )

        ax.set_xticks(x)
        ax.set_xticklabels(
            months,
            fontsize=16,
            fontweight="bold",
            rotation=45,
            ha="right",
        )
        ax.set_ylabel("Response Rate (%)", fontsize=16, fontweight="bold")
        ax.set_title("Response Rate Trend by Campaign", fontsize=20, fontweight="bold")
        ax.legend(fontsize=14)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))

    ctx.results["rate_trend"] = trend
    latest_notes = ", ".join(
        f"{'NU 5+' if s == 'NU' else s}: {trend[s][-1]:.1f}%"
        for s in MAILED_SEGMENTS
        if trend.get(s)
    )
    notes = f"{len(months)} months | Latest: {latest_notes}"

    return [
        AnalysisResult(
            slide_id="A13.6",
            title="Response Rate Trend",
            chart_path=save_to,
            notes=notes,
        )
    ]


# ---------------------------------------------------------------------------
# A14.2 -- Responder account age distribution
# ---------------------------------------------------------------------------


def _account_age(ctx: PipelineContext) -> list[AnalysisResult]:
    """Responder distribution by account age across all mail months."""
    logger.info("A14.2 account age")
    pairs = discover_pairs(ctx)
    if not pairs:
        return [
            AnalysisResult(
                slide_id="A14.2",
                title="Responder Account Age",
                success=False,
                error="No mailer data",
            )
        ]

    data = ctx.data.copy()
    if "Date Opened" not in data.columns:
        return [
            AnalysisResult(
                slide_id="A14.2",
                title="Responder Account Age",
                success=False,
                error="Missing Date Opened column",
            )
        ]

    data["Date Opened"] = pd.to_datetime(data["Date Opened"], errors="coerce")
    data["_age"] = (pd.Timestamp.now() - data["Date Opened"]).dt.days / 365.25

    all_rows = []
    for month, resp_col, _ in pairs:
        resp = data[data[resp_col].isin(RESPONSE_SEGMENTS)]
        if resp.empty:
            continue
        row_data: dict = {"Month": month, "Total Responders": len(resp)}
        for lbl, lo, hi in AGE_SEGMENTS:
            row_data[lbl] = int(((resp["_age"] >= lo) & (resp["_age"] < hi)).sum())
        all_rows.append(row_data)

    if not all_rows:
        return [
            AnalysisResult(
                slide_id="A14.2",
                title="Responder Account Age",
                success=False,
                error="No responders with valid dates",
            )
        ]

    age_df = pd.DataFrame(all_rows)
    labels = [s[0] for s in AGE_SEGMENTS]
    totals = {lbl: int(age_df[lbl].sum()) for lbl in labels if lbl in age_df.columns}
    grand = sum(totals.values())
    pcts = {k: v / grand * 100 if grand > 0 else 0 for k, v in totals.items()}
    largest = max(pcts, key=pcts.get) if pcts else "N/A"

    save_to = ctx.paths.charts_dir / "a14_2_account_age.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(14, 7), save_path=save_to) as (fig, ax):
        lbl_list = list(totals.keys())
        cts = [totals[lbl] for lbl in lbl_list]
        ps = [pcts[lbl] for lbl in lbl_list]
        x = np.arange(len(lbl_list))

        bars = ax.bar(
            x,
            cts,
            color=BAR_COLORS[: len(lbl_list)],
            edgecolor="black",
            linewidth=2,
            alpha=0.8,
        )
        for bar, ct, pct in zip(bars, cts, ps):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(cts) * 0.02,
                f"{pct:.1f}%",
                ha="center",
                va="bottom",
                fontsize=16,
                fontweight="bold",
            )
            if ct > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() / 2,
                    f"{ct:,}",
                    ha="center",
                    va="center",
                    fontsize=14,
                    color="white",
                    fontweight="bold",
                )

        ax.set_xticks(x)
        ax.set_xticklabels(lbl_list, fontsize=14, fontweight="bold")
        ax.set_ylabel("Number of Responders", fontsize=16, fontweight="bold")
        ax.set_title(
            "Responder Distribution by Account Age",
            fontsize=20,
            fontweight="bold",
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    ctx.results["account_age"] = {"totals": totals, "grand": grand}

    return [
        AnalysisResult(
            slide_id="A14.2",
            title="Responder Account Age Distribution",
            chart_path=save_to,
            excel_data={"AccountAge": age_df},
            notes=(
                f"{grand:,} responders across {len(all_rows)} months | "
                f"Dominant: {largest} ({pcts.get(largest, 0):.0f}%)"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


@register
class MailerResponse(AnalysisModule):
    """Mailer Response & Demographics -- per-month summaries, trends, age."""

    module_id = "mailer.response"
    display_name = "Mailer Response Analysis"
    section = "mailer"
    required_columns = ("Date Opened",)

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Mailer Response for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(lambda c: _monthly_summaries(c), "A13", ctx)
        results += _safe(lambda c: _aggregate_summary(c), "A13.Agg", ctx)
        results += _safe(lambda c: _count_trend(c), "A13.5", ctx)
        results += _safe(lambda c: _rate_trend(c), "A13.6", ctx)
        results += _safe(lambda c: _account_age(c), "A14.2", ctx)
        return results
