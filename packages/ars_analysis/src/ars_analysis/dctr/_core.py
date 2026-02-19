"""Core DCTR analysis functions (run_dctr_1 through run_dctr_16)."""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

from ars_analysis.dctr._categories import (
    categorize_account_age,
    categorize_balance,
    categorize_holder_age,
    simplify_account_age,
)
from ars_analysis.dctr._constants import AGE_ORDER, BALANCE_ORDER, HOLDER_AGE_ORDER
from ars_analysis.dctr._helpers import _dctr, _fig, _report, _save, _save_chart, _slide
from ars_analysis.dctr._shared import (
    _branch_dctr,
    _by_dimension,
    _crosstab,
    _l12m_monthly,
    analyze_historical_dctr,
)


def _draw_crosstab_heatmap(pivot_df, chart_dir, filename, title, xlabel, ylabel):
    """Render a DCTR cross-tab pivot as a red-yellow-green heatmap chart."""
    from pathlib import Path

    if pivot_df.empty:
        return
    data = pivot_df.values.astype(float)
    data = np.where(np.isnan(data), 0, data)

    n_rows, n_cols = data.shape
    fig_w = max(10, n_cols * 1.8 + 3)
    fig_h = max(6, n_rows * 0.7 + 2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    try:
        cmap = LinearSegmentedColormap.from_list(
            "dctr_xtab", ["#E74C3C", "#F39C12", "#F1C40F", "#2ECC71", "#27AE60"]
        )
        valid_vals = data[data > 0]
        vmin = valid_vals.min() if len(valid_vals) else 0
        vmax = valid_vals.max() if len(valid_vals) else 1

        im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)

        ax.set_xticks(range(n_cols))
        ax.set_xticklabels(pivot_df.columns, rotation=45, ha="right", fontsize=12)
        ax.set_yticks(range(n_rows))
        ax.set_yticklabels(pivot_df.index, fontsize=12)

        # Annotate cells
        for i in range(n_rows):
            for j in range(n_cols):
                val = data[i, j]
                text = f"{val:.0%}" if val > 0 else "N/A"
                color = "white" if val < (vmin + vmax) / 2 else "black"
                ax.text(j, i, text, ha="center", va="center", fontsize=10, color=color)

        ax.set_xlabel(xlabel, fontsize=14, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=14, fontweight="bold")
        ax.set_title(title, fontsize=16, fontweight="bold", pad=15)
        fig.colorbar(im, ax=ax, shrink=0.8, label="DCTR %")
        plt.tight_layout()

        _save_chart(fig, Path(chart_dir) / filename)
    finally:
        plt.close(fig)


def run_dctr_1(ctx):
    _report(ctx, "\n📅 DCTR-1 — Historical DCTR (Eligible)")
    yearly, decade, ins = analyze_historical_dctr(ctx["eligible_data"], "Eligible")
    _save(
        ctx,
        {"Yearly": yearly, "Decade": decade},
        "DCTR-1-Historical",
        "Historical Debit Card Take Rate",
        {
            "Overall DCTR": f"{ins['overall_dctr']:.1%}",
            "Accounts": f"{ins['total_accounts']:,}",
            "With Debit": f"{ins['with_debit_count']:,}",
            "Recent DCTR": f"{ins['recent_dctr']:.1%}",
        },
    )
    ctx["results"]["dctr_1"] = {"yearly": yearly, "decade": decade, "insights": ins}
    _report(ctx, f"   Overall: {ins['overall_dctr']:.1%} | Recent: {ins['recent_dctr']:.1%}")
    return ctx


def run_dctr_2(ctx):
    _report(ctx, "\n📊 DCTR-2 — Open vs Eligible Comparison")
    oa = ctx["open_accounts"]
    ed = ctx["eligible_data"]
    open_yearly, open_decade, open_ins = analyze_historical_dctr(oa, "Open")
    hist_ins = ctx["results"]["dctr_1"]["insights"]

    comparison = pd.DataFrame(
        [
            {
                "Account Group": "All Open",
                "Total Accounts": len(oa),
                "With Debit": open_ins["with_debit_count"],
                "DCTR %": open_ins["overall_dctr"],
            },
            {
                "Account Group": "Eligible Only",
                "Total Accounts": hist_ins["total_accounts"],
                "With Debit": hist_ins["with_debit_count"],
                "DCTR %": hist_ins["overall_dctr"],
            },
        ]
    )
    diff = hist_ins["overall_dctr"] - open_ins["overall_dctr"]

    _save(
        ctx,
        {"Comparison": comparison, "Open-Yearly": open_yearly, "Open-Decade": open_decade},
        "DCTR-2-OpenVsEligible",
        "DCTR: Open vs Eligible",
        {
            "Open DCTR": f"{open_ins['overall_dctr']:.1%}",
            "Eligible DCTR": f"{hist_ins['overall_dctr']:.1%}",
            "Difference": f"{diff:+.1%}",
        },
    )

    # Chart A7.1
    try:
        chart_dir = ctx["chart_dir"]
        fig, ax = _fig(ctx, "half")
        od, ed_v = open_ins["overall_dctr"] * 100, hist_ins["overall_dctr"] * 100
        bars = ax.bar(
            ["All Open\n(incl. Ineligible)", "Eligible Only\n(Debit Qualified)"],
            [od, ed_v],
            color=["#70AD47", "#4472C4"],
            width=0.5,
            edgecolor="black",
            linewidth=2,
            alpha=0.8,
        )
        for bar, v, c in zip(
            bars, [od, ed_v], [open_ins["with_debit_count"], hist_ins["with_debit_count"]]
        ):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1,
                f"{v:.1f}%",
                ha="center",
                fontweight="bold",
                fontsize=22,
            )
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v / 2,
                f"{c:,}\naccounts",
                ha="center",
                fontweight="bold",
                fontsize=18,
                color="white",
            )
        ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
        ax.set_title("DCTR by Eligibility", fontsize=24, fontweight="bold", pad=20)
        ax.set_ylim(0, max(od, ed_v) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
        ax.tick_params(axis="both", labelsize=18)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        color = "green" if diff > 0 else "red"
        ax.text(
            0.5,
            0.5,
            f"{'↑' if diff > 0 else '↓'} {abs(diff * 100):.1f}%\nimprovement",
            transform=ax.transAxes,
            ha="center",
            fontsize=20,
            fontweight="bold",
            color=color,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=color, linewidth=2),
        )
        ax.grid(False)
        ax.set_axisbelow(True)
        plt.tight_layout()
        cp = _save_chart(fig, chart_dir / "dctr_open_vs_eligible.png")
        ctx["results"]["dctr_2_chart"] = cp
    except Exception as e:
        cp = None
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx["results"]["dctr_2"] = {
        "comparison": comparison,
        "insights": {
            "open_dctr": open_ins["overall_dctr"],
            "eligible_dctr": hist_ins["overall_dctr"],
            "difference": diff,
            "open_total": len(oa),
            "eligible_total": hist_ins["total_accounts"],
        },
    }
    _report(
        ctx,
        f"   Open: {open_ins['overall_dctr']:.1%} | Eligible: {hist_ins['overall_dctr']:.1%} | Δ {diff:+.1%}",
    )
    return ctx


