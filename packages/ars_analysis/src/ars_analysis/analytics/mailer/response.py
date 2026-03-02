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
    MOVEMENT_COLORS,
    RESPONSE_SEGMENTS,
    SEGMENT_COLORS,
    SUCCESSFUL_TIERS,
    VALID_RESPONSES,
    _safe,
    analyze_ladder,
    analyze_month,
    compute_inside_numbers,
    discover_pairs,
    format_title,
    parse_month,
)
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.pipeline.context import PipelineContext

BAR_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6"]


# ---------------------------------------------------------------------------
# Chart rendering helpers
# ---------------------------------------------------------------------------


def _render_donut_chart(seg_details: dict, save_path, title: str) -> bool:
    """Render donut chart (Response Share) for one month. Returns success."""
    active = [s for s in RESPONSE_SEGMENTS if s in seg_details]
    if not active:
        return False

    resp_counts = [seg_details[s]["responders"] for s in active]
    colors = [SEGMENT_COLORS.get(s, "#888") for s in active]
    total = sum(resp_counts)

    with chart_figure(figsize=(6, 5.5), save_path=save_path) as (fig, ax):
        if total > 0:
            wedges, texts, autotexts = ax.pie(
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
            ax.add_artist(centre)
            ax.text(
                0, 0, f"{total:,}\nTotal", ha="center", va="center", fontsize=16, fontweight="bold"
            )
        else:
            ax.text(
                0.5,
                0.5,
                "No Responders",
                ha="center",
                va="center",
                fontsize=16,
                transform=ax.transAxes,
            )
            ax.axis("off")
        ax.set_title(title, fontsize=18, fontweight="bold", pad=15)
    return True


def _render_hbar_chart(seg_details: dict, save_path, title: str) -> bool:
    """Render horizontal bar chart (Response Rate) for one month. Returns success."""
    active = [s for s in RESPONSE_SEGMENTS if s in seg_details]
    if not active:
        return False

    rates = [seg_details[s]["rate"] for s in active]
    resp_counts = [seg_details[s]["responders"] for s in active]
    mailed_counts = [seg_details[s]["mailed"] for s in active]
    colors = [SEGMENT_COLORS.get(s, "#888") for s in active]

    with chart_figure(figsize=(8, 7), save_path=save_path) as (fig, ax):
        y = np.arange(len(active))
        bars = ax.barh(y, rates, color=colors, edgecolor="none", height=0.65, alpha=0.90)
        max_rate = max(rates) if rates else 1
        for bar, rate, resp, mailed in zip(bars, rates, resp_counts, mailed_counts):
            bar_cy = bar.get_y() + bar.get_height() / 2
            if bar.get_width() > max_rate * 0.25:
                ax.text(
                    bar.get_width() * 0.5,
                    bar_cy,
                    f"{resp}/{mailed}",
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color="white",
                )
                ax.text(
                    bar.get_width() + max_rate * 0.02,
                    bar_cy,
                    f"{rate:.1f}%",
                    ha="left",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                )
            else:
                ax.text(
                    bar.get_width() + max_rate * 0.02,
                    bar_cy,
                    f"{resp}/{mailed} ({rate:.1f}%)",
                    ha="left",
                    va="center",
                    fontsize=12,
                    fontweight="bold",
                )
        ax.set_yticks(y)
        ax.set_yticklabels(active, fontsize=14, fontweight="bold")
        ax.set_xlabel("Response Rate (%)", fontsize=14, fontweight="bold")
        ax.set_xlim(0, max_rate * 1.45 if max_rate > 0 else 1)
        ax.invert_yaxis()
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_title(title, fontsize=18, fontweight="bold", pad=15)
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
    prev_rate: float | None = None

    for idx, (month, resp_col, mail_col) in enumerate(pairs):
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
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        # Save donut and hbar as SEPARATE PNGs for 3-column mailer_summary layout
        donut_path = ctx.paths.charts_dir / f"a13_{month.lower()}_donut.png"
        hbar_path = ctx.paths.charts_dir / f"a13_{month.lower()}_hbar.png"
        ok_donut = _render_donut_chart(seg_details, donut_path, "Response Share")
        ok_hbar = _render_hbar_chart(seg_details, hbar_path, "Response Rate")

        # Compute ladder for this month
        ladder = analyze_ladder(data, pairs, idx)

        # Build "Inside the Numbers" bullets -- member characteristics first
        inside_numbers = compute_inside_numbers(
            ctx, data, resp_col,
            ladder=ladder,
            prev_rate=prev_rate,
            current_rate=overall_rate,
        )
        inside_bullets: list[str] = []
        for pct_str, desc in inside_numbers:
            inside_bullets.append(f"{pct_str}|{desc}")
        # Segment response rates removed -- already shown in hbar chart

        # Build insight text with MoM delta
        if prev_rate is not None:
            delta = overall_rate - prev_rate
            direction = "increase" if delta >= 0 else "decrease"
            insight_text = (
                f"Mailed {total_mailed:,}, {total_resp:,} responded "
                f"({overall_rate:.1f}%) -- {abs(delta):.1f}pp {direction} vs prior mailer"
            )
        else:
            insight_text = (
                f"Mailed {total_mailed:,}, {total_resp:,} responded ({overall_rate:.1f}%)"
            )

        # Build KPIs
        kpis = {
            "Mailed": f"{total_mailed:,}",
            "Responded": f"{total_resp:,}",
            "Rate": f"{overall_rate:.1f}%",
        }

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
                chart_path=donut_path if ok_donut else None,
                extra_charts=[hbar_path] if ok_hbar else None,
                bullets=[insight_text] + inside_bullets,
                kpis=kpis,
                excel_data={"Response": pd.DataFrame(rows)},
                slide_type="mailer_summary",
                layout_index=13,
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
            "ladder": ladder,
        }
        prev_rate = overall_rate

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
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    donut_path = ctx.paths.charts_dir / "a13_agg_donut.png"
    hbar_path = ctx.paths.charts_dir / "a13_agg_hbar.png"
    ok_donut = _render_donut_chart(combined, donut_path, "Response Share")
    ok_hbar = _render_hbar_chart(combined, hbar_path, "Response Rate")

    # Compute cumulative ladder stats across all months
    cumulative_ladder: dict | None = None
    monthly_data = ctx.results.get("monthly_summaries", {})
    for m_data in monthly_data.values():
        m_ladder = m_data.get("ladder")
        if m_ladder is None:
            continue
        if cumulative_ladder is None:
            cumulative_ladder = {
                "first_count": 0,
                "repeat_count": 0,
                "movement_up": 0,
                "movement_same": 0,
                "movement_down": 0,
                "total_successful": 0,
            }
        for k in cumulative_ladder:
            cumulative_ladder[k] += m_ladder.get(k, 0)

    # Build combined responder mask across ALL months for inside numbers
    # Use the last resp_col for compute_inside_numbers base
    last_resp_col = pairs[-1][1]
    all_resp_mask = pd.Series(False, index=data.index)
    for _, resp_col, _ in pairs:
        all_resp_mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
    responders = data[all_resp_mask]
    n_resp = len(responders)

    inside_numbers = compute_inside_numbers(
        ctx, data, last_resp_col,
        ladder=cumulative_ladder,
    )
    inside_bullets: list[str] = []
    for pct_str, desc in inside_numbers:
        inside_bullets.append(f"{pct_str}|{desc}")
    # Segment response rates removed -- already shown in hbar chart

    kpis = {
        "Mailed": f"{total_m:,}",
        "Responded": f"{total_r:,}",
        "Rate": f"{overall:.1f}%",
    }

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
            chart_path=donut_path if ok_donut else None,
            extra_charts=[hbar_path] if ok_hbar else None,
            bullets=[
                f"{len(pairs)} campaigns, {total_m:,} mailed, "
                f"{total_r:,} responded ({overall:.1f}%)"
            ]
            + inside_bullets,
            kpis=kpis,
            excel_data={"AllTime": pd.DataFrame(rows)},
            slide_type="mailer_summary",
            layout_index=13,
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
        ax.legend(fontsize=11, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5)
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
    """Responder vs non-responder distribution by account age (all months combined)."""
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

    data["Date Opened"] = pd.to_datetime(data["Date Opened"], errors="coerce", format="mixed")

    # Aggregate across all months: count mailed + responders per age bucket
    resp_totals: dict[str, int] = {s[0]: 0 for s in AGE_SEGMENTS}
    mailed_totals: dict[str, int] = {s[0]: 0 for s in AGE_SEGMENTS}
    detail_rows: list[dict] = []

    for month, resp_col, mail_col in pairs:
        mailed = data[data[mail_col].isin(MAILED_SEGMENTS)]
        if mailed.empty:
            continue
        mail_date = parse_month(f"{month} Mail")
        if pd.isna(mail_date):
            mail_date = pd.Timestamp.now()

        m_age = (mail_date - mailed["Date Opened"]).dt.days / 365.25
        r_mask = mailed[resp_col].isin(RESPONSE_SEGMENTS)

        row_data: dict = {"Month": month}
        for lbl, lo, hi in AGE_SEGMENTS:
            bucket = (m_age >= lo) & (m_age < hi)
            n_mailed = int(bucket.sum())
            n_resp = int((bucket & r_mask).sum())
            mailed_totals[lbl] += n_mailed
            resp_totals[lbl] += n_resp
            row_data[f"{lbl} Mailed"] = n_mailed
            row_data[f"{lbl} Responded"] = n_resp
        detail_rows.append(row_data)

    if not detail_rows or sum(resp_totals.values()) == 0:
        return [
            AnalysisResult(
                slide_id="A14.2",
                title="Responder Account Age",
                success=False,
                error="No responders with valid dates",
            )
        ]

    age_df = pd.DataFrame(detail_rows)
    labels = [s[0] for s in AGE_SEGMENTS]
    grand_resp = sum(resp_totals.values())
    grand_mailed = sum(mailed_totals.values())

    # Compute response rate per bucket
    rates = {}
    for lbl in labels:
        m = mailed_totals[lbl]
        rates[lbl] = resp_totals[lbl] / m * 100 if m > 0 else 0

    # Identify best and worst buckets for insight
    best_bucket = max(rates, key=rates.get) if rates else "N/A"
    worst_bucket = min(rates, key=rates.get) if rates else "N/A"
    best_rate = rates.get(best_bucket, 0)
    worst_rate = rates.get(worst_bucket, 0)

    save_to = ctx.paths.charts_dir / "a14_2_account_age.png"
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    with chart_figure(figsize=(16, 9), save_path=save_to) as (fig, ax):
        y = np.arange(len(labels))
        h = 0.35

        resp_vals = [resp_totals[lbl] for lbl in labels]
        non_resp = [mailed_totals[lbl] - resp_totals[lbl] for lbl in labels]

        from ars_analysis.charts.style import SILVER, TEAL

        ax.barh(
            y + h / 2,
            resp_vals,
            h,
            label="Responders",
            color=TEAL,
            edgecolor="black",
            linewidth=1.2,
        )
        ax.barh(
            y - h / 2,
            non_resp,
            h,
            label="Non-Responders",
            color=SILVER,
            edgecolor="black",
            linewidth=1.2,
        )

        # Rate annotations on the right
        max_val = max(max(resp_vals), max(non_resp)) if resp_vals else 1
        for i, lbl in enumerate(labels):
            rate = rates[lbl]
            ax.text(
                max_val * 1.02,
                i,
                f"{rate:.1f}%",
                va="center",
                fontsize=18,
                fontweight="bold",
                color=TEAL if rate >= grand_resp / grand_mailed * 100 else "#94A3B8",
            )

        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=16, fontweight="bold")
        ax.set_xlabel("Number of Accounts", fontsize=18, fontweight="bold")
        ax.set_title(
            "Account Age: Responders vs Non-Responders",
            fontsize=22,
            fontweight="bold",
            pad=16,
        )
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.tick_params(axis="x", labelsize=14)
        ax.legend(fontsize=14, loc="lower right")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_axisbelow(True)

        # Add "Response Rate" label above the rate annotations
        ax.text(
            max_val * 1.02,
            len(labels) - 0.3,
            "Rate",
            va="bottom",
            fontsize=13,
            fontweight="bold",
            color="#64748B",
        )

        # Insight callout
        if best_rate > 0 and worst_rate > 0 and best_bucket != worst_bucket:
            ratio = best_rate / worst_rate if worst_rate > 0 else 0
            if ratio > 1.3:
                callout = (
                    f'"{best_bucket}" accounts respond at '
                    f'{ratio:.1f}x the rate of "{worst_bucket}" accounts'
                )
                ax.text(
                    0.02,
                    0.02,
                    callout,
                    transform=ax.transAxes,
                    fontsize=12,
                    style="italic",
                    color="#475569",
                    bbox={"boxstyle": "round,pad=0.4", "facecolor": "#F1F5F9", "alpha": 0.9},
                )

    ctx.results["account_age"] = {
        "totals": resp_totals,
        "mailed": mailed_totals,
        "rates": rates,
        "grand_resp": grand_resp,
        "grand_mailed": grand_mailed,
    }

    overall_rate = grand_resp / grand_mailed * 100 if grand_mailed > 0 else 0
    return [
        AnalysisResult(
            slide_id="A14.2",
            title="Responder Account Age Distribution",
            chart_path=save_to,
            excel_data={"AccountAge": age_df},
            notes=(
                f"{grand_resp:,} responders of {grand_mailed:,} mailed ({overall_rate:.1f}%) | "
                f"Best: {best_bucket} ({best_rate:.1f}%) | "
                f"Lowest: {worst_bucket} ({worst_rate:.1f}%)"
            ),
        )
    ]


