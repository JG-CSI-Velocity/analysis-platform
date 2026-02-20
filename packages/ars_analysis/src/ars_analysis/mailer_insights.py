"""
mailer_insights.py — A12 Mail Campaign Spend & Swipes Analysis
================================================================
Analyses by mail month (dynamic column discovery):
  A12.{month} Spend  — NU 5+ vs Non-Responder + TH segment spend trends
  A12.{month} Swipes — NU 5+ vs Non-Responder + TH segment swipe trends

Produces 2 slides per mail month (side-by-side NU | TH charts).

Column patterns:
  MmmYY Mail   — mail segment assignment (NU, TH-10, TH-15, TH-20, TH-25)
  MmmYY Resp   — response code (NU 5+, NU 1-4, TH-10, TH-15, TH-20, TH-25)
  MmmYY Spend  — monthly spend per account
  MmmYY Swipes — monthly swipe count per account

Usage:
    from mailer_insights import run_mailer_insights_suite
    ctx = run_mailer_insights_suite(ctx)
"""

import matplotlib
import pandas as pd

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from ars_analysis.mailer_common import (
    SPEND_PATTERN,
    SWIPE_PATTERN,
    TH_SEGMENTS,
)
from ars_analysis.mailer_common import (
    parse_month as _parse_month,
)
from ars_analysis.mailer_common import (
    report as _report,
)
from ars_analysis.mailer_common import (
    save_chart as _save_chart,
)
from ars_analysis.mailer_common import (
    save_to_excel as _save,
)
from ars_analysis.mailer_common import (
    slide as _slide,
)

# =============================================================================
# CHART COLORS
# =============================================================================

COLOR_SCHEME = {
    "No-Mail": "#F5F5F5",
    "Non-Responders": "#404040",
    "NU 5+": "#E74C3C",
    "TH-10": "#3498DB",
    "TH-15": "#2ECC71",
    "TH-20": "#F39C12",
    "TH-25": "#9B59B6",
}


def _behavior_commentary(avg_series, metric_type):
    """Build 1/3/6-month behavior change text from a metric series."""
    n = len(avg_series)
    if n < 2:
        return ""
    latest = avg_series.iloc[-1]
    parts = []
    for lookback, label in [(1, "1-mo"), (3, "3-mo"), (6, "6-mo")]:
        if n > lookback:
            prev = avg_series.iloc[-(lookback + 1)]
            if prev and prev != 0:
                pct = (latest - prev) / abs(prev) * 100
                sign = "+" if pct >= 0 else ""
                if metric_type == "Spend":
                    parts.append(f"{label}: {sign}{pct:.1f}% (${latest:,.0f})")
                else:
                    parts.append(f"{label}: {sign}{pct:.1f}% ({latest:,.0f})")
    return " | ".join(parts) if parts else ""


# =============================================================================
# COLUMN DISCOVERY
# =============================================================================


def discover_mailer_columns(ctx):
    """
    Discover all MmmYY Mail/Resp/Spend/Swipes columns from the data.
    Returns sorted list of (month_label, resp_col, mail_col) tuples
    and the spend/swipe column lists.
    """
    from ars_analysis.mailer_common import discover_pairs as _dp

    pairs = _dp(ctx)

    data = ctx["data"]
    cols = list(data.columns)
    client_id = ctx.get("client_id", "")

    # Metric columns
    spend_cols = sorted([c for c in cols if SPEND_PATTERN.match(c)], key=_parse_month)
    swipe_cols = sorted([c for c in cols if SWIPE_PATTERN.match(c)], key=_parse_month)

    if client_id == "1200":
        cutoff = pd.to_datetime("Apr24", format="%b%y")
        spend_cols = [c for c in spend_cols if _parse_month(c) >= cutoff]
        swipe_cols = [c for c in swipe_cols if _parse_month(c) >= cutoff]

    return pairs, spend_cols, swipe_cols


# =============================================================================
# METRIC CALCULATIONS
# =============================================================================