def run_dctr_3(ctx):
    _report(ctx, "\n📅 DCTR-3 — Last 12 Months")
    el12 = ctx["eligible_last_12m"]
    l12m = ctx["last_12_months"]
    sd, ed = ctx["start_date"], ctx["end_date"]

    if el12 is None or el12.empty:
        ctx["results"]["dctr_3"] = {"insights": {"total_accounts": 0, "dctr": 0}}
        _report(ctx, "   ⚠️ No L12M data")
        return ctx

    # Filter to exact date range
    el12f = el12[
        (pd.to_datetime(el12["Date Opened"], errors="coerce") >= sd)
        & (pd.to_datetime(el12["Date Opened"], errors="coerce") <= ed)
    ].copy()

    monthly, l12m_ins = _l12m_monthly(el12f, l12m)
    yearly, decade, yins = analyze_historical_dctr(el12f, "L12M")

    overall = ctx["results"]["dctr_1"]["insights"]["overall_dctr"]
    comp = l12m_ins["dctr"] - overall

    _save(
        ctx,
        {"Monthly": monthly, "Yearly": yearly},
        "DCTR-3-L12M",
        "Last 12 Months DCTR",
        {
            "L12M DCTR": f"{l12m_ins['dctr']:.1%}",
            "vs Overall": f"{comp:+.1%}",
            "Accounts": f"{l12m_ins['total_accounts']:,}",
            "Period": f"{sd.strftime('%b %Y')} - {ed.strftime('%b %Y')}",
        },
    )

    # Chart A7.3: Historical vs L12M
    try:
        chart_dir = ctx["chart_dir"]
        fig, ax = _fig(ctx, "half")
        hd = overall * 100
        ld = l12m_ins["dctr"] * 100
        ht = ctx["results"]["dctr_1"]["insights"]["total_accounts"]
        lt = l12m_ins["total_accounts"]
        bars = ax.bar(
            ["All-Time\n(Cumulative)", "Last 12 Months\n(Recent)"],
            [hd, ld],
            color=["#5B9BD5", "#FFC000"],
            width=0.5,
            edgecolor="black",
            linewidth=2,
            alpha=0.8,
        )
        for bar, v, c in zip(bars, [hd, ld], [ht, lt]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1,
                f"{v:.1f}%",
                ha="center",
                fontweight="bold",
                fontsize=22,
            )
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v / 2,
                f"{c:,}\naccounts",
                ha="center",
                fontweight="bold",
                fontsize=18,
                color="white",
            )
        ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
        ax.set_title("DCTR by Time Period", fontsize=24, fontweight="bold", pad=20)
        ax.set_ylim(0, max(hd, ld) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
        ax.tick_params(axis="both", labelsize=18)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        t = comp * 100
        tc = "green" if t > 0 else "red" if t < 0 else "gray"
        ax.text(
            0.5,
            0.5,
            f"{'↑' if t > 0 else '↓'} {abs(t):.1f}%",
            transform=ax.transAxes,
            ha="center",
            fontsize=20,
            fontweight="bold",
            color=tc,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor=tc, linewidth=2),
        )
        ax.grid(False)
        ax.set_axisbelow(True)
        plt.tight_layout()
        cp3 = _save_chart(fig, chart_dir / "dctr_hist_vs_l12m.png")
        ctx["results"]["dctr_3_chart"] = cp3
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    l12m_ins["comparison_to_overall"] = comp
    ctx["results"]["dctr_3"] = {"monthly": monthly, "yearly": yearly, "insights": l12m_ins}
    _report(
        ctx,
        f"   L12M: {l12m_ins['dctr']:.1%} ({l12m_ins['total_accounts']:,} accts) | vs Overall: {comp:+.1%}",
    )
    return ctx


def run_dctr_4_5(ctx):
    _report(ctx, "\n👤 DCTR-4/5 — Personal & Business Historical")
    ep = ctx["eligible_personal"]
    eb = ctx["eligible_business"]

    p_yr, p_dec, p_ins = analyze_historical_dctr(ep, "Personal")
    _save(
        ctx,
        {"Yearly": p_yr, "Decade": p_dec},
        "DCTR-4-Personal",
        "Personal DCTR",
        {"Personal DCTR": f"{p_ins.get('overall_dctr', 0):.1%}", "Count": f"{len(ep):,}"},
    )

    has_biz = len(eb) > 0
    if has_biz:
        b_yr, b_dec, b_ins = analyze_historical_dctr(eb, "Business")
        _save(
            ctx,
            {"Yearly": b_yr, "Decade": b_dec},
            "DCTR-5-Business",
            "Business DCTR",
            {"Business DCTR": f"{b_ins.get('overall_dctr', 0):.1%}", "Count": f"{len(eb):,}"},
        )
    else:
        b_yr, b_dec, b_ins = (
            pd.DataFrame(),
            pd.DataFrame(),
            {"total_accounts": 0, "overall_dctr": 0, "with_debit_count": 0},
        )

    # Chart A7.2: Personal vs Business bar
    try:
        chart_dir = ctx["chart_dir"]
        overall = ctx["results"]["dctr_1"]["insights"]["overall_dctr"] * 100
        fig, ax = _fig(ctx, "single")

        if has_biz:
            cats = ["Personal", "Business"]
            vals = [p_ins["overall_dctr"] * 100, b_ins["overall_dctr"] * 100]
            colors = ["#4472C4", "#ED7D31"]
            cts = [p_ins["with_debit_count"], b_ins["with_debit_count"]]
        else:
            cats = ["Personal"]
            vals = [p_ins["overall_dctr"] * 100]
            colors = ["#4472C4"]
            cts = [p_ins["with_debit_count"]]

        bars = ax.bar(
            cats, vals, color=colors, edgecolor="black", linewidth=2, alpha=0.9, width=0.5
        )
        for bar, v, c in zip(bars, vals, cts):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v + 1,
                f"{v:.1f}%",
                ha="center",
                fontweight="bold",
                fontsize=22,
            )
            if v > 10:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    v / 2,
                    f"{c:,}\naccts",
                    ha="center",
                    fontsize=18,
                    fontweight="bold",
                    color="white",
                )
        ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
        ax.set_title("Personal vs Business DCTR", fontsize=24, fontweight="bold", pad=20)
        ax.set_ylim(0, max(vals) * 1.15)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
        ax.tick_params(axis="both", labelsize=18)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", alpha=0.3, linestyle="--")
        ax.set_axisbelow(True)
        ax.text(
            0.02,
            0.98,
            f"Overall: {overall:.1f}%",
            transform=ax.transAxes,
            fontsize=18,
            va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#eee", alpha=0.8),
        )
        plt.tight_layout()
        _save_chart(fig, chart_dir / "dctr_personal_vs_business.png")
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx["results"]["dctr_4"] = {"yearly": p_yr, "decade": p_dec, "insights": p_ins}
    ctx["results"]["dctr_5"] = {"yearly": b_yr, "decade": b_dec, "insights": b_ins}
    _report(
        ctx,
        f"   Personal: {p_ins.get('overall_dctr', 0):.1%} | Business: {b_ins.get('overall_dctr', 0):.1%}",
    )
    return ctx


def run_dctr_6_7(ctx):
    _report(ctx, "\n📅 DCTR-6/7 — Personal & Business L12M Monthly")
    l12m = ctx["last_12_months"]

    # Personal L12M
    epl = ctx["eligible_personal_last_12m"]
    pl_monthly, pl_ins = _l12m_monthly(epl, l12m)
    _save(
        ctx,
        pl_monthly,
        "DCTR-6-Personal-L12M",
        "Personal L12M DCTR",
        {
            "DCTR": f"{pl_ins['dctr']:.1%}",
            "Accounts": f"{pl_ins['total_accounts']:,}",
            "Active Months": f"{pl_ins['months_active']}",
        },
    )
    ctx["results"]["dctr_6"] = {"monthly": pl_monthly, "insights": pl_ins}
    _report(ctx, f"   Personal L12M: {pl_ins['dctr']:.1%} ({pl_ins['total_accounts']:,} accts)")

    # Business L12M
    ebl = ctx["eligible_business_last_12m"]
    bl_monthly, bl_ins = _l12m_monthly(ebl, l12m)
    _save(
        ctx,
        bl_monthly,
        "DCTR-7-Business-L12M",
        "Business L12M DCTR",
        {"DCTR": f"{bl_ins['dctr']:.1%}", "Accounts": f"{bl_ins['total_accounts']:,}"},
    )
    ctx["results"]["dctr_7"] = {"monthly": bl_monthly, "insights": bl_ins}
    _report(ctx, f"   Business L12M: {bl_ins['dctr']:.1%} ({bl_ins['total_accounts']:,} accts)")
    return ctx