# ---------------------------------------------------------------------------
# A15 -- Standalone ladder analysis slides
# ---------------------------------------------------------------------------


def _ladder_slides(ctx: PipelineContext) -> list[AnalysisResult]:
    """One 3-panel ladder chart per month (starting from 2nd month)."""
    logger.info("A15 ladder slides")
    pairs = discover_pairs(ctx)
    if len(pairs) < 2:
        return []

    data = ctx.data
    results: list[AnalysisResult] = []
    ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

    for idx in range(1, len(pairs)):
        month, resp_col, _ = pairs[idx]
        ladder = analyze_ladder(data, pairs, idx)
        if ladder is None or ladder["total_successful"] == 0:
            continue

        total = ladder["total_successful"]
        first_pct = ladder["first_count"] / total * 100
        repeat_total = ladder["repeat_count"]
        up_pct = (
            ladder["movement_up"] / repeat_total * 100 if repeat_total > 0 else 0
        )

        # Conclusion headline (exec presentation skill)
        if repeat_total > 0:
            headline = (
                f"{total:,} responders -- {first_pct:.0f}% first-time, "
                f"{up_pct:.0f}% of repeats moved up the ladder"
            )
        else:
            headline = f"{total:,} responders -- {first_pct:.0f}% first-time"

        save_to = ctx.paths.charts_dir / f"a15_{month.lower()}_ladder.png"

        with chart_figure(figsize=(18, 8), save_path=save_to) as (fig, ax):
            import matplotlib.gridspec as gridspec
            import matplotlib.pyplot as plt

            ax.remove()
            gs = gridspec.GridSpec(1, 3, figure=fig, width_ratios=[1.2, 0.8, 1], wspace=0.3)

            # Panel 1: Response Distribution (horizontal bar)
            ax1 = fig.add_subplot(gs[0, 0])
            tiers = SUCCESSFUL_TIERS
            counts = [ladder["distribution"].get(t, 0) for t in tiers]
            colors = [SEGMENT_COLORS.get(t, "#888") for t in tiers]

            y_pos = np.arange(len(tiers))
            bars = ax1.barh(y_pos, counts, color=colors, height=0.6)
            max_c = max(counts) if counts else 1
            for bar, count in zip(bars, counts):
                pct = count / total * 100 if total > 0 else 0
                ax1.text(
                    bar.get_width() + max_c * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    f"{count:,} ({pct:.0f}%)",
                    va="center",
                    fontsize=11,
                    fontweight="bold",
                )
            ax1.set_yticks(y_pos)
            ax1.set_yticklabels(tiers, fontsize=13, fontweight="bold")
            ax1.set_xlim(0, max_c * 1.35 if max_c > 0 else 1)
            ax1.invert_yaxis()
            ax1.spines["top"].set_visible(False)
            ax1.spines["right"].set_visible(False)
            ax1.set_title("Response Distribution", fontsize=15, fontweight="bold")

            # Panel 2: First vs Repeat (donut)
            ax2 = fig.add_subplot(gs[0, 1])
            if ladder["first_count"] + repeat_total > 0:
                sizes = [ladder["first_count"], repeat_total]
                labels = ["First", "Repeat"]
                donut_colors = [MOVEMENT_COLORS["First"], "#607D8B"]
                wedges, texts, autotexts = ax2.pie(
                    sizes,
                    labels=labels,
                    autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
                    colors=donut_colors,
                    startangle=90,
                    counterclock=False,
                    textprops={"fontsize": 13, "fontweight": "bold"},
                    pctdistance=0.75,
                    wedgeprops={"linewidth": 2, "edgecolor": "white"},
                )
                for at in autotexts:
                    at.set_color("white")
                    at.set_fontsize(15)
                    at.set_fontweight("bold")
                centre = plt.Circle((0, 0), 0.5, fc="white")
                ax2.add_artist(centre)
                ax2.text(
                    0, 0, f"{total:,}", ha="center", va="center",
                    fontsize=18, fontweight="bold",
                )
            ax2.set_title("First vs Repeat", fontsize=15, fontweight="bold")

            # Panel 3: Ladder Movement (repeat only)
            ax3 = fig.add_subplot(gs[0, 2])
            if repeat_total > 0:
                mv_labels = ["Up", "Same", "Down"]
                mv_counts = [
                    ladder["movement_up"],
                    ladder["movement_same"],
                    ladder["movement_down"],
                ]
                mv_colors = [
                    MOVEMENT_COLORS["Up"],
                    MOVEMENT_COLORS["Same"],
                    MOVEMENT_COLORS["Down"],
                ]
                y_pos = np.arange(len(mv_labels))
                bars = ax3.barh(y_pos, mv_counts, color=mv_colors, height=0.6)
                max_mv = max(mv_counts) if mv_counts else 1
                for bar, count in zip(bars, mv_counts):
                    pct = count / repeat_total * 100
                    ax3.text(
                        bar.get_width() + max_mv * 0.02,
                        bar.get_y() + bar.get_height() / 2,
                        f"{count:,} ({pct:.0f}%)",
                        va="center",
                        fontsize=11,
                        fontweight="bold",
                    )
                ax3.set_yticks(y_pos)
                ax3.set_yticklabels(mv_labels, fontsize=13, fontweight="bold")
                ax3.set_xlim(0, max_mv * 1.4 if max_mv > 0 else 1)
                ax3.invert_yaxis()
            else:
                ax3.text(
                    0.5, 0.5, "No repeat\nresponders",
                    ha="center", va="center", fontsize=13,
                    transform=ax3.transAxes,
                )
                ax3.set_xticks([])
                ax3.set_yticks([])
            ax3.set_title("Ladder Movement\n(Repeat Only)", fontsize=15, fontweight="bold")
            ax3.spines["top"].set_visible(False)
            ax3.spines["right"].set_visible(False)

        # Notes
        notes_parts = [
            f"Total: {total:,}",
            f"First: {ladder['first_count']:,}",
            f"Repeat: {repeat_total:,}",
        ]
        if repeat_total > 0:
            notes_parts.append(
                f"Up: {ladder['movement_up']:,}, "
                f"Same: {ladder['movement_same']:,}, "
                f"Down: {ladder['movement_down']:,}"
            )

        results.append(
            AnalysisResult(
                slide_id=f"A15.{month}",
                title=headline,
                chart_path=save_to,
                notes=" | ".join(notes_parts),
            )
        )

    return results


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
        results += _safe(lambda c: _ladder_slides(c), "A15", ctx)
        return results