def _calc_nu_metrics(data, resp_col, mail_col, metric_cols):
    """Calculate NU 5+ responder vs non-responder averages."""
    nu_resp = data[data[resp_col] == "NU 5+"]
    nu_non = data[
        ((data[resp_col] == "NU 1-4") | (data[resp_col].isna())) & (data[mail_col] == "NU")
    ]

    n_resp = len(nu_resp)
    n_non = len(nu_non)

    avg_resp = nu_resp[metric_cols].mean() if n_resp > 0 else pd.Series(0.0, index=metric_cols)
    avg_non = nu_non[metric_cols].mean() if n_non > 0 else pd.Series(0.0, index=metric_cols)

    return {
        "num_resp": n_resp,
        "num_non_resp": n_non,
        "avg_resp": avg_resp,
        "avg_non_resp": avg_non,
    }


def _calc_th_metrics(data, resp_col, mail_col, metric_cols):
    """Calculate TH segment responder averages + TNR (non-responders)."""
    result = {}

    for seg in TH_SEGMENTS:
        seg_data = data[(data[mail_col] == seg) & (data[resp_col] == seg)]
        if not seg_data.empty:
            result[seg] = {"count": len(seg_data), "avg": seg_data[metric_cols].mean()}

    # TH Non-Responders
    tnr = data[(data[mail_col].isin(TH_SEGMENTS)) & (~data[resp_col].isin(TH_SEGMENTS))]
    if not tnr.empty:
        result["TNR"] = {"count": len(tnr), "avg": tnr[metric_cols].mean()}

    return result


# =============================================================================
# CHART RENDERING
# =============================================================================


def _draw_nu_chart(ax, dates, nu_metrics, metric_type, month):
    """Draw NU responder vs non-responder trend line chart."""
    avg_r = nu_metrics["avg_resp"]
    avg_n = nu_metrics["avg_non_resp"]

    ax.plot(
        dates,
        avg_r.values,
        marker="o",
        color=COLOR_SCHEME["NU 5+"],
        linewidth=2.5,
        markersize=8,
        label="NU 5+ Responders",
    )
    ax.plot(
        dates,
        avg_n.values,
        marker="s",
        color=COLOR_SCHEME["Non-Responders"],
        linestyle="--",
        linewidth=2,
        markersize=6,
        alpha=0.8,
        label="NU Non-Responders",
    )

    ax.set_title(f"{month} — Non-User {metric_type} per Account", fontsize=18, fontweight="bold")
    ax.set_xlabel("Month", fontsize=14)
    ax.set_ylabel(f"Average {metric_type}", fontsize=14)

    if metric_type == "Spend":
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    else:
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.tick_params(axis="both", labelsize=14)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.legend(fontsize=14, loc="upper left", frameon=True, fancybox=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)

    # Insight text
    latest_r = avg_r.iloc[-1] if len(avg_r) > 0 else 0
    latest_n = avg_n.iloc[-1] if len(avg_n) > 0 else 0
    delta = latest_r - latest_n
    if metric_type == "Spend":
        insight = f"NU 5+: ${latest_r:,.0f}/acct | Non-Resp: ${latest_n:,.0f}/acct | Δ${delta:,.0f}"
    else:
        insight = f"NU 5+: {latest_r:,.0f}/acct | Non-Resp: {latest_n:,.0f}/acct | Δ{delta:,.0f}"

    return insight