def run_dctr_8(ctx):
    _report(ctx, "\n📊 DCTR-8 — Comprehensive Summary")
    r = ctx["results"]
    rows = []

    def _add(
        label,
        cat,
        ins_key,
        total_key="total_accounts",
        wd_key="with_debit_count",
        dctr_key="overall_dctr",
    ):
        ins = r.get(ins_key, {}).get("insights", {})
        if not ins:
            return
        ta = ins.get(total_key, 0)
        if ta == 0:
            return
        wd = ins.get(wd_key, ins.get("with_debit", 0))
        dc = ins.get(dctr_key, ins.get("dctr", 0))
        rows.append(
            {
                "Account Type": label,
                "Category": cat,
                "Total Accounts": ta,
                "With Debit": wd,
                "Without Debit": ta - wd,
                "DCTR %": dc,
            }
        )

    _add("Eligible Accounts", "Overall", "dctr_1")
    _add(
        "Open Accounts (All)",
        "Overall",
        "dctr_2",
        total_key="open_total",
        wd_key="open_total",
        dctr_key="open_dctr",
    )

    # Fix Open — get from comparison
    d2 = r.get("dctr_2", {}).get("insights", {})
    if d2:
        ot = d2.get("open_total", 0)
        od = d2.get("open_dctr", 0)
        if ot > 0:
            # Replace last entry if it was wrong
            rows = [x for x in rows if x["Account Type"] != "Open Accounts (All)"]
            ow = int(od * ot)
            rows.append(
                {
                    "Account Type": "Open Accounts (All)",
                    "Category": "Overall",
                    "Total Accounts": ot,
                    "With Debit": ow,
                    "Without Debit": ot - ow,
                    "DCTR %": od,
                }
            )

    # L12M All
    d3 = r.get("dctr_3", {}).get("insights", {})
    if d3.get("total_accounts", 0) > 0:
        ta = d3["total_accounts"]
        wd = d3["with_debit"]
        dc = d3["dctr"]
        rows.append(
            {
                "Account Type": "Trailing Twelve Months (All)",
                "Category": "Time Period",
                "Total Accounts": ta,
                "With Debit": wd,
                "Without Debit": ta - wd,
                "DCTR %": dc,
            }
        )

    _add("Personal (Historical)", "Account Type", "dctr_4")
    _add("Business (Historical)", "Account Type", "dctr_5")

    # Personal/Business L12M
    for k, lbl in [("dctr_6", "Personal (TTM)"), ("dctr_7", "Business (TTM)")]:
        ins = r.get(k, {}).get("insights", {})
        if ins.get("total_accounts", 0) > 0:
            ta = ins["total_accounts"]
            wd = ins["with_debit"]
            dc = ins["dctr"]
            rows.append(
                {
                    "Account Type": lbl,
                    "Category": "Time Period",
                    "Total Accounts": ta,
                    "With Debit": wd,
                    "Without Debit": ta - wd,
                    "DCTR %": dc,
                }
            )

    summary = pd.DataFrame(rows)
    _save(
        ctx, summary, "DCTR-8-Summary", "Comprehensive DCTR Summary", {"Categories": f"{len(rows)}"}
    )
    ctx["results"]["dctr_8"] = {"summary": summary}
    _report(ctx, f"   {len(rows)} categories summarized")
    return ctx


