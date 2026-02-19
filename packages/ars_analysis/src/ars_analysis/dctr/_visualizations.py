"""Extended DCTR visualization functions (A7 charts and composite slides)."""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from ars_analysis.dctr._helpers import _dctr, _report, _save, _save_chart, _slide
from ars_analysis.dctr._shared import (
    _branch_dctr,
)

# =============================================================================
# FUNNEL: Account & Debit Card Funnel (A7.7)
# =============================================================================


def run_dctr_funnel(ctx):
    _report(ctx, "\n🎯 DCTR — Account Funnel")
    chart_dir = ctx["chart_dir"]
    data = ctx["data"]
    oa = ctx["open_accounts"]
    ed = ctx["eligible_data"]
    ewd = ctx["eligible_with_debit"]

    ta = len(data)
    to = len(oa)
    te = len(ed)
    td = len(ewd)
    through = td / ta * 100 if ta else 0
    dctr_e = td / te * 100 if te else 0

    # Personal/Business splits
    tp = len(data[data["Business?"] == "No"])
    tb = len(data[data["Business?"] == "Yes"])
    has_biz = tb > 0
    op = len(oa[oa["Business?"] == "No"])
    ob = len(oa[oa["Business?"] == "Yes"])
    ep = len(ctx["eligible_personal"])
    eb_cnt = len(ctx["eligible_business"])
    dp = ctx["results"].get("dctr_4", {}).get("insights", {}).get("with_debit_count", 0)
    db_cnt = ctx["results"].get("dctr_5", {}).get("insights", {}).get("with_debit_count", 0)

    try:
        import matplotlib.colors as mcolors
        import matplotlib.patches as patches

        fig, ax = plt.subplots(figsize=(10, 12))
        try:
            fig.patch.set_facecolor("white")
            ax.set_facecolor("#f8f9fa")

            stages = [
                {
                    "name": "Total\nAccounts",
                    "total": ta,
                    "personal": tp,
                    "business": tb,
                    "color": "#1f77b4",
                },
                {
                    "name": "Open\nAccounts",
                    "total": to,
                    "personal": op,
                    "business": ob,
                    "color": "#2c7fb8",
                },
                {
                    "name": "Eligible\nAccounts",
                    "total": te,
                    "personal": ep,
                    "business": eb_cnt,
                    "color": "#ff7f0e",
                },
                {
                    "name": "Eligible With\nDebit Card",
                    "total": td,
                    "personal": dp,
                    "business": db_cnt,
                    "color": "#41b6c4",
                },
            ]

            max_width = 0.8
            stage_height = 0.15
            y_start = 0.85
            stage_gap = 0.02
            current_y = y_start

            for i, stage in enumerate(stages):
                width = (
                    max_width * (stage["total"] / stages[0]["total"])
                    if stages[0]["total"] > 0
                    else 0.1
                )

                if has_biz and stage["total"] > 0:
                    p_ratio = stage["personal"] / stage["total"]
                    p_width = width * p_ratio
                    b_width = width * (1 - p_ratio)
                    # Personal (lighter)
                    rect_p = patches.FancyBboxPatch(
                        (0.5 - width / 2, current_y - stage_height),
                        p_width,
                        stage_height,
                        boxstyle="round,pad=0.01",
                        facecolor=stage["color"],
                        edgecolor="white",
                        linewidth=2,
                        alpha=0.9,
                    )
                    ax.add_patch(rect_p)
                    # Business (darker)
                    rgb = mcolors.hex2color(stage["color"])
                    darker = mcolors.rgb2hex(tuple([c * 0.7 for c in rgb]))
                    rect_b = patches.FancyBboxPatch(
                        (0.5 - width / 2 + p_width, current_y - stage_height),
                        b_width,
                        stage_height,
                        boxstyle="round,pad=0.01",
                        facecolor=darker,
                        edgecolor="white",
                        linewidth=2,
                        alpha=0.9,
                    )
                    ax.add_patch(rect_b)
                    # Labels inside
                    if p_width > 0.05:
                        ax.text(
                            0.5 - width / 2 + p_width / 2,
                            current_y - stage_height / 2,
                            f"{stage['personal']:,}",
                            ha="center",
                            va="center",
                            fontsize=20,
                            color="white",
                            fontweight="bold",
                        )
                    if b_width > 0.05:
                        ax.text(
                            0.5 - width / 2 + p_width + b_width / 2,
                            current_y - stage_height / 2,
                            f"{stage['business']:,}",
                            ha="center",
                            va="center",
                            fontsize=20,
                            color="white",
                            fontweight="bold",
                        )
                    # Total to right
                    ax.text(
                        0.5 + width / 2 + 0.05,
                        current_y - stage_height / 2,
                        f"Total\n{stage['total']:,}",
                        ha="left",
                        va="center",
                        fontsize=18,
                        fontweight="bold",
                        color="black",
                        bbox=dict(
                            boxstyle="round,pad=0.4",
                            facecolor="white",
                            edgecolor="black",
                            alpha=0.9,
                        ),
                    )
                else:
                    rect = patches.FancyBboxPatch(
                        (0.5 - width / 2, current_y - stage_height),
                        width,
                        stage_height,
                        boxstyle="round,pad=0.01",
                        facecolor=stage["color"],
                        edgecolor="white",
                        linewidth=3,
                        alpha=0.9,
                    )
                    ax.add_patch(rect)
                    ax.text(
                        0.5,
                        current_y - stage_height / 2,
                        f"{stage['total']:,}",
                        ha="center",
                        va="center",
                        fontsize=28,
                        fontweight="bold",
                        color="white",
                        zorder=10,
                    )

                # Stage name on left
                ax.text(
                    0.5 - width / 2 - 0.05,
                    current_y - stage_height / 2,
                    stage["name"],
                    ha="right",
                    va="center",
                    fontsize=20,
                    fontweight="600",
                    color="#2c3e50",
                )

                # Conversion arrow between stages
                if i > 0 and stages[i - 1]["total"] > 0:
                    conv = stage["total"] / stages[i - 1]["total"] * 100
                    arrow_y = current_y + stage_gap / 2
                    ax.annotate(
                        "",
                        xy=(0.5, arrow_y - stage_gap + 0.01),
                        xytext=(0.5, arrow_y - 0.01),
                        arrowprops=dict(arrowstyle="->", lw=3, color="#e74c3c"),
                    )
                    ax.text(
                        0.45,
                        arrow_y - stage_gap / 2,
                        f"{conv:.1f}%",
                        ha="center",
                        va="center",
                        fontsize=18,
                        fontweight="bold",
                        color="#e74c3c",
                        bbox=dict(
                            boxstyle="round,pad=0.3",
                            facecolor="white",
                            edgecolor="#e74c3c",
                            alpha=0.9,
                        ),
                    )
                current_y -= stage_height + stage_gap

            # Title and subtitle
            ax.text(
                0.5,
                0.98,
                "Account Eligibility & Debit Card Funnel",
                ha="center",
                va="top",
                fontsize=28,
                fontweight="bold",
                color="#1e3d59",
                transform=ax.transAxes,
            )
            ax.text(
                0.5,
                0.93,
                "All-Time (Historical)",
                ha="center",
                va="top",
                fontsize=20,
                style="italic",
                color="#7f8c8d",
                transform=ax.transAxes,
            )

            # Legend if business accounts
            if has_biz:
                legend_elements = [
                    patches.Patch(
                        facecolor="#808080", edgecolor="black", label="Personal (Lighter shade)"
                    ),
                    patches.Patch(
                        facecolor="#404040", edgecolor="black", label="Business (Darker shade)"
                    ),
                ]
                ax.legend(
                    handles=legend_elements,
                    loc="lower right",
                    fontsize=16,
                    frameon=True,
                    fancybox=True,
                )

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_funnel.png")
        finally:
            plt.close(fig)

        try:
            pd_dctr_funnel = (
                ctx["results"].get("dctr_4", {}).get("insights", {}).get("overall_dctr", 0) * 100
            )
            bd_dctr_funnel = (
                ctx["results"].get("dctr_5", {}).get("insights", {}).get("overall_dctr", 0) * 100
            )
            if has_biz and bd_dctr_funnel > 0:
                subtitle = (
                    f"{dctr_e:.1f}% DCTR eligible; Personal {pd_dctr_funnel:.1f}%"
                    f" vs Business {bd_dctr_funnel:.1f}% — {through:.1f}% end-to-end conversion"
                )
            else:
                subtitle = (
                    f"{dctr_e:.1f}% DCTR among eligible — {through:.1f}% of all accounts"
                    f" converted; {te:,} eligible from {ta:,} total"
                )
            if len(subtitle) > 120:
                subtitle = (
                    f"{dctr_e:.1f}% eligible DCTR — {through:.1f}% end-to-end conversion"
                )
        except Exception:
            subtitle = (
                f"{through:.1f}% of all accounts end up with debit cards"
                f" — {dctr_e:.1f}% DCTR among eligible"
            )
        insights_list = [
            f"Total accounts: {ta:,}",
            f"Open accounts: {to:,} ({to / ta * 100:.1f}% of total)" if ta else "Open: 0",
            f"Eligible accounts: {te:,} ({te / to * 100:.1f}% of open)" if to else "Eligible: 0",
            f"With debit card: {td:,} ({dctr_e:.1f}% DCTR)" if te else "With debit: 0",
            f"End-to-end conversion: {through:.1f}%",
        ]
        if has_biz:
            pd_dctr = (
                ctx["results"].get("dctr_4", {}).get("insights", {}).get("overall_dctr", 0) * 100
            )
            bd_dctr = (
                ctx["results"].get("dctr_5", {}).get("insights", {}).get("overall_dctr", 0) * 100
            )
            insights_list.append(f"Personal DCTR: {pd_dctr:.1f}% | Business DCTR: {bd_dctr:.1f}%")

        _slide(
            ctx,
            "A7.7 - Historical Funnel",
            {
                "title": "Historical Account & Debit Card Funnel",
                "subtitle": subtitle,
                "kpis": {"Through Rate": f"{through:.1f}%", "Eligible DCTR": f"{dctr_e:.1f}%"},
                "chart_path": cp,
                "layout_index": 9,
                "insights": insights_list,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Funnel chart: {e}")

    ctx["results"]["dctr_funnel"] = {"through_rate": through, "dctr_eligible": dctr_e}
    _report(ctx, f"   {ta:,} → {to:,} → {te:,} → {td:,} | Through: {through:.1f}%")
    return ctx


# =============================================================================
# COMBINED SLIDE: Open vs Eligible + Historical vs L12M (A7.1 + A7.3)
# =============================================================================


def run_dctr_combo_slide(ctx):
    """Build a single 3-bar chart: All Open → Eligible All-Time → Eligible L12M.

    Bars = population (account count), line = DCTR rate.
    """
    _report(ctx, "\n📊 DCTR — Overview Slide (A7.1+A7.3)")
    chart_dir = ctx["chart_dir"]

    d1 = ctx["results"].get("dctr_1", {}).get("insights", {})
    d2 = ctx["results"].get("dctr_2", {}).get("insights", {})
    d3 = ctx["results"].get("dctr_3", {}).get("insights", {})

    if not d1 or not d2:
        _report(ctx, "   ⚠️ Missing DCTR results — skipping overview")
        return ctx

    # Population counts
    open_total = d2.get("open_total", 0)
    elig_total = d1.get("total_accounts", 0)
    l12m_total = d3.get("total_accounts", 0)

    # DCTR rates (stored as 0-1 fractions)
    open_rate = d2.get("open_dctr", 0) * 100
    elig_rate = d1.get("overall_dctr", 0) * 100
    l12m_rate = d3.get("dctr", 0) * 100

    cats = ["All Open\nAccounts", "Eligible\n(All-Time)", "Eligible\n(Last 12 Mo.)"]
    counts = [open_total, elig_total, l12m_total]
    rates = [open_rate, elig_rate, l12m_rate]
    bar_colors = ["#70AD47", "#4472C4", "#FFC000"]

    try:
        fig, ax = plt.subplots(figsize=(14, 8))
        try:
            fig.patch.set_facecolor("white")
            x = np.arange(len(cats))

            # Bars = population count (primary axis)
            bars = ax.bar(
                x,
                counts,
                color=bar_colors,
                width=0.55,
                edgecolor="black",
                linewidth=2,
                alpha=0.85,
            )
            for bar, cnt, label in zip(bars, counts, cats):
                # Account count centered in bar
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    cnt / 2,
                    f"{cnt:,}",
                    ha="center",
                    va="center",
                    fontweight="bold",
                    fontsize=20,
                    color="white",
                )
                # Category label at base of column
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    -max(counts) * 0.06,
                    label.replace("\n", " "),
                    ha="center",
                    va="top",
                    fontweight="bold",
                    fontsize=16,
                    color="#333",
                )

            ax.set_ylabel("Number of Accounts", fontsize=20, fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels([""] * len(cats))  # hide default tick labels
            ax.tick_params(axis="y", labelsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{int(v):,}"))
            max_count = max(counts) if counts else 100
            ax.set_ylim(-max_count * 0.10, max_count * 1.15)

            # Rate markers -- independent horizontal line per bar
            ax2 = ax.twinx()
            for i, (r, c) in enumerate(zip(rates, bar_colors)):
                # Short horizontal line centered on bar
                ax2.plot(
                    [i - 0.2, i + 0.2],
                    [r, r],
                    color="black",
                    linewidth=4,
                    solid_capstyle="round",
                    zorder=5,
                )
                ax2.plot(
                    i,
                    r,
                    marker="o",
                    markersize=12,
                    markerfacecolor="white",
                    markeredgecolor="black",
                    markeredgewidth=3,
                    zorder=6,
                )
                ax2.text(
                    i,
                    r + 2.5,
                    f"{r:.1f}%",
                    ha="center",
                    fontweight="bold",
                    fontsize=20,
                    color="black",
                    bbox=dict(
                        boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.9
                    ),
                )
            ax2.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
            ax2.tick_params(axis="y", labelsize=16)
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:.0f}%"))
            min_rate = min(rates) if rates else 0
            max_rate = max(rates) if rates else 100
            ax2.set_ylim(max(0, min_rate - 15), max_rate + 15)

            ax.set_title(
                "DCTR Overview: Population & Take Rate",
                fontsize=24,
                fontweight="bold",
                pad=20,
            )
            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            ax.set_axisbelow(True)
            ax.grid(True, axis="y", alpha=0.2, linestyle="--")
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_overview.png")
        finally:
            plt.close(fig)
    except Exception as e:
        cp = None
        _report(ctx, f"   ⚠️ Overview chart: {e}")

    diff = elig_rate - open_rate
    comp = l12m_rate - elig_rate
    trend = "improving" if comp > 2 else "declining" if comp < -2 else "stable"

    try:
        overview_subtitle = (
            f"Eligible at {elig_rate:.1f}% ({diff:+.1f}pp vs all open {open_rate:.1f}%)"
            f" — L12M {trend} at {l12m_rate:.1f}% ({comp:+.1f}pp)"
        )
        if len(overview_subtitle) > 120:
            overview_subtitle = (
                f"Eligible {elig_rate:.1f}% ({diff:+.1f}pp vs open) — L12M {l12m_rate:.1f}%"
                f" ({comp:+.1f}pp, {trend})"
            )
    except Exception:
        overview_subtitle = (
            f"Eligible {diff:+.1f}pp vs All Open | Last 12 Mo. {trend} ({comp:+.1f}pp)"
        )

    _slide(
        ctx,
        "A7 - DCTR Comparison",
        {
            "title": "DCTR Overview: Population & Take Rate",
            "subtitle": overview_subtitle,
            "chart_path": cp,
            "layout_index": 9,
            "slide_type": "screenshot",
            "insights": [
                f"All Open: {open_total:,} accounts, {open_rate:.1f}% DCTR",
                f"Eligible: {elig_total:,} accounts, {elig_rate:.1f}% DCTR ({diff:+.1f}pp)",
                f"Last 12 Mo: {l12m_total:,} accounts, {l12m_rate:.1f}% DCTR ({comp:+.1f}pp)",
            ],
        },
    )
    _report(
        ctx,
        f"   Overview: Open {open_rate:.1f}% → Eligible {elig_rate:.1f}% → L12M {l12m_rate:.1f}%",
    )
    return ctx


# =============================================================================
# SEGMENT TRENDS: Personal/Business × Historical/L12M (A7.4)
# =============================================================================


def run_dctr_segment_trends(ctx):
    """A7.4: Grouped bar chart — Personal/Business × Historical/L12M DCTR."""
    _report(ctx, "\n📊 DCTR — Segment Trends (A7.4)")
    chart_dir = ctx["chart_dir"]

    # Gather rates from earlier results
    p_ins = ctx["results"].get("dctr_4", {}).get("insights", {})
    b_ins = ctx["results"].get("dctr_5", {}).get("insights", {})
    p6_ins = ctx["results"].get("dctr_6", {}).get("insights", {})
    b7_ins = ctx["results"].get("dctr_7", {}).get("insights", {})

    p_hist = p_ins.get("overall_dctr", 0) * 100
    p_l12m = p6_ins.get("dctr", 0) * 100
    p_trend = p_l12m - p_hist
    has_biz = b_ins.get("total_accounts", 0) > 0
    b_hist = b_ins.get("overall_dctr", 0) * 100
    b_l12m = b7_ins.get("dctr", 0) * 100
    b_trend = b_l12m - b_hist

    # Build summary table
    rows = [
        {
            "Segment": "Personal",
            "Historical DCTR %": p_hist,
            "L12M DCTR %": p_l12m,
            "Change pp": p_trend,
            "Hist Accounts": p_ins.get("total_accounts", 0),
            "L12M Accounts": p6_ins.get("total_accounts", 0),
        }
    ]
    if has_biz:
        rows.append(
            {
                "Segment": "Business",
                "Historical DCTR %": b_hist,
                "L12M DCTR %": b_l12m,
                "Change pp": b_trend,
                "Hist Accounts": b_ins.get("total_accounts", 0),
                "L12M Accounts": b7_ins.get("total_accounts", 0),
            }
        )
    df = pd.DataFrame(rows)
    _save(
        ctx,
        df,
        "DCTR-SegmentTrends",
        "DCTR Segment Trends",
        {
            "Personal Trend": f"{p_trend:+.1f}pp",
            "Business Trend": f"{b_trend:+.1f}pp" if has_biz else "N/A",
        },
    )

    # Chart A7.4: Grouped bar — matching notebook format
    try:
        fig, ax = plt.subplots(figsize=(12, 10))
        try:
            if has_biz:
                cats = [
                    "Personal\nAll-Time",
                    "Personal\nLast 12 Mo.",
                    "Business\nAll-Time",
                    "Business\nLast 12 Mo.",
                ]
                vals = [p_hist, p_l12m, b_hist, b_l12m]
                colors = ["#4472C4", "#5B9BD5", "#ED7D31", "#F4B183"]
            else:
                cats = ["Personal\nAll-Time", "Personal\nLast 12 Mo."]
                vals = [p_hist, p_l12m]
                colors = ["#4472C4", "#5B9BD5"]

            x_pos = np.arange(len(cats))
            bars = ax.bar(
                x_pos, vals, color=colors, edgecolor="black", linewidth=2, alpha=0.9, width=0.6
            )
            for i, (bar, v) in enumerate(zip(bars, vals)):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    v + 1,
                    f"{v:.1f}%",
                    ha="center",
                    fontweight="bold",
                    fontsize=22,
                )
                ct = [
                    p_ins.get("total_accounts", 0),
                    p6_ins.get("total_accounts", 0),
                    b_ins.get("total_accounts", 0),
                    b7_ins.get("total_accounts", 0),
                ]
                if i < len(ct) and ct[i] > 0 and v > 10:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        v / 2,
                        f"{ct[i]:,}\naccts",
                        ha="center",
                        fontsize=16,
                        fontweight="bold",
                        color="white",
                    )
            ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
            ax.set_title(
                "Eligible Account DCTR by Segment",
                fontsize=24,
                fontweight="bold",
                pad=20,
            )
            ax.set_xticks(x_pos)
            ax.set_xticklabels(cats, fontsize=20)
            ax.tick_params(axis="y", labelsize=20)
            ax.set_ylim(0, max(vals) * 1.2 if vals else 100)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.grid(True, axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)

            # Divider between Personal and Business
            if has_biz:
                ax.axvline(x=1.5, color="gray", linestyle="--", linewidth=2, alpha=0.5)

            # Trend annotations
            mid_p = 0.5
            ax.annotate(
                f"{p_trend:+.1f}pp",
                xy=(mid_p, max(p_hist, p_l12m) + 3),
                fontsize=20,
                fontweight="bold",
                ha="center",
                color="green" if p_trend > 0 else "red" if p_trend < 0 else "gray",
            )
            if has_biz:
                mid_b = 2.5
                ax.annotate(
                    f"{b_trend:+.1f}pp",
                    xy=(mid_b, max(b_hist, b_l12m) + 3),
                    fontsize=20,
                    fontweight="bold",
                    ha="center",
                    color="green" if b_trend > 0 else "red" if b_trend < 0 else "gray",
                )
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_segment_trends.png")
        finally:
            plt.close(fig)

        try:
            seg_dir = "up" if p_trend > 0 else "down" if p_trend < 0 else "flat"
            if has_biz:
                subtitle = (
                    f"Personal {p_hist:.1f}% → {p_l12m:.1f}% ({p_trend:+.1f}pp);"
                    f" Business {b_hist:.1f}% → {b_l12m:.1f}% ({b_trend:+.1f}pp) TTM"
                )
                if len(subtitle) > 120:
                    subtitle = (
                        f"Personal {p_trend:+.1f}pp ({p_l12m:.1f}% TTM);"
                        f" Business {b_trend:+.1f}pp ({b_l12m:.1f}% TTM)"
                    )
            else:
                subtitle = (
                    f"Personal trending {seg_dir}: {p_hist:.1f}% all-time"
                    f" → {p_l12m:.1f}% TTM ({p_trend:+.1f}pp)"
                )
        except Exception:
            subtitle = f"Personal {p_trend:+.1f}pp"
            if has_biz:
                subtitle += f" | Business {b_trend:+.1f}pp"
            subtitle += " — Trailing twelve months vs historical"
        _slide(
            ctx,
            "A7.4 - Segment Trends",
            {
                "title": "DCTR Segment Trends",
                "subtitle": subtitle,
                "chart_path": cp,
                "layout_index": 9,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Segment trends chart: {e}")

    ctx["results"]["dctr_segment_trends"] = {
        "personal_trend": p_trend,
        "business_trend": b_trend,
        "has_business": has_biz,
    }
    _report(ctx, f"   Personal: {p_hist:.1f}% → {p_l12m:.1f}% ({p_trend:+.1f}pp)")
    return ctx


# =============================================================================
# DECADE TREND: Line chart with P/B overlay (A7.5)
# =============================================================================


def run_dctr_decade_trend(ctx):
    """A7.5: DCTR trend by decade with Personal/Business overlay."""
    _report(ctx, "\n📈 DCTR — Decade Trend (A7.5)")
    chart_dir = ctx["chart_dir"]

    d1 = ctx["results"].get("dctr_1", {}).get("decade", pd.DataFrame())
    d4 = ctx["results"].get("dctr_4", {}).get("decade", pd.DataFrame())
    d5 = ctx["results"].get("dctr_5", {}).get("decade", pd.DataFrame())

    if d1.empty:
        _report(ctx, "   ⚠️ No decade data")
        return ctx

    _save(ctx, d1, "DCTR-DecadeTrend", "DCTR by Decade")

    try:
        fig = plt.figure(figsize=(16, 8))
        try:
            ax = plt.gca()
            ax2 = ax.twinx()
            decades = d1["Decade"].values
            overall = d1["DCTR %"].values * 100
            x = np.arange(len(decades))

            # Volume bars on secondary axis (notebook: alpha=0.2, gray, no edge)
            total_vol = d1["Total Accounts"].values
            bars = ax2.bar(x, total_vol, alpha=0.2, color="gray", edgecolor="none", width=0.8)
            ax2.set_ylabel("Account Volume", fontsize=24, color="gray")
            max_vol = max(total_vol) if len(total_vol) > 0 else 100
            ax2.set_ylim(0, max_vol * 2)
            ax2.tick_params(axis="y", colors="gray", labelsize=24)

            # Volume labels at base of bars (notebook style)
            for bar, vol in zip(bars, total_vol):
                if vol > 0:
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        vol * 0.02,
                        f"{int(vol):,}",
                        ha="center",
                        va="bottom",
                        fontsize=24,
                        color="black",
                        alpha=0.8,
                    )

            # Overall DCTR line (notebook: black, dashed, markersize=18)
            ax.plot(
                x,
                overall,
                color="black",
                linewidth=3,
                linestyle="--",
                marker="o",
                markersize=18,
                label="Overall",
                zorder=2,
            )

            # Personal overlay (notebook: blue, lw=4, ms=12)
            has_biz = False
            if not d4.empty:
                p_merged = d4.set_index("Decade").reindex(decades)
                p_vals = p_merged["DCTR %"].values * 100
                valid_mask = ~np.isnan(p_vals)
                if valid_mask.any():
                    ax.plot(
                        x[valid_mask],
                        p_vals[valid_mask],
                        color="#4472C4",
                        linewidth=4,
                        marker="o",
                        markersize=12,
                        label="Personal",
                        zorder=3,
                    )
                    for i, v in zip(x[valid_mask], p_vals[valid_mask]):
                        offset = 2 if not (not d5.empty and d5["Total Accounts"].sum() > 0) else 2
                        ax.text(
                            i,
                            v + offset,
                            f"{v:.0f}%",
                            ha="center",
                            va="bottom",
                            fontsize=24,
                            fontweight="bold",
                            color="#4472C4",
                        )

            # Business overlay (notebook: orange, lw=4, square markers)
            if not d5.empty and d5["Total Accounts"].sum() > 0:
                has_biz = True
                b_merged = d5.set_index("Decade").reindex(decades)
                b_vals = b_merged["DCTR %"].values * 100
                valid_mask = ~np.isnan(b_vals)
                if valid_mask.any():
                    ax.plot(
                        x[valid_mask],
                        b_vals[valid_mask],
                        color="#ED7D31",
                        linewidth=4,
                        marker="s",
                        markersize=12,
                        label="Business",
                        zorder=3,
                    )
                    for i, v in zip(x[valid_mask], b_vals[valid_mask]):
                        ax.text(
                            i,
                            v - 3,
                            f"{v:.0f}%",
                            ha="center",
                            va="top",
                            fontsize=24,
                            fontweight="bold",
                            color="#ED7D31",
                        )

            # Axis formatting (notebook: fontsize=24 everywhere)
            ax.set_xticks(x)
            ax.set_xticklabels(decades, fontsize=24, rotation=45 if len(decades) > 8 else 0)
            ax.set_xlabel("Decade", fontsize=24, fontweight="bold")
            ax.set_ylabel("DCTR (%)", fontsize=24, fontweight="bold")
            ax.set_title(
                "Historical DCTR Trend by Decade - Eligible Accounts Only",
                fontsize=24,
                fontweight="bold",
                pad=20,
            )
            ax.set_ylim(0, 110)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x)}%"))
            ax.tick_params(axis="y", labelsize=24)

            # Legend (notebook style)
            legend_items = 1
            if not d4.empty:
                legend_items += 1
            if has_biz:
                legend_items += 1
            ax.legend(
                loc="upper center",
                bbox_to_anchor=(0.5, -0.12),
                ncol=legend_items,
                fontsize=18,
                frameon=True,
            )

            ax.grid(True, axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_decade_trend.png")
        finally:
            plt.close(fig)

        change = overall[-1] - overall[0] if len(overall) >= 2 else 0
        trend = "improving" if change > 0 else "declining" if change < 0 else "stable"
        try:
            first_decade = str(decades[0]) if len(decades) else "earliest"
            last_decade = str(decades[-1]) if len(decades) else "latest"
            peak_idx = int(np.argmax(overall))
            peak_decade = str(decades[peak_idx])
            peak_val = overall[peak_idx]
            decade_subtitle = (
                f"DCTR {trend} from {overall[0]:.0f}% ({first_decade}) to"
                f" {overall[-1]:.0f}% ({last_decade}) ({change:+.1f}pp)"
                f" — peak {peak_val:.0f}% in {peak_decade}"
            )
            if len(decade_subtitle) > 120:
                decade_subtitle = (
                    f"{trend.capitalize()}: {overall[0]:.0f}% ({first_decade})"
                    f" → {overall[-1]:.0f}% ({last_decade}) — {change:+.1f}pp"
                )
        except Exception:
            decade_subtitle = (
                f"Overall {trend}: {overall[0]:.0f}% → {overall[-1]:.0f}%"
                f" ({change:+.1f}pp) across {len(decades)} decades"
            )
        _slide(
            ctx,
            "A7.5 - Decade Trend",
            {
                "title": "Historical DCTR Trend by Decade",
                "subtitle": decade_subtitle,
                "chart_path": cp,
                "layout_index": 9,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Decade trend chart: {e}")

    ctx["results"]["dctr_decade_trend"] = {"decades": len(d1)}
    _report(ctx, f"   {len(d1)} decades plotted")
    return ctx


# =============================================================================
# L12M TREND: Monthly DCTR line chart (A7.6a)
# =============================================================================


def run_dctr_l12m_trend(ctx):
    """A7.6a: L12M monthly DCTR trend line chart with P/B overlay."""
    _report(ctx, "\n📈 DCTR — L12M Monthly Trend (A7.6a)")
    chart_dir = ctx["chart_dir"]
    l12m_months = ctx["last_12_months"]

    # Get monthly data from L12M subsets
    ed = ctx["eligible_last_12m"]
    ep = ctx["eligible_personal_last_12m"]
    eb = ctx["eligible_business_last_12m"]

    if ed is None or ed.empty:
        _report(ctx, "   ⚠️ No L12M data")
        return ctx

    def _monthly_rates(dataset, months):
        dc = dataset.copy()
        dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
        dc["Month_Year"] = dc["Date Opened"].dt.strftime("%b%y")
        rates = []
        for m in months:
            md = dc[dc["Month_Year"] == m]
            t, w, d = _dctr(md)
            rates.append(d * 100 if t > 0 else np.nan)
        return rates

    overall_rates = _monthly_rates(ed, l12m_months)
    personal_rates = (
        _monthly_rates(ep, l12m_months)
        if ep is not None and not ep.empty
        else [np.nan] * len(l12m_months)
    )
    has_biz = eb is not None and not eb.empty and len(eb) > 0
    business_rates = _monthly_rates(eb, l12m_months) if has_biz else [np.nan] * len(l12m_months)

    # Build data table
    trend_df = pd.DataFrame(
        {
            "Month": l12m_months,
            "Overall DCTR %": overall_rates,
            "Personal DCTR %": personal_rates,
            "Business DCTR %": business_rates,
        }
    )
    _save(ctx, trend_df, "DCTR-L12M-Trend", "L12M Monthly DCTR Trend")

    try:
        fig = plt.figure(figsize=(14, 10))
        try:
            ax = plt.gca()
            ax2 = ax.twinx()
            x = np.arange(len(l12m_months))

            # Volume bars on secondary axis (notebook style)
            ed_copy = ed.copy()
            ed_copy["Date Opened"] = pd.to_datetime(ed_copy["Date Opened"], errors="coerce")
            ed_copy["Month_Year"] = ed_copy["Date Opened"].dt.strftime("%b%y")
            total_volume = [len(ed_copy[ed_copy["Month_Year"] == m]) for m in l12m_months]
            bars = ax2.bar(
                x,
                total_volume,
                alpha=0.25,
                color="gray",
                edgecolor="darkgray",
                linewidth=1,
                width=0.8,
            )
            # Volume labels with white background (notebook style)
            for bar, vol in zip(bars, total_volume):
                if vol > 0:
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        vol * 0.05,
                        f"{int(vol):,}",
                        ha="center",
                        va="bottom",
                        fontsize=18,
                        fontweight="bold",
                        color="black",
                        alpha=0.9,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
                    )
            max_vol = max(total_volume) if total_volume else 100
            ax2.set_ylim(0, max_vol * 2)
            ax2.set_ylabel("Number of Accounts", fontsize=24, color="gray", labelpad=15)
            ax2.tick_params(axis="y", labelsize=20, colors="gray")

            # Overall DCTR line (notebook: black, dashed, lw=4, ms=12)
            ov = np.array(overall_rates)
            mask = ~np.isnan(ov)
            if mask.any():
                ax.plot(
                    x[mask],
                    ov[mask],
                    color="black",
                    linewidth=4,
                    linestyle="--",
                    marker="o",
                    markersize=12,
                    label="Overall",
                    zorder=2,
                )
                # Data labels — only first, last, and every 3rd
                for idx, (i, v) in enumerate(zip(x[mask], ov[mask])):
                    if idx == 0 or idx == mask.sum() - 1 or idx % 3 == 0:
                        ax.text(
                            i,
                            v + 1.5,
                            f"{v:.0f}%",
                            ha="center",
                            fontsize=24,
                            fontweight="bold",
                            color="black",
                        )

            # Personal DCTR line (notebook: blue, lw=5, ms=14)
            pr = np.array(personal_rates)
            pmask = ~np.isnan(pr)
            if pmask.any():
                ax.plot(
                    x[pmask],
                    pr[pmask],
                    color="#4472C4",
                    linewidth=5,
                    marker="o",
                    markersize=14,
                    label="Personal",
                    zorder=3,
                )

            # Business DCTR line (notebook: orange)
            if has_biz:
                br = np.array(business_rates)
                bmask = ~np.isnan(br)
                if bmask.any():
                    ax.plot(
                        x[bmask],
                        br[bmask],
                        color="#ED7D31",
                        linewidth=4,
                        marker="s",
                        markersize=12,
                        label="Business",
                        zorder=3,
                    )

            # Axis formatting (notebook: fontsize 24-32)
            ax.set_xticks(x)
            ax.set_xticklabels(l12m_months, rotation=45, ha="right", fontsize=22)
            ax.set_xlabel("Month", fontsize=28, fontweight="bold", labelpad=15)
            ax.set_ylabel("DCTR (%)", fontsize=28, fontweight="bold", labelpad=15)
            ax.set_title(
                "Trailing Twelve Months DCTR Trend (Eligible Accounts)",
                fontsize=32,
                fontweight="bold",
                pad=25,
            )
            ax.tick_params(axis="y", labelsize=24)
            ax.set_ylim(50, 100)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x)}%"))
            ax.legend(
                loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=18, frameon=True
            )
            ax.grid(True, axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax2.spines["top"].set_visible(False)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_l12m_trend.png")
        finally:
            plt.close(fig)

        start_v = next((v for v in overall_rates if not np.isnan(v)), 0)
        end_v = next((v for v in reversed(overall_rates) if not np.isnan(v)), 0)
        change = end_v - start_v
        trend = "improving" if change > 2 else "declining" if change < -2 else "stable"
        try:
            first_month = l12m_months[0] if l12m_months else "start"
            last_month = l12m_months[-1] if l12m_months else "end"
            p_end = next((v for v in reversed(personal_rates) if not np.isnan(v)), None)
            b_end = next((v for v in reversed(business_rates) if not np.isnan(v)), None)
            if has_biz and p_end is not None and b_end is not None:
                l12m_trend_subtitle = (
                    f"DCTR {trend} {start_v:.0f}% → {end_v:.0f}% ({change:+.1f}pp,"
                    f" {first_month}–{last_month}); Personal {p_end:.0f}% vs Business {b_end:.0f}%"
                )
            else:
                l12m_trend_subtitle = (
                    f"DCTR {trend} from {start_v:.0f}% ({first_month})"
                    f" to {end_v:.0f}% ({last_month}) — {change:+.1f}pp over trailing twelve months"
                )
            if len(l12m_trend_subtitle) > 120:
                l12m_trend_subtitle = (
                    f"TTM DCTR {trend}: {start_v:.0f}% → {end_v:.0f}% ({change:+.1f}pp)"
                )
        except Exception:
            l12m_trend_subtitle = (
                f"DCTR {trend} from {start_v:.0f}% to {end_v:.0f}%"
                f" ({change:+.1f}pp) over trailing twelve months"
            )
        _slide(
            ctx,
            "A7.6a - Last 12 Months DCTR Trend",
            {
                "title": "Trailing Twelve Months DCTR Trend",
                "subtitle": l12m_trend_subtitle,
                "chart_path": cp,
                "layout_index": 9,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ L12M trend chart: {e}")

    ctx["results"]["dctr_l12m_trend"] = {"trend_df": trend_df}
    _report(ctx, f"   {len(l12m_months)} months plotted")
    return ctx


# =============================================================================
# L12M FUNNEL: Last 12 Months Funnel with P/B Split (A7.8)
# =============================================================================


def run_dctr_l12m_funnel(ctx):
    """A7.8: L12M proportional funnel chart with Personal/Business split."""
    _report(ctx, "\n🎯 DCTR — L12M Funnel (A7.8)")
    chart_dir = ctx["chart_dir"]
    data = ctx["data"].copy()
    sd, ed_date = ctx["start_date"], ctx["end_date"]

    data["Date Opened"] = pd.to_datetime(data["Date Opened"], errors="coerce")
    l12m_all = data[(data["Date Opened"] >= sd) & (data["Date Opened"] <= ed_date)]
    l12m_open = ctx["open_last_12m"] if ctx.get("open_last_12m") is not None else pd.DataFrame()
    l12m_elig = (
        ctx["eligible_last_12m"] if ctx.get("eligible_last_12m") is not None else pd.DataFrame()
    )
    l12m_debit = l12m_elig[l12m_elig["Debit?"] == "Yes"] if not l12m_elig.empty else pd.DataFrame()

    ta = len(l12m_all)
    to = len(l12m_open)
    te = len(l12m_elig)
    td = len(l12m_debit)
    through = td / ta * 100 if ta else 0
    dctr_e = td / te * 100 if te else 0

    # P/B splits
    has_biz = (
        "Business?" in l12m_elig.columns and len(l12m_elig[l12m_elig["Business?"] == "Yes"]) > 0
    )
    if has_biz:
        ep = l12m_elig[l12m_elig["Business?"] == "No"]
        eb = l12m_elig[l12m_elig["Business?"] == "Yes"]
        pd_dctr = len(ep[ep["Debit?"] == "Yes"]) / len(ep) * 100 if len(ep) else 0
        bd_dctr = len(eb[eb["Debit?"] == "Yes"]) / len(eb) * 100 if len(eb) else 0
    else:
        pd_dctr = dctr_e
        bd_dctr = 0

    funnel_df = pd.DataFrame(
        [
            {"Stage": "Total TTM Accounts", "Count": ta, "Pct of Total": 100},
            {"Stage": "Open Accounts", "Count": to, "Pct of Total": to / ta * 100 if ta else 0},
            {"Stage": "Eligible Accounts", "Count": te, "Pct of Total": te / ta * 100 if ta else 0},
            {"Stage": "With Debit Card", "Count": td, "Pct of Total": through},
        ]
    )
    _save(
        ctx,
        funnel_df,
        "DCTR-L12M-Funnel",
        "L12M Account Funnel",
        {
            "Through Rate": f"{through:.1f}%",
            "DCTR": f"{dctr_e:.1f}%",
            "Period": f"{sd.strftime('%b %Y')} - {ed_date.strftime('%b %Y')}",
        },
    )

    try:
        import matplotlib.colors as mcolors
        import matplotlib.patches as patches

        fig, ax = plt.subplots(figsize=(10, 12))
        try:
            fig.patch.set_facecolor("white")
            ax.set_facecolor("#f8f9fa")

            # Build P/B split counts
            tp_a = (
                len(l12m_all[l12m_all["Business?"] == "No"])
                if "Business?" in l12m_all.columns
                else ta
            )
            tb_a = ta - tp_a
            op_a = (
                len(l12m_open[l12m_open["Business?"] == "No"])
                if not l12m_open.empty and "Business?" in l12m_open.columns
                else to
            )
            ob_a = to - op_a
            ep_a = (
                len(l12m_elig[l12m_elig["Business?"] == "No"])
                if not l12m_elig.empty and "Business?" in l12m_elig.columns
                else te
            )
            eb_a = te - ep_a
            dp_a = (
                len(l12m_debit[l12m_debit["Business?"] == "No"])
                if not l12m_debit.empty and "Business?" in l12m_debit.columns
                else td
            )
            db_a = td - dp_a

            stages = [
                {
                    "name": "Total New\nAccounts",
                    "total": ta,
                    "personal": tp_a,
                    "business": tb_a,
                    "color": "#1f77b4",
                },
                {
                    "name": "Open\nAccounts",
                    "total": to,
                    "personal": op_a,
                    "business": ob_a,
                    "color": "#2c7fb8",
                },
                {
                    "name": "Eligible\nAccounts",
                    "total": te,
                    "personal": ep_a,
                    "business": eb_a,
                    "color": "#ff7f0e",
                },
                {
                    "name": "Eligible With\nDebit Card",
                    "total": td,
                    "personal": dp_a,
                    "business": db_a,
                    "color": "#41b6c4",
                },
            ]

            max_width = 0.8
            stage_height = 0.15
            y_start = 0.85
            stage_gap = 0.02
            current_y = y_start

            for i, stage in enumerate(stages):
                width = (
                    max_width * (stage["total"] / stages[0]["total"])
                    if stages[0]["total"] > 0
                    else 0.1
                )

                if has_biz and stage["total"] > 0:
                    p_ratio = stage["personal"] / stage["total"]
                    p_width = width * p_ratio
                    b_width = width * (1 - p_ratio)
                    # Personal (lighter)
                    rect_p = patches.FancyBboxPatch(
                        (0.5 - width / 2, current_y - stage_height),
                        p_width,
                        stage_height,
                        boxstyle="round,pad=0.01",
                        facecolor=stage["color"],
                        edgecolor="white",
                        linewidth=2,
                        alpha=0.9,
                    )
                    ax.add_patch(rect_p)
                    # Business (darker)
                    rgb = mcolors.hex2color(stage["color"])
                    darker = mcolors.rgb2hex(tuple([c * 0.7 for c in rgb]))
                    rect_b = patches.FancyBboxPatch(
                        (0.5 - width / 2 + p_width, current_y - stage_height),
                        b_width,
                        stage_height,
                        boxstyle="round,pad=0.01",
                        facecolor=darker,
                        edgecolor="white",
                        linewidth=2,
                        alpha=0.9,
                    )
                    ax.add_patch(rect_b)
                    if p_width > 0.05:
                        ax.text(
                            0.5 - width / 2 + p_width / 2,
                            current_y - stage_height / 2,
                            f"{stage['personal']:,}",
                            ha="center",
                            va="center",
                            fontsize=20,
                            color="white",
                            fontweight="bold",
                        )
                    if b_width > 0.05:
                        ax.text(
                            0.5 - width / 2 + p_width + b_width / 2,
                            current_y - stage_height / 2,
                            f"{stage['business']:,}",
                            ha="center",
                            va="center",
                            fontsize=20,
                            color="white",
                            fontweight="bold",
                        )
                    ax.text(
                        0.5 + width / 2 + 0.05,
                        current_y - stage_height / 2,
                        f"Total\n{stage['total']:,}",
                        ha="left",
                        va="center",
                        fontsize=18,
                        fontweight="bold",
                        color="black",
                        bbox=dict(
                            boxstyle="round,pad=0.4",
                            facecolor="white",
                            edgecolor="black",
                            alpha=0.9,
                        ),
                    )
                else:
                    rect = patches.FancyBboxPatch(
                        (0.5 - width / 2, current_y - stage_height),
                        width,
                        stage_height,
                        boxstyle="round,pad=0.01",
                        facecolor=stage["color"],
                        edgecolor="white",
                        linewidth=3,
                        alpha=0.9,
                    )
                    ax.add_patch(rect)
                    ax.text(
                        0.5,
                        current_y - stage_height / 2,
                        f"{stage['total']:,}",
                        ha="center",
                        va="center",
                        fontsize=28,
                        fontweight="bold",
                        color="white",
                        zorder=10,
                    )

                ax.text(
                    0.5 - width / 2 - 0.05,
                    current_y - stage_height / 2,
                    stage["name"],
                    ha="right",
                    va="center",
                    fontsize=20,
                    fontweight="600",
                    color="#2c3e50",
                )

                if i > 0 and stages[i - 1]["total"] > 0:
                    conv = stage["total"] / stages[i - 1]["total"] * 100
                    arrow_y = current_y + stage_gap / 2
                    ax.annotate(
                        "",
                        xy=(0.5, arrow_y - stage_gap + 0.01),
                        xytext=(0.5, arrow_y - 0.01),
                        arrowprops=dict(arrowstyle="->", lw=3, color="#e74c3c"),
                    )
                    ax.text(
                        0.45,
                        arrow_y - stage_gap / 2,
                        f"{conv:.1f}%",
                        ha="center",
                        va="center",
                        fontsize=18,
                        fontweight="bold",
                        color="#e74c3c",
                        bbox=dict(
                            boxstyle="round,pad=0.3",
                            facecolor="white",
                            edgecolor="#e74c3c",
                            alpha=0.9,
                        ),
                    )
                current_y -= stage_height + stage_gap

            # Title and subtitle
            ax.text(
                0.5,
                0.98,
                "Account Eligibility & Debit Card Funnel",
                ha="center",
                va="top",
                fontsize=28,
                fontweight="bold",
                color="#1e3d59",
                transform=ax.transAxes,
            )
            ax.text(
                0.5,
                0.93,
                f"{sd.strftime('%B %Y')} - {ed_date.strftime('%B %Y')}",
                ha="center",
                va="top",
                fontsize=20,
                style="italic",
                color="#7f8c8d",
                transform=ax.transAxes,
            )

            if has_biz:
                legend_elements = [
                    patches.Patch(
                        facecolor="#808080", edgecolor="black", label="Personal (Lighter shade)"
                    ),
                    patches.Patch(
                        facecolor="#404040", edgecolor="black", label="Business (Darker shade)"
                    ),
                ]
                ax.legend(
                    handles=legend_elements,
                    loc="lower right",
                    fontsize=16,
                    frameon=True,
                    fancybox=True,
                )

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_l12m_funnel.png")
        finally:
            plt.close(fig)

        try:
            if has_biz and bd_dctr > 0:
                l12m_funnel_subtitle = (
                    f"{dctr_e:.1f}% TTM eligible DCTR — Personal {pd_dctr:.1f}% vs"
                    f" Business {bd_dctr:.1f}%; {through:.1f}% end-to-end ({td:,}/{ta:,})"
                )
            else:
                l12m_funnel_subtitle = (
                    f"{dctr_e:.1f}% DCTR among {te:,} eligible accounts"
                    f" — {through:.1f}% end-to-end conversion ({td:,} with debit of {ta:,} total)"
                )
            if len(l12m_funnel_subtitle) > 120:
                l12m_funnel_subtitle = (
                    f"{dctr_e:.1f}% eligible DCTR — {through:.1f}% end-to-end; {td:,} of {ta:,} total"
                )
        except Exception:
            l12m_funnel_subtitle = (
                f"{through:.1f}% conversion — {dctr_e:.1f}% DCTR among eligible"
            )
        _slide(
            ctx,
            "A7.8 - L12M Funnel",
            {
                "title": "Trailing Twelve Months Account & Debit Card Funnel",
                "subtitle": l12m_funnel_subtitle,
                "chart_path": cp,
                "layout_index": 9,
                "insights": [
                    f"TTM accounts: {ta:,}",
                    f"Eligible: {te:,}",
                    f"With debit: {td:,}",
                    f"DCTR: {dctr_e:.1f}%",
                ],
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ L12M funnel chart: {e}")

    ctx["results"]["dctr_l12m_funnel"] = {"through": through, "dctr": dctr_e}
    _report(ctx, f"   {ta:,} → {to:,} → {te:,} → {td:,} | Through: {through:.1f}%")
    return ctx


# =============================================================================
# BRANCH TREND: Historical vs L12M Change Tracking (A7.10a)
# =============================================================================


def run_dctr_branch_trend(ctx):
    """A7.10a: Dedicated branch historical vs L12M with change tracking."""
    _report(ctx, "\n🏢 DCTR — Branch Trend (A7.10a)")
    chart_dir = ctx["chart_dir"]
    bm = ctx["config"].get("BranchMapping", {})

    # Get branch data from eligible sets
    hist_df, hist_ins = _branch_dctr(ctx["eligible_data"], bm)
    l12m_df, l12m_ins = _branch_dctr(ctx["eligible_last_12m"], bm)

    if hist_df.empty or l12m_df.empty:
        _report(ctx, "   ⚠️ Insufficient branch data")
        return ctx

    # Merge for comparison
    hd = hist_df[hist_df["Branch"] != "TOTAL"][["Branch", "DCTR %", "Total Accounts"]].rename(
        columns={"DCTR %": "Historical DCTR", "Total Accounts": "Hist Volume"}
    )
    ld = l12m_df[l12m_df["Branch"] != "TOTAL"][["Branch", "DCTR %", "Total Accounts"]].rename(
        columns={"DCTR %": "L12M DCTR", "Total Accounts": "L12M Volume"}
    )
    merged = hd.merge(ld, on="Branch", how="outer").fillna(0)
    merged["Change pp"] = (merged["L12M DCTR"] - merged["Historical DCTR"]) * 100
    merged["Historical DCTR %"] = merged["Historical DCTR"] * 100
    merged["L12M DCTR %"] = merged["L12M DCTR"] * 100
    merged = merged.sort_values("Historical DCTR", ascending=False)

    # Export table
    export_df = merged[
        ["Branch", "Historical DCTR %", "L12M DCTR %", "Change pp", "Hist Volume", "L12M Volume"]
    ].copy()
    improving = (merged["Change pp"] > 0).sum()
    avg_change = merged["Change pp"].mean()

    _save(
        ctx,
        export_df,
        "DCTR-BranchTrend",
        "Branch DCTR: Historical vs L12M",
        {"Improving": f"{improving} of {len(merged)}", "Avg Change": f"{avg_change:+.1f}pp"},
    )

    # Chart: Vertical bars (volume) + DCTR lines — matching Reg E A8.4b format
    try:
        n = len(merged)
        fig, ax1 = plt.subplots(figsize=(28, 14))
        x_pos = np.arange(n)

        # L12M volume bars
        bars = ax1.bar(
            x_pos,
            merged["L12M Volume"],
            width=0.6,
            color="#D9D9D9",
            edgecolor="black",
            linewidth=2,
        )
        ax1.set_ylabel("Eligible Accounts (TTM)", fontsize=28, fontweight="bold")
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(
            merged["Branch"].values,
            rotation=45,
            ha="right",
            fontsize=24,
            fontweight="bold",
        )
        ax1.tick_params(axis="y", labelsize=22)
        ax1.grid(False)
        for spine in ax1.spines.values():
            spine.set_visible(False)

        # Volume labels
        max_vol = merged["L12M Volume"].max() if n > 0 else 1
        for i, v in enumerate(merged["L12M Volume"]):
            ax1.text(
                i,
                v + max_vol * 0.015,
                f"{int(v):,}",
                ha="center",
                va="bottom",
                fontsize=22,
                fontweight="bold",
                color="#333",
            )

        # DCTR lines on secondary axis
        ax2 = ax1.twinx()
        hist_line = ax2.plot(
            x_pos,
            merged["Historical DCTR %"],
            "o-",
            color="#BDC3C7",
            lw=3,
            ms=10,
            label="Historical DCTR",
        )
        l12m_line = ax2.plot(
            x_pos,
            merged["L12M DCTR %"],
            "o-",
            color="#2E86AB",
            lw=4,
            ms=14,
            label="TTM DCTR",
            zorder=5,
        )

        # Data labels on lines
        for i, v in enumerate(merged["L12M DCTR %"]):
            if v > 0:
                ax2.text(
                    i,
                    v + 2,
                    f"{v:.0f}%",
                    ha="center",
                    fontsize=22,
                    fontweight="bold",
                    color="#2E86AB",
                )
        for i, v in enumerate(merged["Historical DCTR %"]):
            if v > 0:
                ax2.text(
                    i,
                    v - 3,
                    f"{v:.0f}%",
                    ha="center",
                    va="top",
                    fontsize=18,
                    color="#95A5A6",
                )

        # Weighted average lines
        hist_wa = (
            (merged["Historical DCTR"] * merged["Hist Volume"]).sum()
            / merged["Hist Volume"].sum()
            * 100
            if merged["Hist Volume"].sum() > 0
            else 0
        )
        l12m_wa = (
            (merged["L12M DCTR"] * merged["L12M Volume"]).sum() / merged["L12M Volume"].sum() * 100
            if merged["L12M Volume"].sum() > 0
            else 0
        )
        ax2.axhline(hist_wa, color="#BDC3C7", linestyle="--", linewidth=3, alpha=0.5)
        ax2.axhline(l12m_wa, color="#2E86AB", linestyle="--", linewidth=3, alpha=0.5)

        ax2.set_ylabel("DCTR (%)", fontsize=28, fontweight="bold")
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{int(v)}%"))
        ax2.tick_params(axis="y", labelsize=22)
        max_dctr = max(merged["L12M DCTR %"].max(), merged["Historical DCTR %"].max())
        ax2.set_ylim(0, max_dctr * 1.2 if max_dctr > 0 else 100)
        ax2.grid(False)
        for spine in ax2.spines.values():
            spine.set_visible(False)

        plt.title(
            "Debit Card Take Rate by Branch\nHistorical vs Trailing Twelve Months",
            fontsize=34,
            fontweight="bold",
            pad=30,
        )
        ax2.legend(
            handles=[hist_line[0], l12m_line[0]],
            labels=["Historical DCTR", "TTM DCTR"],
            loc="upper right",
            bbox_to_anchor=(1.0, 0.98),
            fontsize=22,
            frameon=True,
            fancybox=True,
        )
        plt.subplots_adjust(left=0.08, right=0.92, top=0.93, bottom=0.15)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / "dctr_branch_trend.png")

        trend = "improving" if avg_change > 0 else "declining" if avg_change < 0 else "stable"
        try:
            best_row = merged.loc[merged["L12M DCTR %"].idxmax()]
            worst_row = merged.loc[merged["L12M DCTR %"].idxmin()]
            best_br_name = best_row["Branch"]
            best_br_rate = best_row["L12M DCTR %"]
            worst_br_name = worst_row["Branch"]
            worst_br_rate = worst_row["L12M DCTR %"]
            branch_trend_subtitle = (
                f"{improving}/{len(merged)} branches {trend} (avg {avg_change:+.1f}pp)"
                f" — {best_br_name} leads at {best_br_rate:.1f}%;"
                f" {worst_br_name} trails at {worst_br_rate:.1f}%"
            )
            if len(branch_trend_subtitle) > 120:
                branch_trend_subtitle = (
                    f"{improving} of {len(merged)} branches {trend} ({avg_change:+.1f}pp avg)"
                    f" — {best_br_name} leads at {best_br_rate:.1f}%"
                )
        except Exception:
            branch_trend_subtitle = (
                f"{improving} of {len(merged)} branches {trend} — Avg change: {avg_change:+.1f}pp"
            )
        _slide(
            ctx,
            "A7.10a - Branch DCTR (Hist vs L12M)",
            {
                "title": "Branch DCTR: Historical vs Trailing Twelve Months",
                "subtitle": branch_trend_subtitle,
                "chart_path": cp,
                "layout_index": 13,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch trend chart: {e}")

    ctx["results"]["dctr_branch_trend"] = {
        "improving": improving,
        "total": len(merged),
        "avg_change": avg_change,
    }
    _report(ctx, f"   {improving}/{len(merged)} branches improving | Avg: {avg_change:+.1f}pp")
    return ctx


# =============================================================================
# HEATMAP: Monthly DCTR Heatmap by Branch (A7.13)
# =============================================================================


def run_dctr_heatmap(ctx):
    """A7.13: Monthly DCTR heatmap by branch for L12M."""
    _report(ctx, "\n🗺️ DCTR — Monthly Heatmap (A7.13)")
    chart_dir = ctx["chart_dir"]
    l12m_months = ctx["last_12_months"]
    bm = ctx["config"].get("BranchMapping", {})

    ed = ctx["eligible_data"].copy()
    ed["Date Opened"] = pd.to_datetime(ed["Date Opened"], errors="coerce")
    ed["Month_Year"] = ed["Date Opened"].dt.strftime("%b%y")
    if bm:
        ed["Branch Name"] = ed["Branch"].map(bm).fillna(ed["Branch"])
    else:
        ed["Branch Name"] = ed["Branch"]

    branches = sorted(ed["Branch Name"].unique())
    if len(branches) == 0 or len(l12m_months) == 0:
        _report(ctx, "   ⚠️ No branch/month data")
        return ctx

    # Build heatmap matrix
    heat_data = []
    for branch in branches:
        bd = ed[ed["Branch Name"] == branch]
        row = {"Branch": branch}
        for month in l12m_months:
            md = bd[bd["Month_Year"] == month]
            t = len(md)
            w = len(md[md["Debit?"] == "Yes"])
            row[month] = (w / t * 100) if t > 0 else np.nan
        heat_data.append(row)

    heat_df = pd.DataFrame(heat_data).set_index("Branch")
    _save(ctx, heat_df.reset_index(), "DCTR-Heatmap", "Monthly DCTR Heatmap by Branch")

    try:
        n_branches = len(branches)
        n_months = len(l12m_months)
        fig_h = max(8, n_branches * 0.6 + 2)
        fig, ax = plt.subplots(figsize=(max(14, n_months * 1.2), fig_h))
        try:
            # Custom colormap: red → yellow → green
            cmap = LinearSegmentedColormap.from_list(
                "dctr", ["#E74C3C", "#F39C12", "#F1C40F", "#2ECC71", "#27AE60"]
            )
            data_vals = heat_df.values
            valid_vals = data_vals[~np.isnan(data_vals)]
            vmin = np.percentile(valid_vals, 5) if len(valid_vals) else 0
            vmax = np.percentile(valid_vals, 95) if len(valid_vals) else 100

            im = ax.imshow(data_vals, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)

            # Labels
            ax.set_xticks(range(n_months))
            ax.set_xticklabels(l12m_months, rotation=45, ha="right", fontsize=14)
            ax.set_yticks(range(n_branches))
            ax.set_yticklabels(branches, fontsize=14)

            # Cell text
            for i in range(n_branches):
                for j in range(n_months):
                    v = data_vals[i, j]
                    if not np.isnan(v):
                        txt_color = "white" if v < (vmin + vmax) / 2 else "black"
                        ax.text(
                            j,
                            i,
                            f"{v:.0f}",
                            ha="center",
                            va="center",
                            fontsize=12,
                            fontweight="bold",
                            color=txt_color,
                        )

            plt.colorbar(im, ax=ax, label="DCTR %", shrink=0.8)
            ax.set_title("Monthly DCTR Heatmap by Branch (TTM)", fontsize=20, fontweight="bold")
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_heatmap.png")
        finally:
            plt.close(fig)

        # Overall weighted DCTR
        t_all = len(ed[ed["Month_Year"].isin(l12m_months)])
        w_all = len(ed[(ed["Month_Year"].isin(l12m_months)) & (ed["Debit?"] == "Yes")])
        weighted_avg = w_all / t_all * 100 if t_all else 0

        try:
            branch_avgs = heat_df.mean(axis=1).dropna()
            best_hm_branch = branch_avgs.idxmax() if not branch_avgs.empty else "N/A"
            worst_hm_branch = branch_avgs.idxmin() if not branch_avgs.empty else "N/A"
            best_hm_rate = branch_avgs.max() if not branch_avgs.empty else 0
            worst_hm_rate = branch_avgs.min() if not branch_avgs.empty else 0
            heatmap_subtitle = (
                f"TTM weighted avg {weighted_avg:.1f}% — {best_hm_branch} leads"
                f" ({best_hm_rate:.1f}%), {worst_hm_branch} trails ({worst_hm_rate:.1f}%)"
            )
            if len(heatmap_subtitle) > 120:
                heatmap_subtitle = (
                    f"TTM weighted avg {weighted_avg:.1f}% across {n_branches} branches"
                    f" — {best_hm_branch} best ({best_hm_rate:.1f}%)"
                )
        except Exception:
            heatmap_subtitle = (
                f"Weighted avg: {weighted_avg:.1f}% across {n_branches} branches × {n_months} months"
            )
        _slide(
            ctx,
            "A7.13 - Monthly Heatmap",
            {
                "title": "Monthly DCTR Heatmap by Branch (TTM)",
                "subtitle": heatmap_subtitle,
                "chart_path": cp,
                "layout_index": 9,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Heatmap: {e}")

    ctx["results"]["dctr_heatmap"] = {"branches": len(branches)}
    _report(ctx, f"   {len(branches)} branches × {len(l12m_months)} months")
    return ctx


# =============================================================================
# SEASONALITY: Month/Quarter/Day-of-Week Analysis (A7.14)
# =============================================================================


def run_dctr_seasonality(ctx):
    """A7.14: DCTR seasonality by month, quarter, and day-of-week."""
    _report(ctx, "\n📅 DCTR — Seasonality (A7.14)")
    chart_dir = ctx["chart_dir"]
    ed = ctx["eligible_data"].copy()
    ed["Date Opened"] = pd.to_datetime(ed["Date Opened"], errors="coerce")
    valid = ed[ed["Date Opened"].notna()].copy()

    if valid.empty:
        _report(ctx, "   ⚠️ No date data")
        return ctx

    valid["Month Name"] = valid["Date Opened"].dt.month_name()
    valid["Quarter"] = "Q" + valid["Date Opened"].dt.quarter.astype(str)
    valid["Day of Week"] = valid["Date Opened"].dt.day_name()

    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    q_order = ["Q1", "Q2", "Q3", "Q4"]

    # Monthly DCTR
    m_rows = []
    for m in month_order:
        md = valid[valid["Month Name"] == m]
        if len(md) > 0:
            t, w, d = _dctr(md)
            m_rows.append(
                {"Month Name": m, "Total Accounts": t, "With Debit": w, "DCTR %": d * 100}
            )
    monthly = pd.DataFrame(m_rows)

    # Quarterly
    q_rows = []
    for q in q_order:
        qd = valid[valid["Quarter"] == q]
        if len(qd) > 0:
            t, w, d = _dctr(qd)
            q_rows.append({"Quarter": q, "Total Accounts": t, "With Debit": w, "DCTR %": d * 100})
    quarterly = pd.DataFrame(q_rows)

    # Day of week
    d_rows = []
    for d in dow_order:
        dd = valid[valid["Day of Week"] == d]
        if len(dd) > 0:
            t, w, d_val = _dctr(dd)
            d_rows.append(
                {"Day of Week": d, "Total Accounts": t, "With Debit": w, "DCTR %": d_val * 100}
            )
    dow = pd.DataFrame(d_rows)

    _save(
        ctx,
        {"Monthly": monthly, "Quarterly": quarterly, "Day of Week": dow},
        "DCTR-Seasonality",
        "DCTR Seasonality Analysis",
    )

    try:
        fig, axes = plt.subplots(1, 3, figsize=(22, 8))

        # Monthly
        if not monthly.empty:
            ax = axes[0]
            vals = monthly["DCTR %"].values
            ax.bar(range(len(monthly)), vals, color="#2E86AB", edgecolor="white")
            ax.set_xticks(range(len(monthly)))
            ax.set_xticklabels([m[:3] for m in monthly["Month Name"]], rotation=45, fontsize=14)
            for i, v in enumerate(vals):
                ax.text(i, v + 0.5, f"{v:.0f}%", ha="center", fontsize=12, fontweight="bold")
            ax.set_ylabel("DCTR (%)", fontsize=14)
            ax.set_title("By Month", fontweight="bold", fontsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.tick_params(axis="y", labelsize=12)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

        # Quarterly
        if not quarterly.empty:
            ax = axes[1]
            vals = quarterly["DCTR %"].values
            ax.bar(quarterly["Quarter"], vals, color="#4ECDC4", edgecolor="white", width=0.6)
            for i, v in enumerate(vals):
                ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=14, fontweight="bold")
            ax.set_ylabel("DCTR (%)", fontsize=14)
            ax.set_title("By Quarter", fontweight="bold", fontsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.tick_params(axis="both", labelsize=12)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

        # Day of Week
        if not dow.empty:
            ax = axes[2]
            vals = dow["DCTR %"].values
            weekday_mask = [d not in ["Saturday", "Sunday"] for d in dow["Day of Week"]]
            colors = ["#2E86AB" if wd else "#E74C3C" for wd in weekday_mask]
            ax.bar(range(len(dow)), vals, color=colors, edgecolor="white")
            ax.set_xticks(range(len(dow)))
            ax.set_xticklabels([d[:3] for d in dow["Day of Week"]], fontsize=14)
            for i, v in enumerate(vals):
                ax.text(i, v + 0.5, f"{v:.0f}%", ha="center", fontsize=12, fontweight="bold")
            ax.set_ylabel("DCTR (%)", fontsize=14)
            ax.set_title("By Day of Week", fontweight="bold", fontsize=16)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.tick_params(axis="y", labelsize=12)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

        plt.suptitle("DCTR Seasonality Analysis", fontsize=22, fontweight="bold", y=1.02)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / "dctr_seasonality.png")

        # Insights
        best_month = (
            monthly.loc[monthly["DCTR %"].idxmax(), "Month Name"] if not monthly.empty else "N/A"
        )
        worst_month = (
            monthly.loc[monthly["DCTR %"].idxmin(), "Month Name"] if not monthly.empty else "N/A"
        )
        best_dctr = monthly["DCTR %"].max() if not monthly.empty else 0
        worst_dctr = monthly["DCTR %"].min() if not monthly.empty else 0
        spread = best_dctr - worst_dctr

        weekday_avg = (
            dow[~dow["Day of Week"].isin(["Saturday", "Sunday"])]["DCTR %"].mean()
            if not dow.empty
            else 0
        )
        weekend_avg = (
            dow[dow["Day of Week"].isin(["Saturday", "Sunday"])]["DCTR %"].mean()
            if not dow.empty
            else 0
        )

        _slide(
            ctx,
            "A7.14 - Seasonality",
            {
                "title": "DCTR Seasonality Analysis",
                "subtitle": f"Best: {best_month} ({best_dctr:.0f}%) — Worst: {worst_month} ({worst_dctr:.0f}%) — {spread:.0f}pp spread",
                "chart_path": cp,
                "layout_index": 9,
                "insights": [
                    f"Monthly DCTR spread: {spread:.1f}pp",
                    f"Weekday avg: {weekday_avg:.1f}% | Weekend avg: {weekend_avg:.1f}%",
                ],
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Seasonality chart: {e}")

    ctx["results"]["dctr_seasonality"] = {
        "best_month": best_month if not monthly.empty else "N/A",
        "worst_month": worst_month if not monthly.empty else "N/A",
        "spread": spread if not monthly.empty else 0,
    }
    _report(
        ctx,
        f"   Best: {best_month if not monthly.empty else 'N/A'} | Worst: {worst_month if not monthly.empty else 'N/A'}",
    )
    return ctx


# =============================================================================
# VINTAGE: Vintage Curves & Cohort Analysis (A7.15)
# =============================================================================


def run_dctr_vintage(ctx):
    """A7.15: Vintage curves (DCTR by account age) + cohort analysis by year."""
    _report(ctx, "\n📊 DCTR — Vintage & Cohort (A7.15)")
    chart_dir = ctx["chart_dir"]
    ed = ctx["eligible_data"].copy()
    ed["Date Opened"] = pd.to_datetime(ed["Date Opened"], errors="coerce")
    valid = ed[ed["Date Opened"].notna()].copy()

    if valid.empty:
        _report(ctx, "   ⚠️ No data")
        return ctx

    valid["Account Age Days"] = (pd.Timestamp.now() - valid["Date Opened"]).dt.days
    valid["Year"] = valid["Date Opened"].dt.year

    # Vintage buckets (fine-grained)
    vintage_buckets = [
        ("0-30 days", 0, 30),
        ("31-90 days", 31, 90),
        ("91-180 days", 91, 180),
        ("181-365 days", 181, 365),
        ("1-2 years", 366, 730),
        ("2-3 years", 731, 1095),
        ("3-5 years", 1096, 1825),
        ("5-10 years", 1826, 3650),
        ("10+ years", 3651, 999999),
    ]

    v_rows = []
    cum_debit = 0
    cum_total = 0
    for label, lo, hi in vintage_buckets:
        seg = valid[(valid["Account Age Days"] >= lo) & (valid["Account Age Days"] <= hi)]
        if len(seg) > 0:
            t, w, d = _dctr(seg)
            cum_total += t
            cum_debit += w
            v_rows.append(
                {
                    "Age Bucket": label,
                    "Total Accounts": t,
                    "With Debit": w,
                    "DCTR %": d * 100,
                    "Cumulative Capture %": cum_debit / cum_total * 100 if cum_total else 0,
                }
            )
    vintage_df = pd.DataFrame(v_rows)

    # Cohort analysis by year
    cohort_years = sorted(valid["Year"].dropna().unique())
    c_rows = []
    for yr in cohort_years:
        seg = valid[valid["Year"] == yr]
        if len(seg) > 10:
            t, w, d = _dctr(seg)
            c_rows.append(
                {"Cohort Year": int(yr), "Total Accounts": t, "With Debit": w, "DCTR %": d * 100}
            )
    cohort_df = pd.DataFrame(c_rows)

    _save(
        ctx,
        {"Vintage": vintage_df, "Cohort": cohort_df},
        "DCTR-Vintage",
        "Vintage & Cohort Analysis",
    )

    try:
        fig = plt.figure(figsize=(18, 12))
        try:
            # Top: Vintage curve with cumulative line
            ax1 = plt.subplot(2, 1, 1)
            if not vintage_df.empty:
                x_pos = np.arange(len(vintage_df))
                bars = ax1.bar(
                    x_pos, vintage_df["DCTR %"], color="#2E86AB", alpha=0.8, edgecolor="white"
                )
                for bar, v in zip(bars, vintage_df["DCTR %"]):
                    ax1.text(
                        bar.get_x() + bar.get_width() / 2,
                        v + 1,
                        f"{v:.0f}%",
                        ha="center",
                        fontsize=14,
                        fontweight="bold",
                    )

                ax1_twin = ax1.twinx()
                ax1_twin.plot(
                    x_pos,
                    vintage_df["Cumulative Capture %"],
                    color="#E74C3C",
                    marker="o",
                    ms=9,
                    lw=3,
                    label="Cumulative Capture %",
                )
                for x, y in zip(x_pos, vintage_df["Cumulative Capture %"]):
                    ax1_twin.text(
                        x,
                        y + 2,
                        f"{y:.0f}%",
                        ha="center",
                        fontsize=12,
                        color="#E74C3C",
                        fontweight="bold",
                    )

                ax1.set_xticks(x_pos)
                ax1.set_xticklabels(vintage_df["Age Bucket"], rotation=30, ha="right", fontsize=14)
                ax1.set_ylabel("DCTR %", color="#2E86AB", fontsize=16)
                ax1.set_title("DCTR by Account Age (Vintage Curve)", fontweight="bold", fontsize=18)
                ax1_twin.set_ylabel("Cumulative Capture %", color="#E74C3C", fontsize=16)
                ax1_twin.set_ylim(0, 110)
                ax1.tick_params(axis="y", labelsize=14)
                ax1_twin.tick_params(axis="y", labelsize=14)
                ax1.grid(axis="y", alpha=0.2, ls="--")

            # Bottom: Cohort trend
            ax2 = plt.subplot(2, 1, 2)
            if not cohort_df.empty and len(cohort_df) >= 2:
                years = cohort_df["Cohort Year"].values
                dctr_by_year = cohort_df["DCTR %"].values
                bars2 = ax2.bar(
                    range(len(years)), dctr_by_year, color="#4ECDC4", edgecolor="white", alpha=0.8
                )
                for i, (bar, v) in enumerate(zip(bars2, dctr_by_year)):
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2,
                        v + 1,
                        f"{v:.0f}%",
                        ha="center",
                        fontsize=14,
                        fontweight="bold",
                    )

                # Trend line
                z = np.polyfit(range(len(years)), dctr_by_year, 1)
                p = np.poly1d(z)
                ax2.plot(
                    range(len(years)), p(range(len(years))), color="red", ls="--", lw=2, alpha=0.7
                )

                ax2.set_xticks(range(len(years)))
                ax2.set_xticklabels(years, fontsize=14, rotation=30, ha="right")
                ax2.set_ylabel("DCTR %", fontsize=16)
                ax2.set_title(
                    "DCTR by Account Opening Year (Cohort Analysis)", fontweight="bold", fontsize=18
                )
                ax2.tick_params(axis="y", labelsize=14)
                ax2.grid(axis="y", alpha=0.2, ls="--")

                slope = z[0]
                trend = f"+{slope:.1f}pp/yr" if slope > 0 else f"{slope:.1f}pp/yr"
                tc = "green" if slope > 0 else "red"
                ax2.text(
                    0.98,
                    0.95,
                    f"Trend: {trend}",
                    transform=ax2.transAxes,
                    fontsize=16,
                    ha="right",
                    va="top",
                    fontweight="bold",
                    color=tc,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=tc),
                )
            else:
                slope = 0

            plt.suptitle("Vintage Curves & Cohort Analysis", fontsize=22, fontweight="bold", y=1.01)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_vintage.png")
        finally:
            plt.close(fig)

        # Insights
        new_dctr = vintage_df.iloc[0]["DCTR %"] if not vintage_df.empty else 0
        mature_dctr = vintage_df.iloc[-1]["DCTR %"] if not vintage_df.empty else 0
        gap = new_dctr - mature_dctr

        _slide(
            ctx,
            "A7.15 - Vintage & Cohort",
            {
                "title": "Vintage Curves & Cohort Analysis",
                "subtitle": f"New accounts at {new_dctr:.0f}% vs mature at {mature_dctr:.0f}% — "
                f"Cohort trend {'improving' if slope > 0 else 'declining'} at {slope:.1f}pp/year",
                "chart_path": cp,
                "layout_index": 9,
                "insights": [
                    f"New (0-30 days) DCTR: {new_dctr:.1f}%",
                    f"Mature (10+ years) DCTR: {mature_dctr:.1f}%",
                    f"Gap: {gap:+.1f}pp",
                    f"Cohort years: {len(cohort_df)}",
                ],
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Vintage chart: {e}")

    ctx["results"]["dctr_vintage"] = {
        "new_dctr": vintage_df.iloc[0]["DCTR %"] if not vintage_df.empty else 0,
        "mature_dctr": vintage_df.iloc[-1]["DCTR %"] if not vintage_df.empty else 0,
        "cohort_slope": slope if "slope" in dir() else 0,
    }
    _report(ctx, f"   {len(vintage_df)} vintage buckets | {len(cohort_df)} cohort years")
    return ctx


# =============================================================================
# PERSONAL VS BUSINESS BY DECADE (A7.6b)
# =============================================================================


def run_dctr_decade_pb(ctx):
    """A7.6b: Personal vs Business DCTR by decade — grouped bar chart."""
    _report(ctx, "\n📊 DCTR — Personal vs Business by Decade (A7.6b)")
    chart_dir = ctx["chart_dir"]

    d4 = ctx["results"].get("dctr_4", {}).get("decade", pd.DataFrame())
    d5 = ctx["results"].get("dctr_5", {}).get("decade", pd.DataFrame())

    if d4.empty:
        _report(ctx, "   ⚠️ No personal decade data")
        return ctx

    has_biz = not d5.empty and d5["Total Accounts"].sum() > 0
    p_dec = d4[d4["Decade"] != "TOTAL"].copy()

    if has_biz:
        b_dec = d5[d5["Decade"] != "TOTAL"].copy()
        all_decades = sorted(set(p_dec["Decade"].tolist()) | set(b_dec["Decade"].tolist()))
    else:
        all_decades = p_dec["Decade"].tolist()

    try:
        fig, ax = plt.subplots(figsize=(16, 8))
        try:
            x = np.arange(len(all_decades))

            # Personal DCTR by decade
            p_rates = []
            for d in all_decades:
                match = p_dec[p_dec["Decade"] == d]
                p_rates.append(match["DCTR %"].iloc[0] * 100 if not match.empty else 0)

            if has_biz:
                width = 0.35
                b_rates = []
                for d in all_decades:
                    match = b_dec[b_dec["Decade"] == d]
                    b_rates.append(match["DCTR %"].iloc[0] * 100 if not match.empty else 0)

                ax.bar(
                    x - width / 2,
                    p_rates,
                    width,
                    label="Personal",
                    color="#4472C4",
                    alpha=0.9,
                    edgecolor="black",
                    linewidth=2,
                )
                ax.bar(
                    x + width / 2,
                    b_rates,
                    width,
                    label="Business",
                    color="#ED7D31",
                    alpha=0.9,
                    edgecolor="black",
                    linewidth=2,
                )

                for i, v in enumerate(p_rates):
                    if v > 0:
                        ax.text(
                            i - width / 2,
                            v + 1,
                            f"{v:.0f}%",
                            ha="center",
                            fontsize=18,
                            fontweight="bold",
                            color="#4472C4",
                        )
                for i, v in enumerate(b_rates):
                    if v > 0:
                        ax.text(
                            i + width / 2,
                            v + 1,
                            f"{v:.0f}%",
                            ha="center",
                            fontsize=18,
                            fontweight="bold",
                            color="#ED7D31",
                        )
            else:
                ax.bar(
                    x,
                    p_rates,
                    0.6,
                    label="Personal",
                    color="#4472C4",
                    alpha=0.9,
                    edgecolor="black",
                    linewidth=2,
                )
                for i, v in enumerate(p_rates):
                    if v > 0:
                        ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=20, fontweight="bold")

            ax.set_title(
                "Eligible Personal vs Business DCTR by Decade",
                fontsize=24,
                fontweight="bold",
                pad=20,
            )
            ax.set_xlabel("Decade", fontsize=20, fontweight="bold")
            ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels(all_decades, fontsize=20)
            ax.tick_params(axis="y", labelsize=20)
            max_v = max(p_rates + (b_rates if has_biz else []))
            ax.set_ylim(0, max_v * 1.15 if max_v > 0 else 100)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.legend(
                loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=18, frameon=True
            )
            ax.grid(True, axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_decade_pb.png")
        finally:
            plt.close(fig)

        try:
            p_change = p_rates[-1] - p_rates[0] if len(p_rates) >= 2 else 0
            p_dir = "improving" if p_change > 0 else "declining" if p_change < 0 else "flat"
            if has_biz and b_rates and len(b_rates) >= 2:
                b_change = b_rates[-1] - b_rates[0]
                b_dir = "improving" if b_change > 0 else "declining" if b_change < 0 else "flat"
                subtitle = (
                    f"Personal {p_dir}: {p_rates[0]:.0f}% → {p_rates[-1]:.0f}% ({p_change:+.1f}pp)"
                    f" | Business {b_dir}: {b_rates[0]:.0f}% → {b_rates[-1]:.0f}% ({b_change:+.1f}pp)"
                )
                if len(subtitle) > 120:
                    subtitle = (
                        f"Personal {p_change:+.1f}pp ({p_rates[-1]:.0f}% latest)"
                        f" | Business {b_change:+.1f}pp ({b_rates[-1]:.0f}% latest) — by decade"
                    )
            else:
                subtitle = (
                    f"Personal {p_dir}: {p_rates[0]:.0f}% → {p_rates[-1]:.0f}%"
                    f" ({p_change:+.1f}pp) across {len(all_decades)} decades"
                )
        except Exception:
            subtitle = f"Personal: {p_rates[0]:.0f}% → {p_rates[-1]:.0f}%"
            if has_biz and b_rates:
                subtitle += f" | Business: {b_rates[0]:.0f}% → {b_rates[-1]:.0f}%"
        _slide(
            ctx,
            "A7.6b - Personal vs Business by Decade",
            {
                "title": "Eligible Personal vs Business DCTR by Decade",
                "subtitle": subtitle,
                "chart_path": cp,
                "layout_index": 9,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Decade P/B chart: {e}")

    ctx["results"]["dctr_decade_pb"] = {"decades": len(all_decades)}
    _report(ctx, f"   {len(all_decades)} decades plotted")
    return ctx


# =============================================================================
# ELIGIBLE VS NON-ELIGIBLE DCTR (A7.9)
# =============================================================================


def run_dctr_eligible_vs_non(ctx):
    """A7.9: Eligible vs Non-Eligible DCTR comparison (Last 12 Months)."""
    _report(ctx, "\n📊 DCTR — Eligible vs Non-Eligible (A7.9)")
    chart_dir = ctx["chart_dir"]
    sd, ed_date = ctx["start_date"], ctx["end_date"]

    data = ctx["data"].copy()
    data["Date Opened"] = pd.to_datetime(data["Date Opened"], errors="coerce")
    l12m_all = data[(data["Date Opened"] >= sd) & (data["Date Opened"] <= ed_date)]

    # Open accounts in L12M
    open_l12m = ctx.get("open_last_12m")
    if open_l12m is None or open_l12m.empty:
        open_l12m = (
            l12m_all[l12m_all["Date Closed"].isna()]
            if "Date Closed" in l12m_all.columns
            else l12m_all
        )

    elig_l12m = ctx.get("eligible_last_12m")
    if elig_l12m is None or elig_l12m.empty:
        _report(ctx, "   ⚠️ No L12M eligible data")
        return ctx

    # Non-eligible = open but not eligible
    non_elig = open_l12m[~open_l12m.index.isin(elig_l12m.index)]

    e_total = len(elig_l12m)
    e_debit = len(elig_l12m[elig_l12m["Debit?"] == "Yes"])
    e_dctr = (e_debit / e_total * 100) if e_total > 0 else 0

    n_total = len(non_elig)
    n_debit = len(non_elig[non_elig["Debit?"] == "Yes"]) if not non_elig.empty else 0
    n_dctr = (n_debit / n_total * 100) if n_total > 0 else 0

    gap = e_dctr - n_dctr

    # Excel export
    comp_df = pd.DataFrame(
        [
            {
                "Account Type": "Eligible",
                "Total": e_total,
                "With Debit": e_debit,
                "DCTR %": e_dctr / 100,
            },
            {
                "Account Type": "Non-Eligible",
                "Total": n_total,
                "With Debit": n_debit,
                "DCTR %": n_dctr / 100,
            },
        ]
    )
    _save(
        ctx,
        comp_df,
        "DCTR-EligVsNon-L12M",
        "Eligible vs Non-Eligible DCTR",
        {
            "Eligible DCTR": f"{e_dctr:.1f}%",
            "Non-Eligible DCTR": f"{n_dctr:.1f}%",
            "Gap": f"{gap:+.1f}pp",
        },
    )

    # Chart A7.9: Side-by-side bars matching notebook
    try:
        fig, ax = plt.subplots(figsize=(14, 7))
        try:
            categories = ["Eligible\nAccounts", "Non-Eligible\nAccounts"]
            dctr_vals = [e_dctr, n_dctr]
            counts = [e_total, n_total]
            debit_counts = [e_debit, n_debit]
            colors = ["#2ecc71", "#e74c3c"]

            bars = ax.bar(
                categories, dctr_vals, color=colors, edgecolor="black", linewidth=2, alpha=0.8
            )
            for bar, d, cnt, wd in zip(bars, dctr_vals, counts, debit_counts):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    d + 1,
                    f"{d:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=24,
                    fontweight="bold",
                )
                if d > 20:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        d / 2,
                        f"{cnt:,}\naccounts\n\n{wd:,}\nwith debit",
                        ha="center",
                        va="center",
                        fontsize=16,
                        fontweight="bold",
                        color="white",
                    )

            # Gap indicator
            gap_text = f"Gap: {gap:+.1f}pp\n{'Eligible performs better' if gap > 0 else 'Non-eligible performs better'}"
            gc = "green" if gap > 0 else "red"
            ax.text(
                0.5,
                0.5,
                gap_text,
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=20,
                fontweight="bold",
                color=gc,
                bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=gc, linewidth=2),
            )

            ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
            ax.set_title(
                "Trailing Twelve Months: Eligible vs Non-Eligible DCTR",
                fontsize=24,
                fontweight="bold",
                pad=20,
            )
            ax.set_ylim(0, max(dctr_vals) * 1.15 if max(dctr_vals) > 0 else 100)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.tick_params(axis="both", labelsize=20)
            ax.grid(False)
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            period_text = f"Period: {sd.strftime('%b %Y')} - {ed_date.strftime('%b %Y')}"
            ax.text(
                0.5,
                -0.10,
                period_text,
                transform=ax.transAxes,
                fontsize=16,
                ha="center",
                style="italic",
                color="gray",
            )
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_eligible_vs_non.png")
        finally:
            plt.close(fig)

        better = "Eligible" if gap > 0 else "Non-Eligible"
        _slide(
            ctx,
            "A7.9 - Eligible vs Non-Eligible DCTR",
            {
                "title": "Eligible vs Non-Eligible DCTR (Trailing Twelve Months)",
                "subtitle": f"Eligible at {e_dctr:.0f}% vs Non-Eligible at {n_dctr:.0f}% — Gap of {gap:+.1f}pp",
                "chart_path": cp,
                "layout_index": 9,
                "insights": [
                    f"Period: {sd.strftime('%b %Y')} to {ed_date.strftime('%b %Y')}",
                    f"Eligible: {e_total:,} ({e_dctr:.1f}% DCTR)",
                    f"Non-Eligible: {n_total:,} ({n_dctr:.1f}% DCTR)",
                    f"{better} outperform by {abs(gap):.1f}pp",
                ],
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Eligible vs Non chart: {e}")

    ctx["results"]["dctr_elig_vs_non"] = {
        "eligible_dctr": e_dctr,
        "non_eligible_dctr": n_dctr,
        "gap": gap,
    }
    _report(ctx, f"   Eligible: {e_dctr:.1f}% | Non-Eligible: {n_dctr:.1f}% | Gap: {gap:+.1f}pp")
    return ctx


# =============================================================================
# BRANCH DCTR L12M FOCUS — VERTICAL BARS (A7.10b)
# =============================================================================


def run_dctr_branch_l12m(ctx):
    """A7.10b: Branch DCTR with L12M focus — vertical bars sorted by L12M, volume + DCTR lines."""
    _report(ctx, "\n🏢 DCTR — Branch L12M Focus (A7.10b)")
    chart_dir = ctx["chart_dir"]
    bm = ctx["config"].get("BranchMapping", {})

    hist_df, _ = _branch_dctr(ctx["eligible_data"], bm)
    l12m_df, _ = _branch_dctr(ctx["eligible_last_12m"], bm)

    if hist_df.empty or l12m_df.empty:
        _report(ctx, "   ⚠️ Insufficient branch data")
        return ctx

    hd = hist_df[hist_df["Branch"] != "TOTAL"][["Branch", "DCTR %", "Total Accounts"]].rename(
        columns={"DCTR %": "Historical DCTR", "Total Accounts": "Hist Volume"}
    )
    ld = l12m_df[l12m_df["Branch"] != "TOTAL"][["Branch", "DCTR %", "Total Accounts"]].rename(
        columns={"DCTR %": "L12M DCTR", "Total Accounts": "L12M Volume"}
    )
    merged = hd.merge(ld, on="Branch", how="outer").fillna(0)
    merged = merged.sort_values("L12M DCTR", ascending=False).reset_index(drop=True)
    merged["Historical DCTR %"] = merged["Historical DCTR"] * 100
    merged["L12M DCTR %"] = merged["L12M DCTR"] * 100
    merged["Change %"] = merged["L12M DCTR %"] - merged["Historical DCTR %"]

    # Weighted averages
    hist_wa = (
        (merged["Historical DCTR"] * merged["Hist Volume"]).sum()
        / merged["Hist Volume"].sum()
        * 100
        if merged["Hist Volume"].sum() > 0
        else 0
    )
    l12m_wa = (
        (merged["L12M DCTR"] * merged["L12M Volume"]).sum() / merged["L12M Volume"].sum() * 100
        if merged["L12M Volume"].sum() > 0
        else 0
    )

    n = len(merged)
    improving = (merged["Change %"] > 0).sum()
    avg_change = merged["Change %"].mean()

    # Chart A7.10b: Large vertical bars + DCTR lines (matching notebook)
    try:
        fig, ax1 = plt.subplots(figsize=(28, 14))
        x_pos = np.arange(n)

        # Volume bars
        bars = ax1.bar(
            x_pos, merged["L12M Volume"], width=0.6, color="#D9D9D9", edgecolor="black", linewidth=2
        )
        ax1.set_ylabel("Eligible Accounts (TTM)", fontsize=28, fontweight="bold")
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(
            merged["Branch"].values, rotation=45, ha="right", fontsize=24, fontweight="bold"
        )
        ax1.tick_params(axis="y", labelsize=22)
        ax1.grid(False)
        for spine in ax1.spines.values():
            spine.set_visible(False)

        # Volume labels
        for i, v in enumerate(merged["L12M Volume"]):
            ax1.text(
                i,
                v + max(merged["L12M Volume"]) * 0.015,
                f"{int(v):,}",
                ha="center",
                va="bottom",
                fontsize=22,
                fontweight="bold",
                color="#333",
            )

        # DCTR lines on secondary axis
        ax2 = ax1.twinx()
        hist_line = ax2.plot(
            x_pos,
            merged["Historical DCTR %"],
            "o-",
            color="#BDC3C7",
            lw=3,
            ms=10,
            label="Historical DCTR",
        )
        l12m_line = ax2.plot(
            x_pos,
            merged["L12M DCTR %"],
            "o-",
            color="#2E86AB",
            lw=4,
            ms=14,
            label="TTM DCTR",
            zorder=5,
        )

        # Data labels on lines
        for i, v in enumerate(merged["L12M DCTR %"]):
            ax2.text(
                i, v + 2, f"{v:.0f}%", ha="center", fontsize=22, fontweight="bold", color="#2E86AB"
            )
        for i, v in enumerate(merged["Historical DCTR %"]):
            ax2.text(i, v - 3, f"{v:.0f}%", ha="center", fontsize=18, color="#BDC3C7")

        ax2.set_ylabel("DCTR (%)", fontsize=28, fontweight="bold")
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
        ax2.tick_params(axis="y", labelsize=22)
        max_dctr = max(merged["L12M DCTR %"].max(), merged["Historical DCTR %"].max())
        ax2.set_ylim(0, max_dctr * 1.2 if max_dctr > 0 else 100)
        ax2.grid(False)
        for spine in ax2.spines.values():
            spine.set_visible(False)

        plt.title(
            "Debit Card Take Rate by Branch\nHistorical vs Trailing Twelve Months",
            fontsize=34,
            fontweight="bold",
            pad=30,
        )
        ax2.legend(
            handles=[hist_line[0], l12m_line[0]],
            labels=["Historical DCTR", "TTM DCTR"],
            loc="upper right",
            bbox_to_anchor=(1.0, 0.98),
            fontsize=22,
            frameon=True,
            fancybox=True,
        )
        plt.subplots_adjust(left=0.08, right=0.92, top=0.93, bottom=0.15)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / "dctr_branch_l12m.png")

        trend = "improving" if avg_change > 0 else "declining" if avg_change < 0 else "stable"
        try:
            best_l12m_row = merged.iloc[0]
            worst_l12m_row = merged.iloc[-1]
            best_l12m_name = best_l12m_row["Branch"]
            best_l12m_rate = best_l12m_row["L12M DCTR %"]
            worst_l12m_name = worst_l12m_row["Branch"]
            worst_l12m_rate = worst_l12m_row["L12M DCTR %"]
            vs_hist = l12m_wa - hist_wa
            branch_l12m_subtitle = (
                f"TTM avg {l12m_wa:.1f}% ({vs_hist:+.1f}pp vs historical)"
                f" — {best_l12m_name} leads at {best_l12m_rate:.1f}%;"
                f" {worst_l12m_name} trails at {worst_l12m_rate:.1f}%"
            )
            if len(branch_l12m_subtitle) > 120:
                branch_l12m_subtitle = (
                    f"TTM avg {l12m_wa:.1f}% ({vs_hist:+.1f}pp vs historical);"
                    f" {improving}/{n} branches {trend}"
                )
        except Exception:
            branch_l12m_subtitle = (
                f"TTM avg at {l12m_wa:.0f}% — {improving} of {n} branches {trend} ({avg_change:+.1f}pp)"
            )
        _slide(
            ctx,
            "A7.10b - Branch DCTR (L12M Focus)",
            {
                "title": "Branch DCTR: TTM Performance",
                "subtitle": branch_l12m_subtitle,
                "chart_path": cp,
                "layout_index": 9,
                "insights": [
                    f"Branches analyzed: {n}",
                    f"TTM weighted average: {l12m_wa:.1f}%",
                    f"Historical weighted average: {hist_wa:.1f}%",
                    f"Branches improving: {improving} of {n}",
                ],
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch L12M chart: {e}")

    ctx["results"]["dctr_branch_l12m"] = {
        "improving": improving,
        "total": n,
        "avg_change": avg_change,
    }
    _report(ctx, f"   {improving}/{n} branches improving | L12M avg: {l12m_wa:.1f}%")
    return ctx
