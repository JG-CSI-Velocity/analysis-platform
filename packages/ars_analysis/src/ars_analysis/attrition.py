"""
attrition.py -- A9 Account Attrition Analysis
===============================================
Comprehensive attrition analysis across all dimensions:
  A9.1   Overall Attrition Rate (historical + L12M)
  A9.2   Closure Duration Analysis (time-to-close buckets)
  A9.3   Open vs Closed Comparison (side-by-side tenure)
  A9.4   Attrition by Branch
  A9.5   Attrition by Product Code
  A9.6   Personal vs Business Attrition
  A9.7   Attrition by Account Tenure
  A9.8   Attrition by Balance Tier
  A9.9   Debit Card Retention Effect (hero slide)
  A9.10  Mailer Program Retention Effect (hero slide)
  A9.11  Revenue Impact of Attrition
  A9.12  Attrition Velocity (L12M monthly trend)
  A9.13  ARS-Eligible vs Non-ARS Comparison

Usage:
    from attrition import run_attrition_suite
    ctx = run_attrition_suite(ctx)
"""

import re
import traceback

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from ars_analysis.chart_style import (
    ANNOTATION_SIZE,
    AXIS_LABEL_SIZE,
    BAR_ALPHA,
    BAR_EDGE,
    BUSINESS,
    DATA_LABEL_SIZE,
    LEGEND_SIZE,
    NEGATIVE,
    NEUTRAL,
    PCT_FORMATTER,
    PERSONAL,
    POSITIVE,
    TEAL,
    TICK_SIZE,
    TITLE_SIZE,
    TTM,
)

_STYLE_PATH = Path(__file__).parent / "ars.mplstyle"
if _STYLE_PATH.exists():
    plt.style.use(str(_STYLE_PATH))


# =============================================================================
# HELPERS
# =============================================================================


def _report(ctx, msg):
    print(msg)
    cb = ctx.get("_progress_callback")
    if cb:
        cb(msg)


def _fig(ctx, size="single"):
    mf = ctx.get("_make_figure")
    if mf:
        return mf(size)
    sizes = {
        "single": (14, 7),
        "half": (10, 6),
        "wide": (16, 7),
        "square": (12, 12),
        "large": (28, 14),
        "tall": (14, 10),
    }
    return plt.subplots(figsize=sizes.get(size, (14, 7)))


def _save_chart(fig, path):
    for ax in fig.get_axes():
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _slide(ctx, slide_id, data, category="Attrition"):
    ctx["all_slides"].append({"id": slide_id, "category": category, "data": data, "include": True})


def _save(ctx, df, sheet, title, metrics=None):
    fn = ctx.get("_save_to_excel")
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   Export {sheet}: {e}")


# =============================================================================
# CATEGORIZATION
# =============================================================================

DURATION_ORDER = [
    "0-1 Month",
    "1-3 Months",
    "3-6 Months",
    "6-12 Months",
    "1-2 Years",
    "2-5 Years",
    "5-10 Years",
    "10+ Years",
]

TENURE_ORDER = [
    "0-6 Months",
    "6-12 Months",
    "1-2 Years",
    "2-5 Years",
    "5-10 Years",
    "10+ Years",
]

BALANCE_ORDER = [
    "Negative",
    "$0",
    "$1-$499",
    "$500-$999",
    "$1K-$2.5K",
    "$2.5K-$5K",
    "$5K-$10K",
    "$10K+",
]


def categorize_duration(days):
    """Bucket account lifespan (days) into duration categories."""
    if pd.isna(days) or days < 0:
        return np.nan
    months = days / 30.44
    if months <= 1:
        return "0-1 Month"
    if months <= 3:
        return "1-3 Months"
    if months <= 6:
        return "3-6 Months"
    if months <= 12:
        return "6-12 Months"
    years = days / 365.25
    if years <= 2:
        return "1-2 Years"
    if years <= 5:
        return "2-5 Years"
    if years <= 10:
        return "5-10 Years"
    return "10+ Years"


def categorize_tenure(days):
    """Bucket account tenure (days since opened) into tenure categories."""
    if pd.isna(days) or days < 0:
        return np.nan
    months = days / 30.44
    if months <= 6:
        return "0-6 Months"
    if months <= 12:
        return "6-12 Months"
    years = days / 365.25
    if years <= 2:
        return "1-2 Years"
    if years <= 5:
        return "2-5 Years"
    if years <= 10:
        return "5-10 Years"
    return "10+ Years"


def categorize_balance(bal):
    """Bucket average balance into tiers."""
    if pd.isna(bal):
        return np.nan
    if bal < 0:
        return "Negative"
    if bal == 0:
        return "$0"
    if bal < 500:
        return "$1-$499"
    if bal < 1000:
        return "$500-$999"
    if bal < 2500:
        return "$1K-$2.5K"
    if bal < 5000:
        return "$2.5K-$5K"
    if bal < 10000:
        return "$5K-$10K"
    return "$10K+"


# =============================================================================
# DATA PREPARATION
# =============================================================================


def _prepare_attrition_data(ctx):
    """Prepare open/closed splits and cache on ctx for reuse."""
    cached = ctx["results"].get("_attrition_data")
    if cached is not None:
        return cached

    data = ctx["data"]
    data["Date Opened"] = pd.to_datetime(data["Date Opened"], errors="coerce")
    data["Date Closed"] = pd.to_datetime(data["Date Closed"], errors="coerce")

    open_accts = data[data["Date Closed"].isna()].copy()
    closed_accts = data[data["Date Closed"].notna()].copy()

    # Pre-compute duration for closed accounts
    if not closed_accts.empty:
        closed_accts["_duration_days"] = (
            closed_accts["Date Closed"] - closed_accts["Date Opened"]
        ).dt.days
        closed_accts["_duration_cat"] = closed_accts["_duration_days"].apply(categorize_duration)

    result = (data, open_accts, closed_accts)
    ctx["results"]["_attrition_data"] = result
    return result