def run_dctr_9(ctx):
    _report(ctx, "\n🏢 DCTR-9 — Branch Analysis")
    bm = ctx["config"].get("BranchMapping", {})
    chart_dir = ctx["chart_dir"]

    # A6.9a: All eligible historical
    br_all, br_ins = _branch_dctr(ctx["eligible_data"], bm)
    _save(
        ctx,
        br_all,
        "DCTR-9a-Branch-All",
        "Branch DCTR - All Eligible",
        {
            "Branches": f"{br_ins.get('total_branches', 0)}",
            "Best": f"{br_ins.get('best_branch', 'N/A')} ({br_ins.get('best_dctr', 0):.1%})",
            "Worst": f"{br_ins.get('worst_branch', 'N/A')} ({br_ins.get('worst_dctr', 0):.1%})",
        },
    )
    _report(
        ctx,
        f"   All: {br_ins.get('total_branches', 0)} branches | Best: {br_ins.get('best_branch', 'N/A')} ({br_ins.get('best_dctr', 0):.1%})",
    )

    # A6.9b: All L12M
    br_l12, br_l12_ins = _branch_dctr(ctx["eligible_last_12m"], bm)
    if not br_l12.empty:
        _save(
            ctx,
            br_l12,
            "DCTR-9b-Branch-L12M",
            "Branch DCTR - L12M",
            {"Branches": f"{br_l12_ins.get('total_branches', 0)}"},
        )

    # A6.9c: Personal L12M
    br_pl, br_pl_ins = _branch_dctr(ctx["eligible_personal_last_12m"], bm)
    if not br_pl.empty:
        _save(
            ctx,
            br_pl,
            "DCTR-9c-Branch-Personal-L12M",
            "Branch DCTR - Personal L12M",
            {"Branches": f"{br_pl_ins.get('total_branches', 0)}"},
        )

    # A6.9d: Business L12M
    br_bl, br_bl_ins = _branch_dctr(ctx["eligible_business_last_12m"], bm)
    if not br_bl.empty:
        _save(
            ctx,
            br_bl,
            "DCTR-9d-Branch-Business-L12M",
            "Branch DCTR - Business L12M",
            {"Branches": f"{br_bl_ins.get('total_branches', 0)}"},
        )

    # Chart A7.10b: Historical vs L12M by branch
    try:
        hist_dr = br_all[br_all["Branch"] != "TOTAL"].copy()
        l12m_dr = br_l12[br_l12["Branch"] != "TOTAL"].copy()
        if not hist_dr.empty and not l12m_dr.empty:
            merged = hist_dr[["Branch", "DCTR %", "Total Accounts"]].rename(
                columns={"DCTR %": "Historical DCTR", "Total Accounts": "Hist Volume"}
            )
            l12m_cols = l12m_dr[["Branch", "DCTR %", "Total Accounts"]].rename(
                columns={"DCTR %": "L12M DCTR", "Total Accounts": "L12M Volume"}
            )
            merged = merged.merge(l12m_cols, on="Branch", how="left").fillna(0)
            merged = merged.sort_values("Historical DCTR", ascending=False)
            merged["Change"] = merged["L12M DCTR"] - merged["Historical DCTR"]

            fig, ax1 = plt.subplots(figsize=(16, 8))
            x = np.arange(len(merged))
            w = 0.35
            b1 = ax1.bar(
                x - w / 2,
                merged["Hist Volume"],
                w,
                label="Historical",
                color="#BDC3C7",
                edgecolor="white",
                alpha=0.8,
            )
            b2 = ax1.bar(
                x + w / 2,
                merged["L12M Volume"],
                w,
                label="TTM",
                color="#85C1E9",
                edgecolor="white",
                alpha=0.8,
            )
            ax1.set_ylabel("Accounts", fontsize=20, fontweight="bold")
            ax1.set_xticks(x)
            ax1.set_xticklabels(merged["Branch"], rotation=45, ha="right", fontsize=18)
            ax1.tick_params(axis="y", labelsize=18)

            ax2 = ax1.twinx()
            ax2.plot(
                x,
                merged["Historical DCTR"] * 100,
                "o-",
                color="#1a5276",
                lw=3,
                ms=10,
                label="Hist DCTR",
            )
            ax2.plot(
                x, merged["L12M DCTR"] * 100, "o-", color="#2E7D32", lw=3, ms=12, label="TTM DCTR"
            )
            for i, v in enumerate(merged["L12M DCTR"] * 100):
                if v > 0:
                    ax2.text(
                        i,
                        v + 2,
                        f"{v:.0f}%",
                        ha="center",
                        fontsize=18,
                        fontweight="bold",
                        color="#2E7D32",
                    )
            ax2.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
            ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax2.tick_params(axis="y", labelsize=18)
            ax2.grid(False)
            [s.set_visible(False) for s in ax2.spines.values()]

            plt.title(
                "Branch DCTR: Volume & Rate Comparison", fontsize=24, fontweight="bold", pad=20
            )
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=16)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_branch_comparison.png")
            # Note: This is a supplementary view; A7.10a slide comes from run_dctr_branch_trend

            improving = (merged["Change"] > 0).sum()
            _save(
                ctx,
                merged,
                "DCTR-Branch-Comparison",
                "Branch DCTR Comparison",
                {"Improving": f"{improving} of {len(merged)}"},
            )
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch comparison chart: {e}")

    # Branch bar chart (top 10)
    try:
        fig, ax = _fig(ctx, "single")
        dr = br_all[br_all["Branch"] != "TOTAL"].head(10).iloc[::-1]
        ax.barh(
            dr["Branch"].astype(str),
            dr["DCTR %"] * 100,
            color="#2E86AB",
            edgecolor="black",
            linewidth=1.5,
            alpha=0.9,
        )
        ax.set_xlabel("DCTR (%)", fontsize=20, fontweight="bold")
        ax.set_title("Branch Debit Card Take Rate — Top 10", fontsize=24, fontweight="bold", pad=20)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
        ax.tick_params(axis="both", labelsize=18)
        for i, (d, t) in enumerate(zip(dr["DCTR %"], dr["Total Accounts"])):
            ax.text(
                d * 100 + 0.5,
                i,
                f"{d:.1%} ({int(t):,})",
                va="center",
                fontsize=18,
                fontweight="bold",
            )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="x", alpha=0.3, linestyle="--")
        ax.set_axisbelow(True)
        plt.tight_layout()
        cp2 = _save_chart(fig, chart_dir / "dctr_branch_top10.png")
        _slide(
            ctx,
            "A7.10c - Branch Top 10",
            {
                "title": "Branch Debit Card Take Rate",
                "subtitle": f"{br_ins.get('best_branch', '')} leads at {br_ins.get('best_dctr', 0):.1%}",
                "kpis": {
                    "Branches": f"{br_ins.get('total_branches', 0)}",
                    "Best": f"{br_ins.get('best_dctr', 0):.1%}",
                },
                "chart_path": cp2,
                "layout_index": 4,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Branch bar chart: {e}")

    ctx["results"]["dctr_9"] = {"all": br_ins, "l12m": br_l12_ins}
    return ctx


def run_dctr_10(ctx):
    _report(ctx, "\n📅 DCTR-10 — Account Age Breakdown")
    ed = ctx["eligible_data"].copy()
    ed["Date Opened"] = pd.to_datetime(ed["Date Opened"], errors="coerce")
    ed["Account Age Days"] = (pd.Timestamp.now() - ed["Date Opened"]).dt.days
    df, ins = _by_dimension(
        ed, "Account Age Days", categorize_account_age, AGE_ORDER, "Account Age"
    )
    _save(
        ctx,
        df,
        "DCTR-10-AccountAge",
        "DCTR by Account Age",
        {
            "Highest": f"{ins.get('highest', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
            "Lowest": f"{ins.get('lowest', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})",
        },
    )

    # Chart A7.12: Account Age DCTR — line chart with volume bars (matching notebook)
    try:
        chart_dir = ctx["chart_dir"]
        overall = ctx["results"]["dctr_1"]["insights"]["overall_dctr"] * 100
        dr = df[df["Account Age"] != "TOTAL"]
        if not dr.empty:
            fig, ax = plt.subplots(figsize=(14, 7))
            try:
                x = np.arange(len(dr))
                vals = dr["DCTR %"].values * 100
                volumes = dr["Total Accounts"].values

                # Volume bars on secondary axis
                ax2 = ax.twinx()
                ax2.bar(x, volumes, alpha=0.3, color="gray", edgecolor="none", width=0.6)
                for i, v in enumerate(volumes):
                    if v > 0:
                        ax2.text(
                            i,
                            v * 0.05,
                            f"{v:,}",
                            ha="center",
                            va="bottom",
                            fontsize=16,
                            color="gray",
                        )
                ax2.set_ylabel("Account Volume", fontsize=24, color="gray")
                ax2.set_ylim(0, max(volumes) * 2 if len(volumes) else 100)
                ax2.tick_params(axis="y", colors="gray", labelsize=20)

                # DCTR line chart on primary axis
                ax.plot(
                    x,
                    vals,
                    color="#2E86AB",
                    linewidth=4,
                    marker="o",
                    markersize=12,
                    label="DCTR %",
                    zorder=3,
                )
                for i, v in enumerate(vals):
                    ax.text(
                        i,
                        v + 2,
                        f"{v:.1f}%",
                        ha="center",
                        va="bottom",
                        fontsize=20,
                        fontweight="bold",
                        color="#2E86AB",
                    )

                ax.set_title(
                    "Eligible Accounts DCTR by Account Age/Maturity",
                    fontsize=24,
                    fontweight="bold",
                    pad=25,
                )
                ax.set_xlabel("Account Age", fontsize=20, fontweight="bold")
                ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold", color="#2E86AB")
                ax.set_xticks(x)
                ax.set_xticklabels(dr["Account Age"].values, fontsize=18, rotation=45, ha="right")
                ax.tick_params(axis="y", labelsize=20, colors="#2E86AB")
                ax.set_ylim(0, max(vals) * 1.2 if len(vals) else 100)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
                ax.grid(True, axis="y", alpha=0.3, linestyle="--")
                ax.set_axisbelow(True)
                ax.spines["top"].set_visible(False)
                ax2.spines["top"].set_visible(False)
                plt.tight_layout()
                cp = _save_chart(fig, chart_dir / "dctr_account_age.png")
            finally:
                plt.close(fig)

            newest = vals[0] if len(vals) else 0
            oldest = vals[-1] if len(vals) else 0
            gap = newest - oldest
            trend = (
                "newer accounts have higher DCTR"
                if gap > 5
                else "mature accounts have higher DCTR"
                if gap < -5
                else "DCTR is consistent across account ages"
            )
            try:
                high_band = ins.get("highest", "N/A")
                low_band = ins.get("lowest", "N/A")
                high_dctr = ins.get("highest_dctr", 0) * 100
                low_dctr = ins.get("lowest_dctr", 0) * 100
                spread_pp = high_dctr - low_dctr
                age_subtitle = (
                    f"{high_band} leads at {high_dctr:.1f}% vs {low_band} at {low_dctr:.1f}%"
                    f" ({spread_pp:.1f}pp spread) — {trend}"
                )
                if len(age_subtitle) > 120:
                    age_subtitle = (
                        f"{high_band} highest ({high_dctr:.1f}%) | {low_band} lowest"
                        f" ({low_dctr:.1f}%) — {spread_pp:.1f}pp spread"
                    )
            except Exception:
                age_subtitle = (
                    f"Ranges from {ins.get('lowest_dctr', 0):.0%} to"
                    f" {ins.get('highest_dctr', 0):.0%} — {trend}"
                )
            _slide(
                ctx,
                "A7.12 - DCTR by Account Age",
                {
                    "title": "Eligible Accounts DCTR by Account Age/Maturity",
                    "subtitle": age_subtitle,
                    "chart_path": cp,
                    "layout_index": 9,
                },
            )
    except Exception as e:
        _report(ctx, f"   ⚠️ Account age chart: {e}")

    ctx["results"]["dctr_10"] = {"df": df, "insights": ins}
    _report(ctx, f"   {ins.get('highest', '?')} highest | {ins.get('lowest', '?')} lowest")
    return ctx


def run_dctr_11(ctx):
    _report(ctx, "\n👤 DCTR-11 — Account Holder Age")
    ed = ctx["eligible_data"]

    if "Account Holder Age" not in ed.columns:
        _report(ctx, "   ⚠️ No 'Account Holder Age' column")
        ctx["results"]["dctr_11"] = {}
        return ctx

    edc = ed.copy()
    edc["Account Holder Age"] = pd.to_numeric(edc["Account Holder Age"], errors="coerce")
    valid = edc[(edc["Account Holder Age"] >= 18) & (edc["Account Holder Age"] <= 120)].copy()
    df, ins = _by_dimension(
        valid, "Account Holder Age", categorize_holder_age, HOLDER_AGE_ORDER, "Age Group"
    )
    _save(
        ctx,
        df,
        "DCTR-11-HolderAge",
        "DCTR by Holder Age",
        {
            "Highest": f"{ins.get('highest', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
            "Lowest": f"{ins.get('lowest', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})",
            "Coverage": f"{ins.get('coverage', 0):.1%}",
        },
    )

    # Chart A7.11: Holder Age DCTR — gradient blues, large fonts (matching notebook)
    try:
        chart_dir = ctx["chart_dir"]
        fig, ax = plt.subplots(figsize=(14, 7))
        try:
            dr = df[df["Age Group"] != "TOTAL"]
            vals = dr["DCTR %"].values * 100
            volumes = dr["Total Accounts"].values
            x = np.arange(len(dr))

            # Gradient blues matching notebook
            colors = plt.cm.Blues(np.linspace(0.5, 0.9, len(dr)))
            bars = ax.bar(x, vals, color=colors, edgecolor="black", linewidth=2, alpha=0.9)

            for i, (bar, v, vol) in enumerate(zip(bars, vals, volumes)):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    v + 1,
                    f"{v:.1f}%",
                    ha="center",
                    fontsize=24,
                    fontweight="bold",
                )
                if v > 10:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        v / 2,
                        f"{vol:,}\naccts",
                        ha="center",
                        fontsize=18,
                        fontweight="bold",
                        color="white",
                    )

            ax.set_title(
                "Eligible Accounts DCTR by Account Holder Age",
                fontsize=24,
                fontweight="bold",
                pad=25,
            )
            ax.set_xlabel("Age Group", fontsize=20, fontweight="bold")
            ax.set_ylabel("DCTR (%)", fontsize=20, fontweight="bold")
            ax.set_xticks(x)
            ax.set_xticklabels(dr["Age Group"].values, fontsize=20)
            ax.tick_params(axis="y", labelsize=20)
            ax.set_ylim(0, max(vals) * 1.15 if len(vals) else 100)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:.0f}%"))
            ax.grid(True, axis="y", alpha=0.3, linestyle="--")
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            cp = _save_chart(fig, chart_dir / "dctr_holder_age.png")
        finally:
            plt.close(fig)
        try:
            high_grp = ins.get("highest", "N/A")
            low_grp = ins.get("lowest", "N/A")
            high_pct = ins.get("highest_dctr", 0) * 100
            low_pct = ins.get("lowest_dctr", 0) * 100
            spread_pp = high_pct - low_pct
            overall_dctr = (
                ctx["results"].get("dctr_1", {}).get("insights", {}).get("overall_dctr", 0) * 100
            )
            high_vs_overall = high_pct - overall_dctr
            holder_age_subtitle = (
                f"{high_grp} highest at {high_pct:.1f}% ({high_vs_overall:+.1f}pp vs avg);"
                f" {low_grp} lowest at {low_pct:.1f}% — {spread_pp:.1f}pp spread"
            )
            if len(holder_age_subtitle) > 120:
                holder_age_subtitle = (
                    f"{high_grp} leads at {high_pct:.1f}% | {low_grp} trails at {low_pct:.1f}%"
                    f" — {spread_pp:.1f}pp spread across age groups"
                )
        except Exception:
            holder_age_subtitle = (
                f"Ranges from {ins.get('lowest_dctr', 0):.0%} ({ins.get('lowest', '')})"
                f" to {ins.get('highest_dctr', 0):.0%} ({ins.get('highest', '')})"
            )
        _slide(
            ctx,
            "A7.11 - DCTR by Account Holder Age",
            {
                "title": "Eligible Accounts DCTR by Account Holder Age",
                "subtitle": holder_age_subtitle,
                "chart_path": cp,
                "layout_index": 9,
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    ctx["results"]["dctr_11"] = {"df": df, "insights": ins}
    _report(ctx, f"   {ins.get('highest', '?')} highest at {ins.get('highest_dctr', 0):.1%}")
    return ctx


def run_dctr_12(ctx):
    _report(ctx, "\n💰 DCTR-12 — Balance Range")
    ed = ctx["eligible_data"]
    if "Avg Bal" not in ed.columns:
        _report(ctx, "   ⚠️ No 'Avg Bal' column")
        ctx["results"]["dctr_12"] = {}
        return ctx

    edc = ed.copy()
    edc["Avg Bal"] = pd.to_numeric(edc["Avg Bal"], errors="coerce")
    valid = edc[edc["Avg Bal"].notna()].copy()
    df, ins = _by_dimension(valid, "Avg Bal", categorize_balance, BALANCE_ORDER, "Balance Range")
    _save(
        ctx,
        df,
        "DCTR-12-Balance",
        "DCTR by Balance Range",
        {
            "Highest": f"{ins.get('highest', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
            "Lowest": f"{ins.get('lowest', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})",
        },
    )
    ctx["results"]["dctr_12"] = {"df": df, "insights": ins}
    _report(ctx, f"   {ins.get('highest', '?')} highest | {ins.get('lowest', '?')} lowest")
    return ctx


def run_dctr_13(ctx):
    _report(ctx, "\n🔀 DCTR-13 — Cross-Tab: Holder Age × Balance")
    ed = ctx["eligible_data"]
    if "Account Holder Age" not in ed.columns or "Avg Bal" not in ed.columns:
        _report(ctx, "   ⚠️ Missing columns")
        ctx["results"]["dctr_13"] = {}
        return ctx

    dc = ed.copy()
    dc["Account Holder Age"] = pd.to_numeric(dc["Account Holder Age"], errors="coerce")
    dc["Avg Bal"] = pd.to_numeric(dc["Avg Bal"], errors="coerce")
    valid = dc[
        (dc["Account Holder Age"] >= 18) & (dc["Account Holder Age"] <= 120) & dc["Avg Bal"].notna()
    ].copy()

    detail, dpiv, cpiv, ins = _crosstab(
        valid,
        "Account Holder Age",
        categorize_holder_age,
        HOLDER_AGE_ORDER,
        "Age Group",
        "Avg Bal",
        categorize_balance,
        BALANCE_ORDER,
        "Balance Range",
    )
    if not detail.empty:
        _save(
            ctx,
            detail,
            "DCTR-13-AgeBalance",
            "Cross-Tab: Holder Age × Balance",
            {
                "Segments": f"{ins.get('segments', 0)}",
                "Highest": f"{ins.get('highest_seg', 'N/A')} ({ins.get('highest_dctr', 0):.1%})",
                "Lowest": f"{ins.get('lowest_seg', 'N/A')} ({ins.get('lowest_dctr', 0):.1%})",
            },
        )
        if not dpiv.empty:
            _save(ctx, dpiv, "DCTR-13-Pivot", "DCTR % by Age × Balance")
            # Heatmap chart
            chart_dir = ctx["chart_dir"]
            _draw_crosstab_heatmap(
                dpiv,
                chart_dir,
                "dctr_13_age_balance_heatmap.png",
                "DCTR by Holder Age & Balance Range",
                "Balance Range",
                "Age Group",
            )
            _slide(
                ctx,
                "A7.22 - Holder Age × Balance Heatmap",
                {
                    "title": "DCTR by Holder Age & Balance Range",
                    "subtitle": (
                        f"Highest: {ins.get('highest_seg', 'N/A')} "
                        f"({ins.get('highest_dctr', 0):.1%}) | "
                        f"Lowest: {ins.get('lowest_seg', 'N/A')} "
                        f"({ins.get('lowest_dctr', 0):.1%})"
                    ),
                    "chart_path": str(chart_dir / "dctr_13_age_balance_heatmap.png"),
                    "layout_index": 9,
                    "slide_type": "chart_only",
                },
            )
    ctx["results"]["dctr_13"] = ins
    _report(ctx, f"   {ins.get('segments', 0)} segments")
    return ctx


def run_dctr_14(ctx):
    _report(ctx, "\n🔀 DCTR-14 — Cross-Tab: Account Age × Balance")
    ed = ctx["eligible_data"]
    if "Avg Bal" not in ed.columns:
        _report(ctx, "   ⚠️ Missing 'Avg Bal'")
        ctx["results"]["dctr_14"] = {}
        return ctx

    dc = ed.copy()
    dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
    dc["Account Age Days"] = (pd.Timestamp.now() - dc["Date Opened"]).dt.days
    dc["Avg Bal"] = pd.to_numeric(dc["Avg Bal"], errors="coerce")
    valid = dc[dc["Account Age Days"].notna() & dc["Avg Bal"].notna()].copy()

    detail, dpiv, cpiv, ins = _crosstab(
        valid,
        "Account Age Days",
        categorize_account_age,
        AGE_ORDER,
        "Account Age",
        "Avg Bal",
        categorize_balance,
        BALANCE_ORDER,
        "Balance Range",
    )
    if not detail.empty:
        _save(
            ctx,
            detail,
            "DCTR-14-AcctAgeBalance",
            "Cross-Tab: Account Age × Balance",
            {"Segments": f"{ins.get('segments', 0)}"},
        )
        if not dpiv.empty:
            _save(ctx, dpiv, "DCTR-14-Pivot", "DCTR % by Account Age × Balance")
            chart_dir = ctx["chart_dir"]
            _draw_crosstab_heatmap(
                dpiv,
                chart_dir,
                "dctr_14_acctage_balance_heatmap.png",
                "DCTR by Account Age & Balance Range",
                "Balance Range",
                "Account Age",
            )
            _slide(
                ctx,
                "A7.23 - Account Age × Balance Heatmap",
                {
                    "title": "DCTR by Account Age & Balance Range",
                    "subtitle": f"{ins.get('segments', 0)} segments analyzed",
                    "chart_path": str(chart_dir / "dctr_14_acctage_balance_heatmap.png"),
                    "layout_index": 9,
                    "slide_type": "chart_only",
                },
            )
    ctx["results"]["dctr_14"] = ins
    _report(ctx, f"   {ins.get('segments', 0)} segments")
    return ctx


def run_dctr_15(ctx):
    _report(ctx, "\n🔀 DCTR-15 — Cross-Tab: Branch × Account Age")
    ed = ctx["eligible_data"].copy()
    bm = ctx["config"].get("BranchMapping", {})

    ed["Date Opened"] = pd.to_datetime(ed["Date Opened"], errors="coerce")
    ed["Account Age Days"] = (pd.Timestamp.now() - ed["Date Opened"]).dt.days
    if bm:
        ed["Branch Name"] = ed["Branch"].map(bm).fillna(ed["Branch"])
    else:
        ed["Branch Name"] = ed["Branch"]
    valid = ed[ed["Account Age Days"].notna()].copy()
    valid["Simple Age"] = (
        valid["Account Age Days"].apply(categorize_account_age).apply(simplify_account_age)
    )

    rows = []
    simple_order = ["New (0-1 year)", "Recent (1-5 years)", "Mature (5+ years)"]
    for branch in sorted(valid["Branch Name"].unique()):
        bd = valid[valid["Branch Name"] == branch]
        for ac in simple_order:
            seg = bd[bd["Simple Age"] == ac]
            if len(seg) > 0:
                t, w, d = _dctr(seg)
                rows.append(
                    {
                        "Branch": branch,
                        "Age Category": ac,
                        "Total Accounts": t,
                        "With Debit": w,
                        "DCTR %": d,
                    }
                )

    detail = pd.DataFrame(rows)
    if not detail.empty:
        pivot = detail.pivot_table(index="Branch", columns="Age Category", values="DCTR %")
        pivot = pivot.reindex(columns=simple_order)
        _save(
            ctx,
            detail,
            "DCTR-15-BranchAge",
            "Cross-Tab: Branch × Account Age",
            {"Branches": f"{len(detail['Branch'].unique())}"},
        )
        _save(ctx, pivot, "DCTR-15-Pivot", "Branch DCTR by Account Age")
        chart_dir = ctx["chart_dir"]
        _draw_crosstab_heatmap(
            pivot,
            chart_dir,
            "dctr_15_branch_age_heatmap.png",
            "DCTR by Branch & Account Age",
            "Account Age",
            "Branch",
        )
        _slide(
            ctx,
            "A7.24 - Branch × Account Age Heatmap",
            {
                "title": "DCTR by Branch & Account Age",
                "subtitle": f"{len(detail['Branch'].unique())} branches analyzed",
                "chart_path": str(chart_dir / "dctr_15_branch_age_heatmap.png"),
                "layout_index": 9,
                "slide_type": "chart_only",
            },
        )

        # Find best at new accounts
        new_data = detail[detail["Age Category"] == "New (0-1 year)"]
        best_new = new_data.loc[new_data["DCTR %"].idxmax()] if not new_data.empty else None
        ins = {"branches": len(detail["Branch"].unique())}
        if best_new is not None:
            ins["best_new_branch"] = best_new["Branch"]
            ins["best_new_dctr"] = best_new["DCTR %"]
        ctx["results"]["dctr_15"] = ins
        _report(ctx, f"   {ins['branches']} branches × 3 age categories")
    else:
        ctx["results"]["dctr_15"] = {}
    return ctx


def run_dctr_16(ctx):
    _report(ctx, "\n📊 DCTR-16 — Branch L12M Monthly Table")
    ed = ctx["eligible_data"].copy()
    l12m = ctx["last_12_months"]
    bm = ctx["config"].get("BranchMapping", {})
    chart_dir = ctx["chart_dir"]

    ed["Date Opened"] = pd.to_datetime(ed["Date Opened"], errors="coerce")
    ed["Month_Year"] = ed["Date Opened"].dt.strftime("%b%y")
    if bm:
        ed["Branch Name"] = ed["Branch"].map(bm).fillna(ed["Branch"])
    else:
        ed["Branch Name"] = ed["Branch"]

    all_branches = sorted(ed["Branch Name"].unique())
    rows = []
    for branch in all_branches:
        bd = ed[ed["Branch Name"] == branch]
        row = {"Branch": branch}
        te = td = 0
        for month in l12m:
            md = bd[bd["Month_Year"] == month]
            elig = len(md)
            debits = len(md[md["Debit?"] == "Yes"])
            te += elig
            td += debits
            row[month] = f"{(debits / elig * 100):.1f}%" if elig > 0 else ""
        row["12M Debits"] = td
        row["12M Eligible"] = te
        row["12M Take Rate"] = f"{(td / te * 100):.1f}%" if te > 0 else "0.0%"
        rows.append(row)

    table = pd.DataFrame(rows)
    grand_d = sum(r["12M Debits"] for r in rows)
    grand_e = sum(r["12M Eligible"] for r in rows)
    grand_r = (grand_d / grand_e * 100) if grand_e > 0 else 0

    _save(
        ctx,
        table,
        "DCTR-16-Branch-L12M-Table",
        "Branch L12M Performance",
        {
            "Overall": f"{grand_r:.1f}%",
            "Branches": f"{len(all_branches)}",
            "Total Eligible": f"{grand_e:,}",
            "Total Debits": f"{grand_d:,}",
        },
    )

    # Derive best/worst branch for richer subtitle
    try:
        branch_rates = [
            (r["Branch"], float(r["12M Take Rate"].rstrip("%")))
            for r in rows
            if r.get("12M Take Rate") and r["12M Take Rate"] != "0.0%"
        ]
        branch_rates.sort(key=lambda x: x[1], reverse=True)
        best_br, best_br_rate = branch_rates[0] if branch_rates else ("N/A", grand_r)
        worst_br, worst_br_rate = branch_rates[-1] if len(branch_rates) > 1 else ("N/A", grand_r)
        br_spread = best_br_rate - worst_br_rate
        l12m_subtitle = (
            f"TTM avg {grand_r:.1f}% — {best_br} leads ({best_br_rate:.1f}%),"
            f" {worst_br} trails ({worst_br_rate:.1f}%) — {br_spread:.1f}pp spread"
        )
        if len(l12m_subtitle) > 120:
            l12m_subtitle = (
                f"TTM avg {grand_r:.1f}% across {len(all_branches)} branches"
                f" — {best_br} leads at {best_br_rate:.1f}%"
            )
    except Exception:
        l12m_subtitle = f"Overall take rate {grand_r:.1f}% across {len(all_branches)} branches"

    # Table slide
    _slide(
        ctx,
        "A7.16 - Branch L12M Table",
        {
            "title": "Branch Debit Card Analysis (TTM)",
            "subtitle": l12m_subtitle,
            "layout_index": 11,
            "insights": [
                f"Period: {l12m[0]} to {l12m[-1]}",
                f"Total eligible: {grand_e:,}",
                f"Total debits: {grand_d:,}",
                f"Overall take rate: {grand_r:.1f}%",
            ],
        },
    )

    ctx["results"]["dctr_16"] = {
        "grand_rate": grand_r,
        "branches": len(all_branches),
        "grand_eligible": grand_e,
        "grand_debits": grand_d,
    }
    _report(ctx, f"   {len(all_branches)} branches | Overall: {grand_r:.1f}%")
    return ctx


# =============================================================================
# A7.18 — DCTR OPPORTUNITY SIZING
# =============================================================================


def run_dctr_opportunity(ctx):
    """A7.18 -- Quantify the account/revenue opportunity at benchmark targets."""
    from pathlib import Path

    _report(ctx, "\n📈 A7.18 — DCTR Opportunity Sizing")

    ed = ctx["eligible_data"]
    if ed.empty:
        _report(ctx, "   Skipped: no eligible data")
        return ctx

    total_eligible = len(ed)
    with_debit = len(ed[ed["Debit?"] == "Yes"])
    current_dctr = with_debit / total_eligible if total_eligible > 0 else 0

    targets = ctx.get("dctr_targets", {"peer_avg": 0.65, "p75": 0.72, "best_class": 0.80})
    ic_rate = ctx.get("ic_rate", 0)

    # Calculate opportunity at each target level
    tiers = []
    for key, label in [
        ("peer_avg", "Peer Avg"),
        ("p75", "75th Pctile"),
        ("best_class", "Best-in-Class"),
    ]:
        target = targets.get(key, 0)
        if target <= current_dctr:
            additional = 0
        else:
            additional = int(total_eligible * (target - current_dctr))
        revenue = additional * ic_rate * 12 * 200 if ic_rate > 0 else 0
        tiers.append(
            {
                "label": label,
                "target": target,
                "additional_accounts": additional,
                "revenue": revenue,
            }
        )

    # Build summary DataFrame
    rows = [
        {
            "Level": "Current",
            "DCTR": current_dctr,
            "Accounts w/ Debit": with_debit,
            "Additional Accounts": 0,
            "Est. Annual Revenue Uplift": 0,
        }
    ]
    for tier in tiers:
        rows.append(
            {
                "Level": tier["label"],
                "DCTR": tier["target"],
                "Accounts w/ Debit": with_debit + tier["additional_accounts"],
                "Additional Accounts": tier["additional_accounts"],
                "Est. Annual Revenue Uplift": tier["revenue"],
            }
        )
    summary_df = pd.DataFrame(rows)

    _save(
        ctx,
        summary_df,
        "DCTR-Opportunity",
        "DCTR Opportunity Sizing",
        {
            "Current DCTR": f"{current_dctr:.1%}",
            "Eligible Accounts": f"{total_eligible:,}",
            "Best-Class Gap": f"{max(0, targets.get('best_class', 0.80) - current_dctr):.1%}",
        },
    )

    # Chart: waterfall bar chart
    chart_dir = ctx["chart_dir"]
    fig, ax = _fig(ctx, "single")
    try:
        labels = ["Current"] + [t["label"] for t in tiers]
        values = [current_dctr * 100] + [t["target"] * 100 for t in tiers]
        colors = ["#4472C4"] + [
            "#70AD47" if t["target"] > current_dctr else "#A5A5A5" for t in tiers
        ]

        bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="black", linewidth=1.5)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{val:.1f}%",
                ha="center",
                va="bottom",
                fontsize=14,
                fontweight="bold",
            )

        # Add account deltas above benchmark bars
        for i, tier in enumerate(tiers, start=1):
            if tier["additional_accounts"] > 0:
                ax.text(
                    bars[i].get_x() + bars[i].get_width() / 2,
                    bars[i].get_height() + 2.5,
                    f"+{tier['additional_accounts']:,} accts",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    color="#333333",
                )

        # Reference line at current DCTR
        ax.axhline(y=current_dctr * 100, color="#E74C3C", linestyle="--", linewidth=1.5, alpha=0.7)

        ax.set_ylabel("DCTR %", fontsize=14, fontweight="bold")
        ax.set_title(
            "DCTR Opportunity: Current vs Benchmarks", fontsize=16, fontweight="bold", pad=15
        )
        max_val = max(values) if values else 100
        ax.set_ylim(0, min(100, max_val + 10))
        ax.tick_params(axis="both", labelsize=12)
        plt.tight_layout()

        chart_path = _save_chart(fig, Path(chart_dir) / "dctr_opportunity.png")
    finally:
        plt.close(fig)

    # Subtitle with key insight
    try:
        best_tier = tiers[-1]
        if best_tier["additional_accounts"] > 0:
            if ic_rate > 0:
                subtitle = (
                    f"Current {current_dctr:.1%} vs best-in-class {best_tier['target']:.0%}"
                    f" -- {best_tier['additional_accounts']:,} additional accounts"
                    f" = ${best_tier['revenue']:,.0f}/yr potential"
                )
            else:
                subtitle = (
                    f"Current {current_dctr:.1%} vs best-in-class {best_tier['target']:.0%}"
                    f" -- {best_tier['additional_accounts']:,} additional accounts achievable"
                )
        else:
            subtitle = f"Current DCTR {current_dctr:.1%} exceeds all benchmark targets"
        if len(subtitle) > 120:
            subtitle = (
                f"Current {current_dctr:.1%} — up to {best_tier['additional_accounts']:,}"
                f" additional accounts at best-in-class"
            )
    except Exception:
        subtitle = f"DCTR opportunity analysis ({total_eligible:,} eligible accounts)"

    _slide(
        ctx,
        "A7.18 - DCTR Opportunity",
        {
            "title": "DCTR Opportunity Sizing",
            "subtitle": subtitle,
            "chart_path": chart_path,
            "layout_index": 8,
            "slide_type": "chart",
        },
    )

    ctx["results"]["dctr_opportunity"] = {
        "current_dctr": current_dctr,
        "total_eligible": total_eligible,
        "with_debit": with_debit,
        "tiers": tiers,
    }
    _report(
        ctx,
        f"   Current: {current_dctr:.1%} | "
        f"Best-class gap: {max(0, targets.get('best_class', 0.80) - current_dctr):.1%}",
    )
    return ctx