def _draw_th_chart(ax, dates, th_metrics, metric_type, month):
    """Draw TH segment trend line chart."""
    for seg in TH_SEGMENTS:
        if seg in th_metrics:
            avg = th_metrics[seg]["avg"]
            ax.plot(
                dates,
                avg.values,
                marker="o",
                color=COLOR_SCHEME[seg],
                linewidth=2.5,
                markersize=8,
                label=seg,
            )

    if "TNR" in th_metrics:
        avg_tnr = th_metrics["TNR"]["avg"]
        ax.plot(
            dates,
            avg_tnr.values,
            marker="s",
            color=COLOR_SCHEME["Non-Responders"],
            linestyle="--",
            linewidth=2,
            markersize=6,
            alpha=0.8,
            label="TH Non-Resp",
        )

    ax.set_title(f"{month} — Threshold {metric_type} per Account", fontsize=18, fontweight="bold")
    ax.set_xlabel("Month", fontsize=14)
    ax.set_ylabel(f"Average {metric_type}", fontsize=14)

    if metric_type == "Spend":
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:,.0f}"))
    else:
        ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.tick_params(axis="both", labelsize=14)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    ax.legend(fontsize=14, loc="upper left", frameon=True, fancybox=True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(False)

    # Insight text
    latest_vals = {}
    for seg in TH_SEGMENTS:
        if seg in th_metrics:
            latest_vals[seg] = th_metrics[seg]["avg"].iloc[-1]

    tnr_val = th_metrics["TNR"]["avg"].iloc[-1] if "TNR" in th_metrics else 0

    if latest_vals:
        best_seg = max(latest_vals, key=latest_vals.get)
        best_val = latest_vals[best_seg]
        if metric_type == "Spend":
            insight = f"Best: {best_seg} (${best_val:,.0f}/acct) | TNR: ${tnr_val:,.0f}/acct"
        else:
            insight = f"Best: {best_seg} ({best_val:,.0f}/acct) | TNR: {tnr_val:,.0f}/acct"
    else:
        insight = "No threshold responders found"

    return insight


# =============================================================================
# A12 — PER-MONTH ANALYSIS
# =============================================================================


def run_month_analysis(ctx, month, resp_col, mail_col, spend_cols, swipe_cols):
    """Run A12 analysis for a single mail month — produces 2 slides (Spend + Swipes)."""
    _report(ctx, f"\n   📅 A12 — {month}")
    data = ctx["data"]
    chart_dir = ctx["chart_dir"]

    # Parse metric column dates
    spend_dates = [_parse_month(c) for c in spend_cols]
    swipe_dates = [_parse_month(c) for c in swipe_cols]

    # ── Calculate metrics ──
    nu_spend = _calc_nu_metrics(data, resp_col, mail_col, spend_cols)
    nu_swipe = _calc_nu_metrics(data, resp_col, mail_col, swipe_cols)
    th_spend = _calc_th_metrics(data, resp_col, mail_col, spend_cols)
    th_swipe = _calc_th_metrics(data, resp_col, mail_col, swipe_cols)

    _report(
        ctx,
        f"      NU Responders: {nu_spend['num_resp']:,}  |  Non-Resp: {nu_spend['num_non_resp']:,}",
    )
    th_total = sum(v["count"] for k, v in th_spend.items() if k != "TNR")
    th_detail = ", ".join(f"{k}={v['count']}" for k, v in th_spend.items() if k != "TNR")
    _report(ctx, f"      TH Responders: {th_total:,}  ({th_detail})")

    month_results = {
        "month": month,
        "nu_resp": nu_spend["num_resp"],
        "nu_non_resp": nu_spend["num_non_resp"],
        "th_counts": {k: v["count"] for k, v in th_spend.items() if k != "TNR"},
    }

    # ── SLIDE 1: SWIPES (per mapping: Swipes #37 before Spend #38) ──
    if swipe_cols:
        try:
            fig, (ax_nu, ax_th) = plt.subplots(1, 2, figsize=(20, 8))
            nu_swipe_insight = _draw_nu_chart(ax_nu, swipe_dates, nu_swipe, "Swipes", month)
            th_swipe_insight = _draw_th_chart(ax_th, swipe_dates, th_swipe, "Swipes", month)
            plt.tight_layout()

            cp = _save_chart(fig, chart_dir / f"a12_{month.lower()}_swipes.png")

            behavior = _behavior_commentary(nu_swipe["avg_resp"], "Swipes")
            subtitle = behavior if behavior else f"NU: {nu_swipe_insight}"
            _slide(
                ctx,
                f"A12 - {month} Swipes",
                {
                    "title": f"Mail Campaign Swipes Analysis — {month}",
                    "subtitle": subtitle,
                    "layout_index": 13,
                    "chart_path": cp,
                    "insights": [f"Non-User: {nu_swipe_insight}", f"Threshold: {th_swipe_insight}"],
                    "category": "Mailer",
                },
            )
            month_results["swipe_insight_nu"] = nu_swipe_insight
            month_results["swipe_insight_th"] = th_swipe_insight
        except Exception as e:
            _report(ctx, f"      ⚠️ Swipes chart: {e}")

    # ── SLIDE 2: SPEND ──
    if spend_cols:
        try:
            fig, (ax_nu, ax_th) = plt.subplots(1, 2, figsize=(20, 8))
            nu_spend_insight = _draw_nu_chart(ax_nu, spend_dates, nu_spend, "Spend", month)
            th_spend_insight = _draw_th_chart(ax_th, spend_dates, th_spend, "Spend", month)
            plt.tight_layout()

            cp = _save_chart(fig, chart_dir / f"a12_{month.lower()}_spend.png")

            behavior = _behavior_commentary(nu_spend["avg_resp"], "Spend")
            subtitle = behavior if behavior else f"NU: {nu_spend_insight}"
            _slide(
                ctx,
                f"A12 - {month} Spend",
                {
                    "title": f"Mail Campaign Spend Analysis — {month}",
                    "subtitle": subtitle,
                    "layout_index": 13,
                    "chart_path": cp,
                    "insights": [f"Non-User: {nu_spend_insight}", f"Threshold: {th_spend_insight}"],
                    "category": "Mailer",
                },
            )
            month_results["spend_insight_nu"] = nu_spend_insight
            month_results["spend_insight_th"] = th_spend_insight
        except Exception as e:
            _report(ctx, f"      ⚠️ Spend chart: {e}")

    return month_results


# =============================================================================
# SUITE RUNNER
# =============================================================================


def run_mailer_insights_suite(ctx):
    """Run the full A12 Mailer Insights suite."""
    from ars_analysis.pipeline import save_to_excel

    ctx["_save_to_excel"] = save_to_excel

    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "📧 A12 — MAIL CAMPAIGN INSIGHTS (Spend & Swipes)")
    _report(ctx, "=" * 60)

    # Discover columns
    pairs, spend_cols, swipe_cols = discover_mailer_columns(ctx)

    if not pairs:
        _report(ctx, "   ⚠️ No mail/response column pairs found — skipping A12")
        ctx["results"]["mailer_insights"] = {}
        return ctx

    _report(ctx, f"   Found {len(pairs)} mail months: {', '.join(m for m, _, _ in pairs)}")
    _report(ctx, f"   Spend columns: {len(spend_cols)}  |  Swipe columns: {len(swipe_cols)}")

    if not spend_cols and not swipe_cols:
        _report(ctx, "   ⚠️ No Spend or Swipes columns found — skipping A12")
        ctx["results"]["mailer_insights"] = {}
        return ctx

    # Store discovered columns in ctx for downstream modules
    ctx["mailer_pairs"] = pairs
    ctx["spend_cols"] = spend_cols
    ctx["swipe_cols"] = swipe_cols

    all_results = {}
    for month, resp_col, mail_col in pairs:
        try:
            result = run_month_analysis(ctx, month, resp_col, mail_col, spend_cols, swipe_cols)
            all_results[month] = result
        except Exception as e:
            _report(ctx, f"   ⚠️ {month} failed: {e}")
            import traceback

            traceback.print_exc()

    # ── Summary Excel export ──
    if all_results:
        try:
            rows = []
            for month, r in all_results.items():
                row = {
                    "Month": month,
                    "NU Responders": r["nu_resp"],
                    "NU Non-Responders": r["nu_non_resp"],
                }
                row.update(r.get("th_counts", {}))
                row["NU Spend Insight"] = r.get("spend_insight_nu", "")
                row["TH Spend Insight"] = r.get("spend_insight_th", "")
                row["NU Swipes Insight"] = r.get("swipe_insight_nu", "")
                row["TH Swipes Insight"] = r.get("swipe_insight_th", "")
                rows.append(row)
            summary_df = pd.DataFrame(rows)

            total_nu = summary_df["NU Responders"].sum()
            total_non = summary_df["NU Non-Responders"].sum()
            total_th = sum(summary_df[s].sum() for s in TH_SEGMENTS if s in summary_df.columns)

            _save(
                ctx,
                summary_df,
                "A12-MailInsights",
                "Mail Campaign Performance Summary",
                {
                    "Months Analyzed": len(all_results),
                    "Total NU Responders": f"{total_nu:,}",
                    "Total NU Non-Responders": f"{total_non:,}",
                    "Total TH Responders": f"{total_th:,}",
                },
            )
        except Exception as e:
            _report(ctx, f"   ⚠️ Summary export: {e}")

    ctx["results"]["mailer_insights"] = all_results
    slides = len([s for s in ctx["all_slides"] if s["category"] == "Mailer"])
    _report(ctx, f"\n✅ A12 complete — {slides} Mailer slides created ({len(all_results)} months)")
    return ctx


if __name__ == "__main__":
    print("mailer_insights module — import and call run_mailer_insights_suite(ctx)")