# =============================================================================
# A9.1 -- Overall Attrition Rate
# =============================================================================


def run_attrition_1(ctx):
    """A9.1: Overall attrition rate with historical trend."""
    _report(ctx, "\n   A9 -- 1 -- Overall Attrition Rate")
    fig = None
    try:
        all_data, open_accts, closed = _prepare_attrition_data(ctx)
        total = len(all_data)
        n_closed = len(closed)
        if total == 0:
            _report(ctx, "   No data -- skipping A9.1")
            return ctx

        overall_rate = n_closed / total

        # Annual closures trend
        yearly = None
        if n_closed > 0 and "Date Closed" in closed.columns:
            closed_yr = closed.dropna(subset=["Date Closed"]).copy()
            closed_yr["_close_year"] = closed_yr["Date Closed"].dt.year
            yearly = closed_yr.groupby("_close_year").size().reset_index(name="Closures")
            yearly.columns = ["Year", "Closures"]
            yearly = yearly.sort_values("Year")

        # Chart: annual closures bar with trend
        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        if yearly is not None and len(yearly) > 1:
            fig, ax = _fig(ctx, "single")
            ax.bar(
                yearly["Year"].astype(str),
                yearly["Closures"],
                color=NEGATIVE,
                edgecolor=BAR_EDGE,
                alpha=BAR_ALPHA,
            )
            for i, (y, c) in enumerate(zip(yearly["Year"], yearly["Closures"])):
                ax.text(
                    i,
                    c + yearly["Closures"].max() * 0.02,
                    f"{c:,.0f}",
                    ha="center",
                    fontsize=DATA_LABEL_SIZE,
                    fontweight="bold",
                )
            ax.set_title("Account Closures by Year", fontsize=TITLE_SIZE, fontweight="bold", pad=15)
            ax.set_ylabel("Closures", fontsize=AXIS_LABEL_SIZE)
            ax.tick_params(labelsize=TICK_SIZE)
            plt.tight_layout()
            chart_path = _save_chart(fig, chart_dir / "a9_1_overall_attrition.png")
            fig = None

        # L12M rate
        l12m_rate = 0
        sd, ed = ctx.get("start_date"), ctx.get("end_date")
        if sd and ed and n_closed > 0:
            l12m_closed = closed[(closed["Date Closed"] >= sd) & (closed["Date Closed"] <= ed)]
            l12m_open_start = len(
                all_data[(all_data["Date Closed"].isna()) | (all_data["Date Closed"] >= sd)]
            )
            if l12m_open_start > 0:
                l12m_rate = len(l12m_closed) / l12m_open_start

        # Export
        summary = pd.DataFrame(
            [
                {
                    "Metric": "Total Accounts",
                    "Value": total,
                },
                {
                    "Metric": "Open Accounts",
                    "Value": len(open_accts),
                },
                {
                    "Metric": "Closed Accounts",
                    "Value": n_closed,
                },
                {
                    "Metric": "All-Time Attrition Rate",
                    "Value": f"{overall_rate:.1%}",
                },
                {
                    "Metric": "L12M Attrition Rate",
                    "Value": f"{l12m_rate:.1%}",
                },
            ]
        )
        _save(
            ctx,
            summary,
            "ATTR-1-Summary",
            "A9.1 Overall Attrition Rate",
            metrics={"Attrition Rate": f"{overall_rate:.1%}", "L12M Rate": f"{l12m_rate:.1%}"},
        )
        if yearly is not None:
            _save(ctx, yearly, "ATTR-1-Yearly", "A9.1 Annual Closures")

        # Slide
        insight = {
            "title": "Account Attrition Overview",
            "subtitle": (
                f"{overall_rate:.1%} overall attrition rate "
                f"({n_closed:,} of {total:,} accounts closed)"
            ),
            "slide_type": "screenshot_kpi",
            "layout_index": 5,
            "kpis": {
                "Attrition Rate": f"{overall_rate:.1%}",
                "L12M Rate": f"{l12m_rate:.1%}",
            },
            "chart_path": chart_path,
            "category": "Attrition",
        }
        _slide(ctx, "A9.1 - Overall Attrition Rate", insight)
        ctx["results"]["attrition_1"] = {
            "overall_rate": overall_rate,
            "l12m_rate": l12m_rate,
            "total": total,
            "closed": n_closed,
            "yearly": yearly,
        }
        _report(ctx, f"   A9.1 complete -- {overall_rate:.1%} overall, {l12m_rate:.1%} L12M")
    except Exception as e:
        _report(ctx, f"   A9.1 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.2 -- Closure Duration Analysis
# =============================================================================


def run_attrition_2(ctx):
    """A9.2: How long did closed accounts remain open before closing?"""
    _report(ctx, "\n   A9 -- 2 -- Closure Duration Analysis")
    fig = None
    try:
        _, _, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   No closed accounts -- skipping A9.2")
            return ctx

        valid = closed.dropna(subset=["_duration_cat"])
        if valid.empty:
            return ctx

        dur = valid.groupby("_duration_cat").size().reset_index(name="Count")
        dur.columns = ["Duration", "Count"]
        dur["Duration"] = pd.Categorical(dur["Duration"], categories=DURATION_ORDER, ordered=True)
        dur = dur.sort_values("Duration").dropna(subset=["Duration"])
        dur["Pct"] = dur["Count"] / dur["Count"].sum()

        # Key insight: % closing within first year
        first_year_cats = {"0-1 Month", "1-3 Months", "3-6 Months", "6-12 Months"}
        first_year_pct = dur[dur["Duration"].isin(first_year_cats)]["Pct"].sum()

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        bars = ax.barh(
            dur["Duration"].astype(str),
            dur["Count"],
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for bar, pct in zip(bars, dur["Pct"]):
            w = bar.get_width()
            ax.text(
                w + dur["Count"].max() * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"{int(w):,} ({pct:.0%})",
                va="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Account Lifespan Before Closure", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_xlabel("Closed Accounts", fontsize=AXIS_LABEL_SIZE)
        ax.tick_params(labelsize=TICK_SIZE)
        ax.invert_yaxis()
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_2_closure_duration.png")
        fig = None

        _save(
            ctx,
            dur,
            "ATTR-2-Duration",
            "A9.2 Closure Duration",
            metrics={"First Year Closures": f"{first_year_pct:.0%}"},
        )

        insight = {
            "title": "Account Lifespan Before Closure",
            "subtitle": f"{first_year_pct:.0%} of closures happen within the first year",
            "slide_type": "screenshot",
            "layout_index": 4,
            "chart_path": chart_path,
            "category": "Attrition",
        }
        _slide(ctx, "A9.2 - Closure Duration", insight)
        ctx["results"]["attrition_2"] = {"duration": dur, "first_year_pct": first_year_pct}
        _report(ctx, f"   A9.2 complete -- {first_year_pct:.0%} within first year")
    except Exception as e:
        _report(ctx, f"   A9.2 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.3 -- Open vs Closed Comparison
# =============================================================================


def run_attrition_3(ctx):
    """A9.3: Side-by-side comparison of open vs closed accounts."""
    _report(ctx, "\n   A9 -- 3 -- Open vs Closed Comparison")
    fig = None
    try:
        all_data, open_accts, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   No closed accounts -- skipping A9.3")
            return ctx

        now = pd.Timestamp.now()
        metrics = {}
        for label, df in [("Open", open_accts), ("Closed", closed)]:
            metrics[label] = {
                "Count": len(df),
                "Avg Balance": df["Avg Bal"].mean() if "Avg Bal" in df.columns else 0,
            }
            # Find spend/swipe columns
            spend_cols = [c for c in df.columns if c.endswith(" Spend")]
            swipe_cols = [c for c in df.columns if c.endswith(" Swipes")]
            if spend_cols:
                metrics[label]["Avg Monthly Spend"] = df[spend_cols].mean(axis=1).mean()
            if swipe_cols:
                metrics[label]["Avg Monthly Swipes"] = df[swipe_cols].mean(axis=1).mean()

        comp = pd.DataFrame(metrics).T.reset_index()
        comp.columns = ["Status"] + list(comp.columns[1:])

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        plot_metrics = ["Avg Balance"]
        if "Avg Monthly Spend" in comp.columns:
            plot_metrics.append("Avg Monthly Spend")

        fig, ax = _fig(ctx, "single")
        x = np.arange(len(plot_metrics))
        w = 0.35
        open_vals = [comp.loc[comp["Status"] == "Open", m].values[0] for m in plot_metrics]
        closed_vals = [comp.loc[comp["Status"] == "Closed", m].values[0] for m in plot_metrics]
        b1 = ax.bar(
            x - w / 2,
            open_vals,
            w,
            label="Open",
            color=POSITIVE,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        b2 = ax.bar(
            x + w / 2,
            closed_vals,
            w,
            label="Closed",
            color=NEGATIVE,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for bars in [b1, b2]:
            for bar in bars:
                h = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h,
                    f"${h:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=DATA_LABEL_SIZE,
                    fontweight="bold",
                )
        ax.set_xticks(x)
        ax.set_xticklabels(plot_metrics, fontsize=TICK_SIZE)
        ax.set_title(
            "Open vs Closed Account Comparison", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.legend(fontsize=LEGEND_SIZE)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"${v:,.0f}"))
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_3_open_vs_closed.png")
        fig = None

        _save(ctx, comp, "ATTR-3-Comparison", "A9.3 Open vs Closed Comparison")

        _slide(
            ctx,
            "A9.3 - Open vs Closed",
            {
                "title": "Open vs Closed Account Comparison",
                "subtitle": (
                    f"Open: {len(open_accts):,} accounts | Closed: {len(closed):,} accounts"
                ),
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_3"] = {"comparison": comp}
        _report(ctx, "   A9.3 complete")
    except Exception as e:
        _report(ctx, f"   A9.3 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.4 -- Attrition by Branch
# =============================================================================


def run_attrition_4(ctx):
    """A9.4: Attrition rates by branch."""
    _report(ctx, "\n   A9 -- 4 -- Attrition by Branch")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty or "Branch" not in all_data.columns:
            _report(ctx, "   Skipping A9.4 -- no closed accounts or no Branch column")
            return ctx

        # Apply branch mapping
        bmap = ctx.get("config", {}).get("BranchMapping", {})
        if bmap:
            all_data = all_data.copy()
            all_data["Branch"] = all_data["Branch"].astype(str).map(lambda b: bmap.get(b, b))
            closed = closed.copy()
            closed["Branch"] = closed["Branch"].astype(str).map(lambda b: bmap.get(b, b))

        total_by_branch = all_data.groupby("Branch").size()
        closed_by_branch = closed.groupby("Branch").size()
        branch_df = (
            pd.DataFrame(
                {
                    "Total": total_by_branch,
                    "Closed": closed_by_branch,
                }
            )
            .fillna(0)
            .astype(int)
        )
        branch_df["Open"] = branch_df["Total"] - branch_df["Closed"]
        branch_df["Attrition Rate"] = branch_df["Closed"] / branch_df["Total"]
        branch_df = branch_df.sort_values("Attrition Rate", ascending=True)
        branch_df = branch_df.reset_index()

        # Filter to branches with meaningful sample (30+)
        branch_plot = branch_df[branch_df["Total"] >= 30].copy()
        if branch_plot.empty:
            branch_plot = branch_df.copy()

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        ax.barh(
            branch_plot["Branch"].astype(str),
            branch_plot["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        overall_rate = branch_df["Closed"].sum() / branch_df["Total"].sum()
        ax.axvline(
            overall_rate * 100, color=NEGATIVE, ls="--", lw=2, label=f"Average: {overall_rate:.1%}"
        )
        for i, (rate, ct) in enumerate(zip(branch_plot["Attrition Rate"], branch_plot["Total"])):
            ax.text(
                rate * 100 + 0.5,
                i,
                f"{rate:.1%} (n={ct:,})",
                va="center",
                fontsize=DATA_LABEL_SIZE - 4,
            )
        ax.set_title("Attrition Rate by Branch", fontsize=TITLE_SIZE, fontweight="bold", pad=15)
        ax.set_xlabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.xaxis.set_major_formatter(PCT_FORMATTER)
        ax.legend(fontsize=LEGEND_SIZE)
        ax.tick_params(labelsize=TICK_SIZE - 2)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_4_branch_attrition.png")
        fig = None

        _save(
            ctx,
            branch_df,
            "ATTR-4-Branch",
            "A9.4 Attrition by Branch",
            metrics={
                "Branches": len(branch_df),
                "Highest": f"{branch_df.iloc[-1]['Branch']}: "
                f"{branch_df.iloc[-1]['Attrition Rate']:.1%}",
            },
        )

        _slide(
            ctx,
            "A9.4 - Attrition by Branch",
            {
                "title": "Attrition Rate by Branch",
                "subtitle": f"{len(branch_df)} branches analyzed",
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_4"] = {"branch": branch_df}
        _report(ctx, f"   A9.4 complete -- {len(branch_df)} branches")
    except Exception as e:
        _report(ctx, f"   A9.4 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.5 -- Attrition by Product Code
# =============================================================================


def run_attrition_5(ctx):
    """A9.5: Attrition rates by product code."""
    _report(ctx, "\n   A9 -- 5 -- Attrition by Product Code")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty or "Prod Code" not in all_data.columns:
            _report(ctx, "   Skipping A9.5")
            return ctx

        total_by_prod = all_data.groupby("Prod Code").size()
        closed_by_prod = closed.groupby("Prod Code").size()
        prod_df = (
            pd.DataFrame(
                {
                    "Total": total_by_prod,
                    "Closed": closed_by_prod,
                }
            )
            .fillna(0)
            .astype(int)
        )
        prod_df["Attrition Rate"] = prod_df["Closed"] / prod_df["Total"]
        prod_df = prod_df.sort_values("Total", ascending=False).head(10)
        prod_df = prod_df.reset_index()

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        x = np.arange(len(prod_df))
        ax.bar(x, prod_df["Attrition Rate"] * 100, color=TEAL, edgecolor=BAR_EDGE, alpha=BAR_ALPHA)
        for i, (rate, ct) in enumerate(zip(prod_df["Attrition Rate"], prod_df["Total"])):
            ax.text(
                i,
                rate * 100 + 0.5,
                f"{rate:.1%}",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_xticks(x)
        ax.set_xticklabels(
            prod_df["Prod Code"].astype(str), fontsize=TICK_SIZE - 2, rotation=45, ha="right"
        )
        ax.set_title(
            "Attrition Rate by Product Code (Top 10)",
            fontsize=TITLE_SIZE,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_5_product_attrition.png")
        fig = None

        _save(ctx, prod_df, "ATTR-5-Product", "A9.5 Attrition by Product")

        _slide(
            ctx,
            "A9.5 - Attrition by Product",
            {
                "title": "Attrition by Product Code",
                "subtitle": f"Top {len(prod_df)} product codes by volume",
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_5"] = {"product": prod_df}
        _report(ctx, f"   A9.5 complete -- {len(prod_df)} product codes")
    except Exception as e:
        _report(ctx, f"   A9.5 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.6 -- Personal vs Business Attrition
# =============================================================================


def run_attrition_6(ctx):
    """A9.6: Attrition split by personal vs business accounts."""
    _report(ctx, "\n   A9 -- 6 -- Personal vs Business Attrition")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty or "Business?" not in all_data.columns:
            _report(ctx, "   Skipping A9.6")
            return ctx

        rows = []
        for btype in ["No", "Yes"]:
            label = "Personal" if btype == "No" else "Business"
            total = len(all_data[all_data["Business?"] == btype])
            n_closed = len(closed[closed["Business?"] == btype])
            rate = n_closed / total if total > 0 else 0
            rows.append(
                {
                    "Type": label,
                    "Total": total,
                    "Closed": n_closed,
                    "Open": total - n_closed,
                    "Attrition Rate": rate,
                }
            )
        pb_df = pd.DataFrame(rows)

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        colors = [PERSONAL, BUSINESS]
        bars = ax.bar(
            pb_df["Type"],
            pb_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, pb_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._5:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition: Personal vs Business", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_6_personal_business.png")
        fig = None

        _save(ctx, pb_df, "ATTR-6-PB", "A9.6 Personal vs Business Attrition")

        _slide(
            ctx,
            "A9.6 - Personal vs Business",
            {
                "title": "Personal vs Business Attrition",
                "subtitle": (
                    f"Personal: {pb_df.iloc[0]['Attrition Rate']:.1%} | "
                    f"Business: {pb_df.iloc[1]['Attrition Rate']:.1%}"
                ),
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_6"] = {"personal_business": pb_df}
        _report(ctx, "   A9.6 complete")
    except Exception as e:
        _report(ctx, f"   A9.6 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.7 -- Attrition by Account Tenure
# =============================================================================


def run_attrition_7(ctx):
    """A9.7: Do newer accounts close faster than established ones?"""
    _report(ctx, "\n   A9 -- 7 -- Attrition by Tenure")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   Skipping A9.7")
            return ctx

        now = pd.Timestamp.now()
        all_copy = all_data.copy()
        all_copy["_tenure_days"] = (now - all_copy["Date Opened"]).dt.days
        all_copy["_tenure_cat"] = all_copy["_tenure_days"].apply(categorize_tenure)

        closed_copy = closed.copy()
        closed_copy["_tenure_days"] = (
            closed_copy["Date Closed"] - closed_copy["Date Opened"]
        ).dt.days
        closed_copy["_tenure_cat"] = closed_copy["_tenure_days"].apply(categorize_tenure)

        total_by_tenure = all_copy.groupby("_tenure_cat").size()
        closed_by_tenure = closed_copy.groupby("_tenure_cat").size()
        tenure_df = (
            pd.DataFrame(
                {
                    "Total": total_by_tenure,
                    "Closed": closed_by_tenure,
                }
            )
            .fillna(0)
            .astype(int)
        )
        tenure_df["Attrition Rate"] = tenure_df["Closed"] / tenure_df["Total"]
        tenure_df.index = pd.CategoricalIndex(
            tenure_df.index, categories=TENURE_ORDER, ordered=True
        )
        tenure_df = tenure_df.sort_index().reset_index()
        tenure_df.columns = ["Tenure", "Total", "Closed", "Attrition Rate"]

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        ax.bar(
            tenure_df["Tenure"].astype(str),
            tenure_df["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, (rate, ct) in enumerate(zip(tenure_df["Attrition Rate"], tenure_df["Total"])):
            ax.text(
                i,
                rate * 100 + 0.5,
                f"{rate:.1%}",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition Rate by Account Tenure", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE - 2)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_7_tenure_attrition.png")
        fig = None

        _save(ctx, tenure_df, "ATTR-7-Tenure", "A9.7 Attrition by Tenure")

        _slide(
            ctx,
            "A9.7 - Attrition by Tenure",
            {
                "title": "Attrition Rate by Account Tenure",
                "subtitle": "Newer accounts typically show higher closure rates",
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_7"] = {"tenure": tenure_df}
        _report(ctx, "   A9.7 complete")
    except Exception as e:
        _report(ctx, f"   A9.7 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.8 -- Attrition by Balance Tier
# =============================================================================


def run_attrition_8(ctx):
    """A9.8: Attrition rates across balance tiers."""
    _report(ctx, "\n   A9 -- 8 -- Attrition by Balance Tier")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty or "Avg Bal" not in all_data.columns:
            _report(ctx, "   Skipping A9.8")
            return ctx

        all_copy = all_data.copy()
        all_copy["_bal_cat"] = all_copy["Avg Bal"].apply(categorize_balance)
        closed_copy = closed.copy()
        closed_copy["_bal_cat"] = closed_copy["Avg Bal"].apply(categorize_balance)

        total_by_bal = all_copy.groupby("_bal_cat").size()
        closed_by_bal = closed_copy.groupby("_bal_cat").size()
        bal_df = (
            pd.DataFrame(
                {
                    "Total": total_by_bal,
                    "Closed": closed_by_bal,
                }
            )
            .fillna(0)
            .astype(int)
        )
        bal_df["Attrition Rate"] = bal_df["Closed"] / bal_df["Total"]
        bal_df.index = pd.CategoricalIndex(bal_df.index, categories=BALANCE_ORDER, ordered=True)
        bal_df = bal_df.sort_index().reset_index()
        bal_df.columns = ["Balance Tier", "Total", "Closed", "Attrition Rate"]

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        ax.bar(
            bal_df["Balance Tier"].astype(str),
            bal_df["Attrition Rate"] * 100,
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, (rate, ct) in enumerate(zip(bal_df["Attrition Rate"], bal_df["Total"])):
            ax.text(
                i,
                rate * 100 + 0.5,
                f"{rate:.1%}",
                ha="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition Rate by Balance Tier", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE - 4)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_8_balance_attrition.png")
        fig = None

        _save(ctx, bal_df, "ATTR-8-Balance", "A9.8 Attrition by Balance Tier")

        _slide(
            ctx,
            "A9.8 - Attrition by Balance",
            {
                "title": "Attrition Rate by Balance Tier",
                "subtitle": "Lower-balance accounts tend to attrite at higher rates",
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_8"] = {"balance": bal_df}
        _report(ctx, "   A9.8 complete")
    except Exception as e:
        _report(ctx, f"   A9.8 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.9 -- Debit Card Retention Effect (Hero Slide)
# =============================================================================


def run_attrition_9(ctx):
    """A9.9: Do accounts with debit cards close less often?"""
    _report(ctx, "\n   A9 -- 9 -- Debit Card Retention Effect")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty or "Debit?" not in all_data.columns:
            _report(ctx, "   Skipping A9.9")
            return ctx

        rows = []
        for debit_val, label in [("Yes", "With Debit Card"), ("No", "Without Debit Card")]:
            total = len(all_data[all_data["Debit?"] == debit_val])
            n_closed = len(closed[closed["Debit?"] == debit_val])
            rate = n_closed / total if total > 0 else 0
            rows.append(
                {
                    "Debit Status": label,
                    "Total": total,
                    "Closed": n_closed,
                    "Open": total - n_closed,
                    "Attrition Rate": rate,
                }
            )
        debit_df = pd.DataFrame(rows)

        with_rate = debit_df.iloc[0]["Attrition Rate"]
        without_rate = debit_df.iloc[1]["Attrition Rate"]
        retention_lift = without_rate - with_rate

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        colors = [POSITIVE, NEGATIVE]
        bars = ax.bar(
            debit_df["Debit Status"],
            debit_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, debit_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._5:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Debit Card Impact on Account Retention", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE)

        # Annotation for retention lift
        if retention_lift > 0:
            ax.annotate(
                f"{retention_lift:.1%} lower attrition\nwith debit cards",
                xy=(0, with_rate * 100),
                fontsize=ANNOTATION_SIZE,
                xytext=(0.5, (with_rate + without_rate) / 2 * 100),
                ha="center",
                fontweight="bold",
                color=POSITIVE,
                arrowprops=dict(arrowstyle="->", color=POSITIVE, lw=2),
            )
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_9_debit_retention.png")
        fig = None

        _save(
            ctx,
            debit_df,
            "ATTR-9-Debit",
            "A9.9 Debit Card Retention",
            metrics={
                "With Debit": f"{with_rate:.1%}",
                "Without Debit": f"{without_rate:.1%}",
                "Retention Lift": f"{retention_lift:.1%}",
            },
        )

        if retention_lift > 0:
            subtitle = f"Accounts with debit cards show {retention_lift:.1%} lower attrition"
        else:
            subtitle = "Attrition rates by debit card status"

        insight = {
            "title": "Debit Card Impact on Retention",
            "subtitle": subtitle,
            "slide_type": "screenshot_kpi",
            "layout_index": 5,
            "kpis": {
                "With Debit": f"{with_rate:.1%}",
                "Without": f"{without_rate:.1%}",
            },
            "chart_path": chart_path,
            "category": "Attrition",
        }
        _slide(ctx, "A9.9 - Debit Card Retention", insight)
        ctx["results"]["attrition_9"] = {"debit": debit_df, "retention_lift": retention_lift}
        _report(ctx, f"   A9.9 complete -- lift: {retention_lift:.1%}")
    except Exception as e:
        _report(ctx, f"   A9.9 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.10 -- Mailer Program Retention Effect (Hero Slide)
# =============================================================================


def run_attrition_10(ctx):
    """A9.10: Do mailed/responding accounts close less often?"""
    _report(ctx, "\n   A9 -- 10 -- Mailer Retention Effect")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   Skipping A9.10")
            return ctx

        # Discover mailer columns
        mail_cols = [c for c in all_data.columns if re.match(r"^[A-Z][a-z]{2}\d{2}\s+Mail$", c)]
        resp_cols = [c for c in all_data.columns if re.match(r"^[A-Z][a-z]{2}\d{2}\s+Resp$", c)]

        if not mail_cols:
            _report(ctx, "   No mailer columns found -- skipping A9.10")
            return ctx

        # Classify: ever mailed, ever responded, never mailed
        all_copy = all_data.copy()
        all_copy["_ever_mailed"] = all_copy[mail_cols].notna().any(axis=1)
        if resp_cols:
            all_copy["_ever_responded"] = all_copy[resp_cols].notna().any(axis=1)
        else:
            all_copy["_ever_responded"] = False

        def _classify(row):
            if row["_ever_responded"]:
                return "Responded"
            if row["_ever_mailed"]:
                return "Mailed (No Response)"
            return "Never Mailed"

        all_copy["_mail_group"] = all_copy.apply(_classify, axis=1)

        rows = []
        group_order = ["Responded", "Mailed (No Response)", "Never Mailed"]
        for grp in group_order:
            subset = all_copy[all_copy["_mail_group"] == grp]
            total = len(subset)
            n_closed = subset["Date Closed"].notna().sum()
            rate = n_closed / total if total > 0 else 0
            rows.append(
                {"Group": grp, "Total": total, "Closed": int(n_closed), "Attrition Rate": rate}
            )
        mail_df = pd.DataFrame(rows)

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        colors = [POSITIVE, TTM, NEUTRAL]
        bars = ax.bar(
            mail_df["Group"],
            mail_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, mail_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Mailer Program Impact on Retention", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_10_mailer_retention.png")
        fig = None

        _save(ctx, mail_df, "ATTR-10-Mailer", "A9.10 Mailer Retention")

        resp_rate = mail_df.iloc[0]["Attrition Rate"]
        never_rate = mail_df.iloc[2]["Attrition Rate"]
        lift = never_rate - resp_rate

        if lift > 0:
            subtitle = (
                f"Mailer responders show {lift:.1%} lower attrition than never-mailed accounts"
            )
        else:
            subtitle = "Attrition rates by mailer program participation"

        insight = {
            "title": "Mailer Program Impact on Retention",
            "subtitle": subtitle,
            "slide_type": "screenshot_kpi",
            "layout_index": 5,
            "kpis": {
                "Responders": f"{resp_rate:.1%}",
                "Never Mailed": f"{never_rate:.1%}",
            },
            "chart_path": chart_path,
            "category": "Attrition",
        }
        _slide(ctx, "A9.10 - Mailer Retention", insight)
        ctx["results"]["attrition_10"] = {"mailer": mail_df, "lift": lift}
        _report(ctx, f"   A9.10 complete -- lift: {lift:.1%}")
    except Exception as e:
        _report(ctx, f"   A9.10 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.11 -- Revenue Impact of Attrition
# =============================================================================


def run_attrition_11(ctx):
    """A9.11: What revenue is lost from closed accounts?"""
    _report(ctx, "\n   A9 -- 11 -- Revenue Impact of Attrition")
    fig = None
    try:
        _, _, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   Skipping A9.11")
            return ctx

        nsf_fee = ctx.get("nsf_od_fee", 30)
        ic_rate = ctx.get("ic_rate", 0.007)

        # Find last non-zero spend/items for each closed account
        spend_cols = sorted([c for c in closed.columns if c.endswith(" Spend")])
        items_cols = sorted([c for c in closed.columns if "Items" in c or "NSF" in c])

        closed_copy = closed.copy()
        if spend_cols:
            closed_copy["_last_spend"] = (
                closed_copy[spend_cols].replace(0, np.nan).ffill(axis=1).iloc[:, -1].fillna(0)
            )
        else:
            closed_copy["_last_spend"] = 0

        if items_cols:
            closed_copy["_last_items"] = (
                closed_copy[items_cols].replace(0, np.nan).ffill(axis=1).iloc[:, -1].fillna(0)
            )
        else:
            closed_copy["_last_items"] = 0

        closed_copy["_est_annual_revenue"] = (
            closed_copy["_last_spend"] * ic_rate * 12 + closed_copy["_last_items"] * nsf_fee * 12
        )

        total_lost = closed_copy["_est_annual_revenue"].sum()
        avg_lost = closed_copy["_est_annual_revenue"].mean()
        n_closed = len(closed_copy)

        summary = pd.DataFrame(
            [
                {"Metric": "Closed Accounts", "Value": f"{n_closed:,}"},
                {"Metric": "Est. Annual Revenue Lost", "Value": f"${total_lost:,.0f}"},
                {"Metric": "Avg Revenue per Closed Acct", "Value": f"${avg_lost:,.2f}"},
                {"Metric": "NSF/OD Fee Used", "Value": f"${nsf_fee:.2f}"},
                {"Metric": "IC Rate Used", "Value": f"{ic_rate:.4f}"},
            ]
        )

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None

        # Revenue distribution of closed accounts
        bins = [0, 50, 100, 250, 500, 1000, float("inf")]
        labels = ["$0-$50", "$50-$100", "$100-$250", "$250-$500", "$500-$1K", "$1K+"]
        closed_copy["_rev_bin"] = pd.cut(
            closed_copy["_est_annual_revenue"], bins=bins, labels=labels, include_lowest=True
        )
        rev_dist = (
            closed_copy.groupby("_rev_bin", observed=True)
            .agg(Count=("_rev_bin", "size"), Total_Revenue=("_est_annual_revenue", "sum"))
            .reset_index()
        )

        fig, ax = _fig(ctx, "single")
        ax.bar(
            rev_dist["_rev_bin"].astype(str),
            rev_dist["Total_Revenue"],
            color=NEGATIVE,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
        )
        for i, (rev, ct) in enumerate(zip(rev_dist["Total_Revenue"], rev_dist["Count"])):
            ax.text(
                i,
                rev + total_lost * 0.02,
                f"${rev:,.0f}\n({ct:,} accts)",
                ha="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )
        ax.set_title(
            "Estimated Annual Revenue Lost by Tier", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Revenue Lost ($)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"${v:,.0f}"))
        ax.tick_params(labelsize=TICK_SIZE - 2)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_11_revenue_impact.png")
        fig = None

        _save(
            ctx,
            summary,
            "ATTR-11-Revenue",
            "A9.11 Revenue Impact",
            metrics={"Annual Revenue Lost": f"${total_lost:,.0f}"},
        )

        insight = {
            "title": "Revenue Impact of Account Closures",
            "subtitle": (
                f"Est. ${total_lost:,.0f} in annual revenue lost from {n_closed:,} closed accounts"
            ),
            "slide_type": "screenshot_kpi",
            "layout_index": 5,
            "kpis": {
                "Revenue Lost": f"${total_lost:,.0f}",
                "Per Account": f"${avg_lost:,.0f}",
            },
            "chart_path": chart_path,
            "category": "Attrition",
        }
        _slide(ctx, "A9.11 - Revenue Impact", insight)
        ctx["results"]["attrition_11"] = {"total_lost": total_lost, "avg_lost": avg_lost}
        _report(ctx, f"   A9.11 complete -- ${total_lost:,.0f} est. annual loss")
    except Exception as e:
        _report(ctx, f"   A9.11 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.12 -- Attrition Velocity (L12M Monthly Trend)
# =============================================================================


def run_attrition_12(ctx):
    """A9.12: Monthly closure trend over L12M with moving average."""
    _report(ctx, "\n   A9 -- 12 -- Attrition Velocity")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   Skipping A9.12")
            return ctx

        sd, ed = ctx.get("start_date"), ctx.get("end_date")
        if not sd or not ed:
            _report(ctx, "   No date range -- skipping A9.12")
            return ctx

        l12m_closed = closed[(closed["Date Closed"] >= sd) & (closed["Date Closed"] <= ed)].copy()

        if l12m_closed.empty:
            _report(ctx, "   No L12M closures -- skipping A9.12")
            return ctx

        l12m_closed["_close_month"] = l12m_closed["Date Closed"].dt.to_period("M")
        monthly = l12m_closed.groupby("_close_month").size().reset_index(name="Closures")
        monthly["Month"] = monthly["_close_month"].dt.to_timestamp()
        monthly = monthly.sort_values("Month")

        # 3-month moving average
        if len(monthly) >= 3:
            monthly["MA3"] = monthly["Closures"].rolling(3, min_periods=1).mean()
        else:
            monthly["MA3"] = monthly["Closures"]

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        month_labels = monthly["Month"].dt.strftime("%b %y")
        x = np.arange(len(monthly))
        ax.bar(
            x,
            monthly["Closures"],
            color=TEAL,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            label="Monthly Closures",
        )
        ax.plot(
            x,
            monthly["MA3"],
            color=NEGATIVE,
            linewidth=3,
            marker="o",
            markersize=8,
            label="3-Mo Avg",
        )
        for i, c in enumerate(monthly["Closures"]):
            ax.text(
                i,
                c + monthly["Closures"].max() * 0.03,
                str(int(c)),
                ha="center",
                fontsize=DATA_LABEL_SIZE - 2,
                fontweight="bold",
            )
        ax.set_xticks(x)
        ax.set_xticklabels(month_labels, fontsize=TICK_SIZE - 2, rotation=45, ha="right")
        ax.set_title(
            "Monthly Account Closures (L12M)", fontsize=TITLE_SIZE, fontweight="bold", pad=15
        )
        ax.set_ylabel("Closures", fontsize=AXIS_LABEL_SIZE)
        ax.legend(fontsize=LEGEND_SIZE)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_12_velocity.png")
        fig = None

        export_df = monthly[["Month", "Closures", "MA3"]].copy()
        export_df["Month"] = export_df["Month"].dt.strftime("%Y-%m")
        _save(ctx, export_df, "ATTR-12-Velocity", "A9.12 Attrition Velocity")

        total_l12m = monthly["Closures"].sum()
        trend = ""
        if len(monthly) >= 6:
            first_half = monthly["Closures"].iloc[: len(monthly) // 2].mean()
            second_half = monthly["Closures"].iloc[len(monthly) // 2 :].mean()
            if second_half > first_half * 1.1:
                trend = "increasing"
            elif second_half < first_half * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"

        subtitle = f"{total_l12m:,} closures over L12M"
        if trend:
            subtitle += f" (trend: {trend})"

        insight = {
            "title": "Attrition Velocity -- Monthly Trend",
            "subtitle": subtitle,
            "slide_type": "screenshot_kpi",
            "layout_index": 5,
            "kpis": {
                "L12M Closures": f"{total_l12m:,}",
                "Monthly Avg": f"{total_l12m / len(monthly):,.0f}",
            },
            "chart_path": chart_path,
            "category": "Attrition",
        }
        _slide(ctx, "A9.12 - Attrition Velocity", insight)
        ctx["results"]["attrition_12"] = {
            "monthly": export_df,
            "total_l12m": total_l12m,
            "trend": trend,
        }
        _report(ctx, f"   A9.12 complete -- {total_l12m:,} L12M closures, trend: {trend}")
    except Exception as e:
        _report(ctx, f"   A9.12 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# A9.13 -- ARS-Eligible vs Non-ARS Comparison
# =============================================================================


def run_attrition_13(ctx):
    """A9.13: Compare attrition for ARS-eligible vs non-eligible accounts."""
    _report(ctx, "\n   A9 -- 13 -- ARS vs Non-ARS Comparison")
    fig = None
    try:
        all_data, _, closed = _prepare_attrition_data(ctx)
        if closed.empty:
            _report(ctx, "   Skipping A9.13")
            return ctx

        esc = ctx.get("eligible_stat_code", [])
        epc = ctx.get("eligible_prod_code", [])
        if not esc or not epc:
            _report(ctx, "   No eligibility config -- skipping A9.13")
            return ctx

        all_copy = all_data.copy()
        all_copy["_ars_eligible"] = all_copy["Stat Code"].isin(esc) & all_copy["Prod Code"].isin(
            epc
        )

        rows = []
        for elig, label in [(True, "ARS-Eligible"), (False, "Non-Eligible")]:
            subset = all_copy[all_copy["_ars_eligible"] == elig]
            total = len(subset)
            n_closed = subset["Date Closed"].notna().sum()
            rate = n_closed / total if total > 0 else 0
            rows.append(
                {"Group": label, "Total": total, "Closed": int(n_closed), "Attrition Rate": rate}
            )
        ars_df = pd.DataFrame(rows)

        chart_dir = Path(ctx["chart_dir"])
        chart_path = None
        fig, ax = _fig(ctx, "single")
        colors = [POSITIVE, NEUTRAL]
        bars = ax.bar(
            ars_df["Group"],
            ars_df["Attrition Rate"] * 100,
            color=colors,
            edgecolor=BAR_EDGE,
            alpha=BAR_ALPHA,
            width=0.5,
        )
        for bar, row in zip(bars, ars_df.itertuples()):
            h = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                h + 0.5,
                f"{row._4:.1%}\n({row.Closed:,} / {row.Total:,})",
                ha="center",
                fontsize=DATA_LABEL_SIZE,
                fontweight="bold",
            )
        ax.set_title(
            "Attrition: ARS-Eligible vs Non-Eligible",
            fontsize=TITLE_SIZE,
            fontweight="bold",
            pad=15,
        )
        ax.set_ylabel("Attrition Rate (%)", fontsize=AXIS_LABEL_SIZE)
        ax.yaxis.set_major_formatter(PCT_FORMATTER)
        ax.tick_params(labelsize=TICK_SIZE)
        plt.tight_layout()
        chart_path = _save_chart(fig, chart_dir / "a9_13_ars_comparison.png")
        fig = None

        _save(ctx, ars_df, "ATTR-13-ARS", "A9.13 ARS vs Non-ARS")

        ars_rate = ars_df.iloc[0]["Attrition Rate"]
        non_rate = ars_df.iloc[1]["Attrition Rate"]
        diff = non_rate - ars_rate

        if diff > 0:
            subtitle = f"ARS-eligible accounts show {diff:.1%} lower attrition than non-eligible"
        else:
            subtitle = "Attrition comparison by eligibility status"

        _slide(
            ctx,
            "A9.13 - ARS vs Non-ARS",
            {
                "title": "ARS-Eligible vs Non-Eligible Attrition",
                "subtitle": subtitle,
                "slide_type": "screenshot",
                "layout_index": 4,
                "chart_path": chart_path,
                "category": "Attrition",
            },
        )
        ctx["results"]["attrition_13"] = {"ars": ars_df, "diff": diff}
        _report(ctx, f"   A9.13 complete -- diff: {diff:.1%}")
    except Exception as e:
        _report(ctx, f"   A9.13 failed: {e}")
        traceback.print_exc()
    finally:
        if fig is not None:
            plt.close(fig)
    return ctx


# =============================================================================
# SUITE RUNNER
# =============================================================================


def run_attrition_suite(ctx):
    """Run all A9 attrition sub-analyses. Entry point from pipeline."""
    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "   ATTRITION ANALYSIS SUITE (A9)")
    _report(ctx, "=" * 60)

    from ars_analysis.pipeline import save_to_excel

    ctx["_save_to_excel"] = save_to_excel

    for fn in [
        run_attrition_1,
        run_attrition_2,
        run_attrition_3,
        run_attrition_4,
        run_attrition_5,
        run_attrition_6,
        run_attrition_7,
        run_attrition_8,
        run_attrition_9,
        run_attrition_10,
        run_attrition_11,
        run_attrition_12,
        run_attrition_13,
    ]:
        ctx = fn(ctx)

    _report(ctx, "\n   === ATTRITION SUITE COMPLETE ===")
    return ctx