# =============================================================================
# A7.19 — DCTR BY PRODUCT TYPE
# =============================================================================


def run_dctr_by_product(ctx):
    """A7.19 -- DCTR breakdown by Prod Code with historical vs L12M comparison."""
    from pathlib import Path

    _report(ctx, "\n📦 A7.19 — DCTR by Product Type")

    ed = ctx["eligible_data"]
    if ed.empty or "Prod Code" not in ed.columns:
        _report(ctx, "   Skipped: no eligible data or missing Prod Code column")
        return ctx

    # Historical DCTR by product
    hist_rows = []
    for pc in sorted(ed["Prod Code"].dropna().unique()):
        seg = ed[ed["Prod Code"] == pc]
        t, w, d = _dctr(seg)
        if t > 0:
            hist_rows.append(
                {
                    "Prod Code": pc,
                    "Total Accounts": t,
                    "With Debit": w,
                    "DCTR %": d,
                }
            )
    hist_df = pd.DataFrame(hist_rows)
    if hist_df.empty:
        _report(ctx, "   Skipped: no product type data")
        return ctx
    hist_df = hist_df.sort_values("Total Accounts", ascending=False)

    # L12M DCTR by product (if L12M subset available)
    l12m_data = ctx.get("eligible_last_12m", pd.DataFrame())
    l12m_map = {}
    if not l12m_data.empty and "Prod Code" in l12m_data.columns:
        for pc in l12m_data["Prod Code"].dropna().unique():
            seg = l12m_data[l12m_data["Prod Code"] == pc]
            t, w, d = _dctr(seg)
            if t > 0:
                l12m_map[pc] = d

    # Build combined DataFrame
    combined_rows = []
    for _, row in hist_df.iterrows():
        pc = row["Prod Code"]
        combined_rows.append(
            {
                "Prod Code": pc,
                "Total Accounts": row["Total Accounts"],
                "Historical DCTR %": row["DCTR %"],
                "L12M DCTR %": l12m_map.get(pc, None),
            }
        )
    combined_df = pd.DataFrame(combined_rows)

    _save(
        ctx,
        combined_df,
        "DCTR-ByProduct",
        "DCTR by Product Type",
        {"Products": f"{len(combined_df)}"},
    )

    # Chart: grouped bar (hist vs L12M)
    chart_dir = ctx["chart_dir"]
    fig, ax = _fig(ctx, "single")
    try:
        prods = combined_df["Prod Code"].tolist()
        hist_vals = (combined_df["Historical DCTR %"] * 100).tolist()
        l12m_vals = (combined_df["L12M DCTR %"].fillna(0) * 100).tolist()

        x = np.arange(len(prods))
        width = 0.35

        bars1 = ax.bar(
            x - width / 2,
            hist_vals,
            width,
            label="Historical",
            color="#4472C4",
            edgecolor="black",
            linewidth=1,
        )
        bars2 = ax.bar(
            x + width / 2,
            l12m_vals,
            width,
            label="L12M",
            color="#70AD47",
            edgecolor="black",
            linewidth=1,
        )

        for bar, val in zip(bars1, hist_vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    f"{val:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )
        for bar, val in zip(bars2, l12m_vals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.5,
                    f"{val:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )

        # Volume overlay on secondary axis
        ax2 = ax.twinx()
        volumes = combined_df["Total Accounts"].tolist()
        ax2.plot(
            x, volumes, "o-", color="#E74C3C", linewidth=2, markersize=8, label="Account Volume"
        )
        ax2.set_ylabel("Account Volume", fontsize=12, color="#E74C3C")
        ax2.tick_params(axis="y", labelcolor="#E74C3C")

        ax.set_xlabel("Product Code", fontsize=14, fontweight="bold")
        ax.set_ylabel("DCTR %", fontsize=14, fontweight="bold")
        ax.set_title(
            "DCTR by Product Type (Historical vs L12M)", fontsize=16, fontweight="bold", pad=15
        )
        ax.set_xticks(x)
        ax.set_xticklabels(prods, fontsize=12)
        ax.legend(loc="upper left", fontsize=11)
        ax2.legend(loc="upper right", fontsize=11)
        max_dctr = max(hist_vals + l12m_vals) if hist_vals else 100
        ax.set_ylim(0, min(100, max_dctr + 10))
        plt.tight_layout()

        chart_path = _save_chart(fig, Path(chart_dir) / "dctr_by_product.png")
    finally:
        plt.close(fig)

    # Subtitle
    try:
        best = combined_df.loc[combined_df["Historical DCTR %"].idxmax()]
        worst = combined_df.loc[combined_df["Historical DCTR %"].idxmin()]
        spread = best["Historical DCTR %"] - worst["Historical DCTR %"]
        subtitle = (
            f"{len(prods)} product types — {best['Prod Code']} leads at"
            f" {best['Historical DCTR %']:.1%}, {worst['Prod Code']} trails at"
            f" {worst['Historical DCTR %']:.1%} ({spread:.1%} spread)"
        )
        if len(subtitle) > 120:
            subtitle = (
                f"{len(prods)} products — {best['Prod Code']} leads at"
                f" {best['Historical DCTR %']:.1%}"
            )
    except Exception:
        subtitle = f"DCTR by product type ({len(prods)} products)"

    _slide(
        ctx,
        "A7.19 - DCTR by Product Type",
        {
            "title": "DCTR by Product Type",
            "subtitle": subtitle,
            "chart_path": chart_path,
            "layout_index": 8,
            "slide_type": "chart",
        },
    )

    ctx["results"]["dctr_by_product"] = {
        "products": len(prods),
        "data": combined_df,
    }
    _report(ctx, f"   {len(prods)} product types analyzed")
    return ctx


# =============================================================================
# A7.0 — DCTR EXECUTIVE SUMMARY
# =============================================================================


def run_dctr_executive_summary(ctx):
    """A7.0 -- Single summary slide synthesizing all DCTR findings into KPIs."""
    from pathlib import Path

    _report(ctx, "\n📋 A7.0 — DCTR Executive Summary")

    results = ctx.get("results", {})

    # Pull KPIs from prior analyses (with safe fallbacks)
    dctr_1 = results.get("dctr_1", {})
    ins = dctr_1.get("insights", {})
    overall_dctr = ins.get("overall_dctr", 0)
    recent_dctr = ins.get("recent_dctr", 0)

    dctr_3 = results.get("dctr_3", {})
    l12m_ins = dctr_3.get("insights", {})
    l12m_dctr = l12m_ins.get("dctr", 0)

    dctr_9_hist = results.get("dctr_9_hist", {})
    hist_branch = dctr_9_hist.get("insights", {})
    best_branch = hist_branch.get("best_branch", "N/A")
    best_dctr = hist_branch.get("best_dctr", 0)
    worst_branch = hist_branch.get("worst_branch", "N/A")
    worst_dctr = hist_branch.get("worst_dctr", 0)

    opp = results.get("dctr_opportunity", {})
    tiers = opp.get("tiers", [])
    best_class_gap = 0
    best_class_accts = 0
    if tiers:
        best_tier = tiers[-1]
        best_class_gap = max(0, best_tier.get("target", 0) - overall_dctr)
        best_class_accts = best_tier.get("additional_accounts", 0)

    targets = ctx.get("dctr_targets", {"peer_avg": 0.65, "p75": 0.72, "best_class": 0.80})

    # Build KPI summary
    kpis = {
        "Overall DCTR": f"{overall_dctr:.1%}",
        "L12M DCTR": f"{l12m_dctr:.1%}" if l12m_dctr else f"{recent_dctr:.1%}",
        "Best Branch": f"{best_branch} ({best_dctr:.1%})" if best_branch != "N/A" else "N/A",
        "Worst Branch": f"{worst_branch} ({worst_dctr:.1%})" if worst_branch != "N/A" else "N/A",
        "Best-Class Target": f"{targets.get('best_class', 0.80):.0%}",
        "Opportunity": f"{best_class_accts:,} accounts" if best_class_accts else "At target",
    }

    # Build insight bullets
    bullets = []
    if overall_dctr > 0:
        bullets.append(f"Overall eligible DCTR stands at {overall_dctr:.1%}")
    trend_dctr = l12m_dctr if l12m_dctr else recent_dctr
    if trend_dctr and overall_dctr:
        diff = trend_dctr - overall_dctr
        direction = "improving" if diff > 0.005 else "declining" if diff < -0.005 else "stable"
        bullets.append(f"Recent trend is {direction} ({diff:+.1%} vs historical)")
    if best_branch != "N/A" and worst_branch != "N/A":
        branch_spread = best_dctr - worst_dctr
        bullets.append(
            f"Branch spread: {branch_spread:.1%} ({best_branch} at {best_dctr:.1%}"
            f" vs {worst_branch} at {worst_dctr:.1%})"
        )
    if best_class_accts > 0:
        bullets.append(
            f"Closing to best-in-class ({targets.get('best_class', 0.80):.0%}) would"
            f" capture {best_class_accts:,} additional accounts"
        )

    # Chart: KPI dashboard with boxes
    chart_dir = ctx["chart_dir"]
    fig = plt.figure(figsize=(20, 10))
    fig.patch.set_facecolor("white")
    try:
        ax = fig.add_axes([0.02, 0.02, 0.96, 0.96])
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis("off")

        ax.text(
            5,
            9.5,
            "DCTR Executive Summary",
            fontsize=24,
            fontweight="bold",
            color="#1E3D59",
            ha="center",
            va="top",
        )

        # KPI boxes (2 rows of 3)
        box_colors = ["#4472C4", "#70AD47", "#4472C4", "#E74C3C", "#F39C12", "#70AD47"]
        kpi_items = list(kpis.items())
        positions = [
            (1.5, 7.5),
            (5.0, 7.5),
            (8.5, 7.5),
            (1.5, 5.5),
            (5.0, 5.5),
            (8.5, 5.5),
        ]
        from matplotlib.patches import FancyBboxPatch

        for i, ((label, value), (px, py)) in enumerate(zip(kpi_items, positions)):
            color = box_colors[i % len(box_colors)]
            box = FancyBboxPatch(
                (px - 1.3, py - 0.7),
                2.6,
                1.4,
                boxstyle="round,pad=0.1",
                facecolor=color,
                alpha=0.15,
                edgecolor=color,
                linewidth=2,
            )
            ax.add_patch(box)
            ax.text(
                px,
                py + 0.25,
                value,
                fontsize=18,
                fontweight="bold",
                color=color,
                ha="center",
                va="center",
            )
            ax.text(px, py - 0.3, label, fontsize=11, color="#666666", ha="center", va="center")

        # Bullet insights
        y_start = 3.8
        ax.text(1.0, y_start, "Key Insights", fontsize=16, fontweight="bold", color="#1E3D59")
        for j, bullet in enumerate(bullets[:4]):
            ax.text(
                1.2, y_start - 0.7 - j * 0.6, f"  {bullet}", fontsize=12, color="#333333", wrap=True
            )

        chart_path = _save_chart(fig, Path(chart_dir) / "dctr_executive_summary.png")
    finally:
        plt.close(fig)

    # Subtitle
    try:
        subtitle = (
            f"DCTR at {overall_dctr:.1%} — "
            + (f"L12M {l12m_dctr:.1%}" if l12m_dctr else f"recent {recent_dctr:.1%}")
            + (f" — {best_class_accts:,} account opportunity" if best_class_accts else "")
        )
        if len(subtitle) > 120:
            subtitle = (
                f"Overall DCTR {overall_dctr:.1%} with {best_class_accts:,} account opportunity"
            )
    except Exception:
        subtitle = "DCTR Executive Summary"

    _slide(
        ctx,
        "A7.0 - DCTR Executive Summary",
        {
            "title": "DCTR At a Glance",
            "subtitle": subtitle,
            "chart_path": chart_path,
            "layout_index": 8,
            "slide_type": "chart",
        },
    )

    ctx["results"]["dctr_executive_summary"] = {
        "kpis": kpis,
        "bullets": bullets,
    }
    _report(ctx, f"   Summary: {overall_dctr:.1%} overall | {len(bullets)} insights")
    return ctx
