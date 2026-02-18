"""
value.py — Value Analysis Module (A11)
=======================================
A11.1  Value of a Debit Card   — revenue comparison with/without debit
A11.2  Value of Reg E Opt-In   — revenue comparison with/without Reg E

Both produce:
  • Visual comparison table chart (matplotlib Rectangle grid)
  • Excel export (comparison + value summary)
  • PowerPoint slide (layout_index 5 — half image / half insights)

Usage:
    from value import run_value_suite
    ctx = run_value_suite(ctx)
"""

import matplotlib
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

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
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _slide(ctx, slide_id, data, category="Value"):
    ctx["all_slides"].append({"id": slide_id, "category": category, "data": data, "include": True})


def _save(ctx, df, sheet, title, metrics=None):
    fn = ctx.get("_save_to_excel")
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   ⚠️ Export {sheet}: {e}")


def _find_col(df, keyword, period_hint="12"):
    """Find a column by keyword (e.g. 'spend', 'items') with period hint."""
    # Try exact match first: keyword + period hint
    for col in df.columns:
        if keyword in col.lower() and (period_hint in col or period_hint.lower() in col.lower()):
            return col
    # Fallback: keyword + common period patterns (L12M, 12M, 12 Month, etc.)
    period_patterns = ["l12m", "12m", "12 month", "last 12", "ltm", "trailing"]
    for col in df.columns:
        cl = col.lower()
        if keyword in cl and any(p in cl for p in period_patterns):
            return col
    # Last resort: keyword only (no period filter)
    for col in df.columns:
        if keyword in col.lower():
            return col
    return None


# =============================================================================
# COMPARISON TABLE CHART (shared by A11.1 and A11.2)
# =============================================================================


def _draw_comparison_table(
    ctx,
    row_data,
    col1_header,
    col2_header,
    col1_color="#6B7F99",
    col2_color="#4A9B9F",
    highlight_color="#D4A574",
):
    """
    Draw the clean rectangular comparison table used by both A11.1 and A11.2.

    Parameters
    ----------
    row_data : list of tuples
        Each: (y_pos, label, col1_val_str, col2_val_str)
    col1_header, col2_header : str
        Column header text (can include \\n).
    col1_color, col2_color : str
        Hex colors for the two data columns.
    highlight_color : str
        Color for the final row (Revenue Per Account).

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig = plt.figure(figsize=(10, 8))
    ax = plt.gca()
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Column headers
    ax.text(5, 9, col1_header, fontsize=18, fontweight="500", color="#333333", ha="center")
    ax.text(7.5, 9, col2_header, fontsize=18, fontweight="500", color="#333333", ha="center")

    n_rows = len(row_data)
    for i, (y_pos, label, with_val, without_val) in enumerate(row_data):
        # Row label
        ax.text(2.5, y_pos, label, fontsize=16, color="#333333", va="center", ha="right")

        # Determine cell colors — last row gets highlight color
        if i < n_rows - 1:
            c1, c2 = col1_color, col2_color
        else:
            c1 = c2 = highlight_color

        # Column-1 cell
        rect1 = Rectangle((3.75, y_pos - 0.5), 2.25, 1, facecolor=c1, edgecolor="none")
        ax.add_patch(rect1)
        ax.text(
            5,
            y_pos,
            with_val,
            fontsize=18,
            color="white",
            ha="center",
            va="center",
            fontweight="500",
        )

        # Column-2 cell
        rect2 = Rectangle((6.25, y_pos - 0.5), 2.25, 1, facecolor=c2, edgecolor="none")
        ax.add_patch(rect2)
        ax.text(
            7.5,
            y_pos,
            without_val,
            fontsize=18,
            color="white",
            ha="center",
            va="center",
            fontweight="500",
        )

        # Dotted line separator (skip after last row)
        if i < n_rows - 1:
            ax.plot(
                [2.5, 8.5],
                [y_pos - 0.75, y_pos - 0.75],
                color="#CCCCCC",
                linewidth=1,
                linestyle="--",
            )

    plt.tight_layout()
    return fig


def _draw_value_slide(
    ctx,
    row_data,
    col1_header,
    col2_header,
    impact,
    col1_color="#6B7F99",
    col2_color="#4A9B9F",
    highlight_color="#D4A574",
):
    """Draw combined comparison table (left) + potential impact text (right)."""
    fig = plt.figure(figsize=(20, 8))
    fig.patch.set_facecolor("white")

    # --- LEFT HALF: Comparison table ---
    ax_left = fig.add_axes([0.02, 0.05, 0.48, 0.90])
    ax_left.set_xlim(0, 10)
    ax_left.set_ylim(0, 10)
    ax_left.axis("off")

    ax_left.text(5, 9, col1_header, fontsize=18, fontweight="500", color="#333333", ha="center")
    ax_left.text(7.5, 9, col2_header, fontsize=18, fontweight="500", color="#333333", ha="center")

    n_rows = len(row_data)
    for i, (y_pos, label, with_val, without_val) in enumerate(row_data):
        ax_left.text(2.5, y_pos, label, fontsize=16, color="#333333", va="center", ha="right")
        if i < n_rows - 1:
            c1, c2 = col1_color, col2_color
        else:
            c1 = c2 = highlight_color

        rect1 = Rectangle((3.75, y_pos - 0.5), 2.25, 1, facecolor=c1, edgecolor="none")
        ax_left.add_patch(rect1)
        ax_left.text(
            5,
            y_pos,
            with_val,
            fontsize=18,
            color="white",
            ha="center",
            va="center",
            fontweight="500",
        )

        rect2 = Rectangle((6.25, y_pos - 0.5), 2.25, 1, facecolor=c2, edgecolor="none")
        ax_left.add_patch(rect2)
        ax_left.text(
            7.5,
            y_pos,
            without_val,
            fontsize=18,
            color="white",
            ha="center",
            va="center",
            fontweight="500",
        )

        if i < n_rows - 1:
            ax_left.plot(
                [2.5, 8.5],
                [y_pos - 0.75, y_pos - 0.75],
                color="#CCCCCC",
                linewidth=1,
                linestyle="--",
            )

    # --- RIGHT HALF: Potential impact text (no background panel) ---
    ax_right = fig.add_axes([0.52, 0.05, 0.46, 0.90])
    ax_right.set_xlim(0, 10)
    ax_right.set_ylim(0, 10)
    ax_right.axis("off")

    awo = impact.get("awo", 0)
    delta = impact.get("delta", 0)
    hist_rate = impact.get("hist_rate", 0)
    l12m_rate = impact.get("l12m_rate", 0)
    pot_hist = impact.get("pot_hist", 0)
    pot_l12m = impact.get("pot_l12m", 0)
    pot_100 = impact.get("pot_100", awo * delta)
    rate_label = impact.get("rate_label", "DCTR")

    ax_right.text(
        5, 9.2, "Potential Impact", fontsize=22, fontweight="bold", color="#1E3D59", ha="center"
    )

    y = 8.0
    for label, value in [
        ("Accounts without feature", f"{awo:,}"),
        ("Revenue delta per account", f"${delta:.2f}"),
    ]:
        ax_right.text(5, y, label, fontsize=13, color="#666666", ha="center")
        y -= 0.5
        ax_right.text(5, y, value, fontsize=20, fontweight="bold", color="#333333", ha="center")
        y -= 1.0

    ax_right.text(
        5,
        y,
        "Estimated Revenue Opportunity",
        fontsize=16,
        fontweight="bold",
        color="#005072",
        ha="center",
    )
    y -= 0.9

    for label, value in [
        (f"At {hist_rate:.0%} Historical {rate_label}", f"${pot_hist:,.0f}"),
        (f"At {l12m_rate:.0%} TTM {rate_label}", f"${pot_l12m:,.0f}"),
        ("At 100% Adoption", f"${pot_100:,.0f}"),
    ]:
        ax_right.text(5, y, label, fontsize=12, color="#666666", ha="center")
        y -= 0.5
        ax_right.text(5, y, value, fontsize=20, fontweight="bold", color="#333333", ha="center")
        y -= 0.8

    return fig


# =============================================================================
# A11.1 — VALUE OF A DEBIT CARD
# =============================================================================


def run_value_1(ctx):
    """A11.1 — Value of a Debit Card: revenue with vs without debit."""
    _report(ctx, "\n💰 A11.1 — Value of a Debit Card")
    chart_dir = ctx["chart_dir"]

    # ── Fee configuration ──
    fee_amount = ctx.get("nsf_od_fee", 0.0)
    rate_amount = ctx.get("ic_rate", 0.0)
    _report(ctx, f"   NSF/OD Fee: ${fee_amount:.2f}  |  IC Rate: {rate_amount:.4%}")

    # ── Build L12M-active personal accounts ──
    ep = ctx.get("eligible_personal")
    if ep is None or ep.empty:
        _report(ctx, "   ⚠️ No eligible personal accounts")
        return ctx

    sd = ctx["start_date"]
    df = ep.copy()
    df["Date Closed"] = pd.to_datetime(df["Date Closed"], errors="coerce")
    active = df[df["Date Closed"].isna() | (df["Date Closed"] >= sd)].copy()
    _report(ctx, f"   Active personal accounts in L12M: {len(active):,}")

    # ── Discover spend / items columns ──
    spend_col = _find_col(active, "spend")
    items_col = _find_col(active, "items")
    if not spend_col or not items_col:
        _report(ctx, "   ⚠️ Could not find L12M spend/items columns — skipping A11.1")
        ctx["results"]["value_1"] = {}
        return ctx
    _report(ctx, f"   Spend col: {spend_col}  |  Items col: {items_col}")

    # ── Revenue calculation ──
    active["NSF/OD Revenue"] = active[items_col].fillna(0) * fee_amount
    active["Interchange Revenue"] = active[spend_col].fillna(0) * rate_amount
    active["Total Revenue"] = active["NSF/OD Revenue"] + active["Interchange Revenue"]

    rev = active.groupby("Debit?").agg(
        Accounts=("Debit?", "count"),
        NSF_OD=("NSF/OD Revenue", "sum"),
        IC=("Interchange Revenue", "sum"),
        Total=("Total Revenue", "sum"),
        Spend=(spend_col, "sum"),
        Items=(items_col, "sum"),
    )

    if "Yes" not in rev.index or "No" not in rev.index:
        _report(ctx, "   ⚠️ Need both Yes and No debit groups")
        return ctx

    # Extract metrics
    aw = int(rev.loc["Yes", "Accounts"])
    awo = int(rev.loc["No", "Accounts"])
    rw = rev.loc["Yes", "Total"]
    rwo = rev.loc["No", "Total"]
    rpw = rw / aw if aw else 0
    rpwo = rwo / awo if awo else 0
    nsf_w = rev.loc["Yes", "NSF_OD"]
    nsf_wo = rev.loc["No", "NSF_OD"]
    ic_w = rev.loc["Yes", "IC"]
    ic_wo = rev.loc["No", "IC"]
    delta_raw = rpw - rpwo
    delta = round(delta_raw, 2)
    multiplier = rpw / rpwo if rpwo > 0 else 0

    # ── Historical & L12M DCTR from earlier results ──
    dctr_1 = ctx["results"].get("dctr_1", {})
    dctr_3 = ctx["results"].get("dctr_3", {})

    hist_dctr = dctr_1.get("insights", {}).get("overall_dctr", None)
    if hist_dctr is None:
        # Fallback — compute from eligible_personal
        t_ep = len(ep)
        w_ep = len(ep[ep["Debit?"] == "Yes"])
        hist_dctr = w_ep / t_ep if t_ep > 0 else 0.80

    l12m_dctr = dctr_3.get("insights", {}).get("dctr", hist_dctr)

    pot_hist = awo * delta * hist_dctr
    pot_l12m = awo * delta * l12m_dctr
    pot_100 = awo * delta

    _report(ctx, f"   Rev/acct WITH: ${rpw:.2f}  |  WITHOUT: ${rpwo:.2f}  |  Δ ${delta:.2f}")
    _report(ctx, f"   Historical DCTR: {hist_dctr:.1%}  |  L12M DCTR: {l12m_dctr:.1%}")
    _report(ctx, f"   Potential (L12M): ${pot_l12m:,.0f}")

    # ── Chart — comparison table ──
    row_data = [
        (8, "Accounts", f"{aw:,}", f"{awo:,}"),
        (6.5, f"NSF/OD Revenue\n(${fee_amount})", f"${nsf_w:,.0f}", f"${nsf_wo:,.0f}"),
        (5, f"Interchange\nRevenue ({rate_amount:.4f})", f"${ic_w:,.0f}", f"${ic_wo:,.0f}"),
        (3.5, "Total Revenue", f"${rw:,.0f}", f"${rwo:,.0f}"),
        (2, "Revenue Per\nAccount", f"${rpw:.2f}", f"${rpwo:.2f}"),
    ]

    try:
        impact = {
            "awo": awo,
            "delta": delta,
            "hist_rate": hist_dctr,
            "l12m_rate": l12m_dctr,
            "pot_hist": pot_hist,
            "pot_l12m": pot_l12m,
            "pot_100": pot_100,
            "rate_label": "DCTR",
        }
        fig = _draw_value_slide(
            ctx,
            row_data,
            col1_header="With\nDebit Card",
            col2_header="Without\nDebit Card",
            impact=impact,
        )
        cp = _save_chart(fig, chart_dir / "a11_1_debit_card_value.png")

        subtitle = (
            f"${delta:.2f} more revenue per account — "
            f"${pot_l12m:,.0f} potential at {l12m_dctr:.0%} TTM DCTR"
        )
        _slide(
            ctx,
            "A11.1 - Value of a Debit Card",
            {
                "title": "Value of a Debit Card",
                "subtitle": subtitle,
                "layout_index": 13,
                "chart_path": cp,
                "category": "Value",
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    # ── Excel exports ──
    comp_df = pd.DataFrame(
        {
            "Debit Card Status": ["With Debit Card", "Without Debit Card"],
            "Accounts": [aw, awo],
            "NSF/OD Revenue": [nsf_w, nsf_wo],
            "Interchange Revenue": [ic_w, ic_wo],
            "Total Revenue": [rw, rwo],
            "Revenue Per Account": [rpw, rpwo],
        }
    )
    _save(
        ctx,
        comp_df,
        "A11-DebitCardValue",
        "Value of a Debit Card Analysis",
        {
            "Delta Per Account": f"${delta:.2f}",
            "Accounts Without Debit": f"{awo:,}",
            "Historical DCTR": f"{hist_dctr:.1%}",
            "TTM DCTR": f"{l12m_dctr:.1%}",
            "Potential (Historical)": f"${pot_hist:,.0f}",
            "Potential (L12M)": f"${pot_l12m:,.0f}",
        },
    )

    summary_df = pd.DataFrame(
        {
            "Metric": [
                "Revenue Per Account Delta",
                "Potential Value (100% conversion)",
                f"Potential Value ({hist_dctr:.0%} Historical DCTR)",
                f"Potential Value ({l12m_dctr:.0%} TTM DCTR)",
                "Accounts Without Debit",
            ],
            "Value": [
                f"${delta:.2f}",
                f"${pot_100:,.0f}",
                f"${pot_hist:,.0f}",
                f"${pot_l12m:,.0f}",
                f"{awo:,}",
            ],
        }
    )
    _save(ctx, summary_df, "A11-ValueSummary", "Value of a Debit Card - Summary Metrics")

    ctx["results"]["value_1"] = {
        "delta": delta,
        "multiplier": multiplier,
        "accts_with": aw,
        "accts_without": awo,
        "rev_per_with": rpw,
        "rev_per_without": rpwo,
        "nsf_w": nsf_w,
        "nsf_wo": nsf_wo,
        "ic_w": ic_w,
        "ic_wo": ic_wo,
        "rev_with": rw,
        "rev_without": rwo,
        "hist_dctr": hist_dctr,
        "l12m_dctr": l12m_dctr,
        "pot_hist": pot_hist,
        "pot_l12m": pot_l12m,
        "pot_100": pot_100,
    }
    return ctx


# =============================================================================
# A11.2 — VALUE OF REG E OPT-IN
# =============================================================================


def run_value_2(ctx):
    """A11.2 — Value of Reg E Opt-In: revenue with vs without Reg E."""
    _report(ctx, "\n💰 A11.2 — Value of Reg E Opt-In")
    chart_dir = ctx["chart_dir"]

    # ── Fee configuration ──
    fee_amount = ctx.get("nsf_od_fee", 0.0)
    rate_amount = ctx.get("ic_rate", 0.0)
    _report(ctx, f"   NSF/OD Fee: ${fee_amount:.2f}  |  IC Rate: {rate_amount:.4%}")

    # ── Reg E eligible base (personal + debit) ──
    base = ctx.get("reg_e_eligible_base")
    if base is None or base.empty:
        _report(ctx, "   ⚠️ No Reg E eligible base — skipping A11.2")
        ctx["results"]["value_2"] = {}
        return ctx

    # Get Reg E column and opt-in values — use dynamically resolved column
    lrc = ctx.get("latest_reg_e_column")
    if not lrc:
        # Fallback to config
        lrc = ctx.get("config", {}).get("LatestRegEColumn")
    if not lrc or lrc not in base.columns:
        _report(ctx, "   ⚠️ Reg E column not found — skipping A11.2")
        _report(ctx, f"   ctx key: {ctx.get('latest_reg_e_column')}")
        _report(ctx, f"   config key: {ctx.get('config', {}).get('LatestRegEColumn')}")
        _report(
            ctx,
            f"   Available cols with 'Reg': {[c for c in base.columns if 'reg' in c.lower()][:5]}",
        )
        ctx["results"]["value_2"] = {}
        return ctx

    # Use same opt-in list as reg_e module
    opt_in_raw = ctx.get("reg_e_opt_in", [])
    if isinstance(opt_in_raw, str):
        opt_in_vals = [opt_in_raw]
    elif opt_in_raw:
        opt_in_vals = [str(v).strip() for v in opt_in_raw]
    else:
        # Fallback to config
        opt_in_raw = ctx.get("config", {}).get("RegEOptIn", "Opt In ATM/POS OD Limit")
        opt_in_vals = [opt_in_raw] if isinstance(opt_in_raw, str) else list(opt_in_raw)

    # ── Filter to L12M-active ──
    sd = ctx["start_date"]
    df = base.copy()
    df["Date Closed"] = pd.to_datetime(df["Date Closed"], errors="coerce")
    active = df[df["Date Closed"].isna() | (df["Date Closed"] >= sd)].copy()
    _report(ctx, f"   Active Reg E-eligible accounts in L12M: {len(active):,}")

    # ── Discover spend / items columns ──
    spend_col = _find_col(active, "spend")
    items_col = _find_col(active, "items")
    if not spend_col or not items_col:
        avail = [
            c
            for c in active.columns
            if any(k in c.lower() for k in ["spend", "item", "txn", "trans", "amount", "revenue"])
        ]
        _report(ctx, "   ⚠️ Could not find L12M spend/items columns — skipping A11.2")
        _report(ctx, f"   Available candidates: {avail[:10]}")
        ctx["results"]["value_2"] = {}
        return ctx
    _report(ctx, f"   Spend col: {spend_col}  |  Items col: {items_col}")

    # ── Flag Reg E status ──
    active["Has_RegE"] = active[lrc].astype(str).str.strip().isin(opt_in_vals)

    # ── Revenue calculation ──
    active["NSF/OD Revenue"] = active[items_col].fillna(0) * fee_amount
    active["Interchange Revenue"] = active[spend_col].fillna(0) * rate_amount
    active["Total Revenue"] = active["NSF/OD Revenue"] + active["Interchange Revenue"]

    rev = active.groupby("Has_RegE").agg(
        Accounts=("Has_RegE", "count"),
        NSF_OD=("NSF/OD Revenue", "sum"),
        IC=("Interchange Revenue", "sum"),
        Total=("Total Revenue", "sum"),
        Spend=(spend_col, "sum"),
        Items=(items_col, "sum"),
    )

    if True not in rev.index or False not in rev.index:
        _report(ctx, "   ⚠️ Need both opted-in and opted-out groups")
        return ctx

    # Extract metrics
    aw = int(rev.loc[True, "Accounts"])
    awo = int(rev.loc[False, "Accounts"])
    rw = rev.loc[True, "Total"]
    rwo = rev.loc[False, "Total"]
    rpw = rw / aw if aw else 0
    rpwo = rwo / awo if awo else 0
    nsf_w = rev.loc[True, "NSF_OD"]
    nsf_wo = rev.loc[False, "NSF_OD"]
    ic_w = rev.loc[True, "IC"]
    ic_wo = rev.loc[False, "IC"]
    delta_raw = rpw - rpwo
    delta = round(delta_raw, 2)
    multiplier = rpw / rpwo if rpwo > 0 else 0

    # ── Historical & L12M Reg E rates from A8.1 results ──
    re1 = ctx["results"].get("reg_e_1", {})
    hist_rege = re1.get("opt_in_rate", None)
    if hist_rege is None:
        total = aw + awo
        hist_rege = aw / total if total > 0 else 0.30

    l12m_rege = re1.get("l12m_rate", hist_rege)

    pot_hist = awo * delta * hist_rege
    pot_l12m = awo * delta * l12m_rege

    _report(ctx, f"   Rev/acct WITH Reg E: ${rpw:.2f}  |  WITHOUT: ${rpwo:.2f}  |  Δ ${delta:.2f}")
    _report(ctx, f"   Historical Reg E rate: {hist_rege:.1%}  |  L12M: {l12m_rege:.1%}")
    _report(ctx, f"   Potential (L12M): ${pot_l12m:,.0f}")

    # ── Chart — comparison table ──
    row_data = [
        (8, "Accounts", f"{aw:,}", f"{awo:,}"),
        (6.5, f"NSF/OD Revenue\n(${fee_amount})", f"${nsf_w:,.0f}", f"${nsf_wo:,.0f}"),
        (5, f"Interchange\nRevenue ({rate_amount:.4f})", f"${ic_w:,.0f}", f"${ic_wo:,.0f}"),
        (3.5, "Total Revenue", f"${rw:,.0f}", f"${rwo:,.0f}"),
        (2, "Revenue Per\nAccount", f"${rpw:.2f}", f"${rpwo:.2f}"),
    ]

    try:
        impact = {
            "awo": awo,
            "delta": delta,
            "hist_rate": hist_rege,
            "l12m_rate": l12m_rege,
            "pot_hist": pot_hist,
            "pot_l12m": pot_l12m,
            "pot_100": awo * delta,
            "rate_label": "Reg E",
        }
        fig = _draw_value_slide(
            ctx,
            row_data,
            col1_header="With\nReg E Opt-In",
            col2_header="Without\nReg E Opt-In",
            impact=impact,
        )
        cp = _save_chart(fig, chart_dir / "a11_2_reg_e_value.png")

        subtitle = (
            f"${delta:.2f} more revenue per account — "
            f"${pot_l12m:,.0f} potential at {l12m_rege:.0%} TTM Reg E rate"
        )
        _slide(
            ctx,
            "A11.2 - Value of Reg E Opt-In",
            {
                "title": "Value of Reg E Opt-In",
                "subtitle": subtitle,
                "layout_index": 13,
                "chart_path": cp,
                "category": "Value",
            },
        )
    except Exception as e:
        _report(ctx, f"   ⚠️ Chart: {e}")

    # ── Excel exports ──
    comp_df = pd.DataFrame(
        {
            "Reg E Status": ["With Reg E Opt-In", "Without Reg E Opt-In"],
            "Accounts": [aw, awo],
            "NSF/OD Revenue": [nsf_w, nsf_wo],
            "Interchange Revenue": [ic_w, ic_wo],
            "Total Revenue": [rw, rwo],
            "Revenue Per Account": [rpw, rpwo],
        }
    )
    _save(
        ctx,
        comp_df,
        "A11.2-RegEValue",
        "Value of Reg E Opt-In Analysis",
        {
            "Delta Per Account": f"${delta:.2f}",
            "Accounts Without Reg E": f"{awo:,}",
            "Historical Reg E Rate": f"{hist_rege:.1%}",
            "TTM Reg E Rate": f"{l12m_rege:.1%}",
            "Potential (Historical)": f"${pot_hist:,.0f}",
            "Potential (L12M)": f"${pot_l12m:,.0f}",
        },
    )

    ctx["results"]["value_2"] = {
        "delta": delta,
        "multiplier": multiplier,
        "accts_with": aw,
        "accts_without": awo,
        "rev_per_with": rpw,
        "rev_per_without": rpwo,
        "nsf_w": nsf_w,
        "nsf_wo": nsf_wo,
        "ic_w": ic_w,
        "ic_wo": ic_wo,
        "rev_with": rw,
        "rev_without": rwo,
        "hist_rege": hist_rege,
        "l12m_rege": l12m_rege,
        "pot_hist": pot_hist,
        "pot_l12m": pot_l12m,
    }
    return ctx


# =============================================================================
# SUITE RUNNER
# =============================================================================


def run_value_suite(ctx):
    """Run the full Value analysis suite (A11)."""
    from ars_analysis.pipeline import save_to_excel

    ctx["_save_to_excel"] = save_to_excel

    def _safe(fn, label):
        """Run an analysis function; log errors and continue."""
        try:
            return fn(ctx)
        except Exception as e:
            _report(ctx, f"   ⚠️ {label} failed: {e}")
            import traceback

            traceback.print_exc()
            return ctx

    _report(ctx, "\n" + "=" * 60)
    _report(ctx, "💰 A11 — VALUE ANALYSIS")
    _report(ctx, "=" * 60)

    ctx = _safe(run_value_1, "A11.1 Debit Card Value")
    ctx = _safe(run_value_2, "A11.2 Reg E Value")

    slides = len([s for s in ctx["all_slides"] if s["category"] == "Value"])
    _report(ctx, f"\n✅ A11 complete — {slides} Value slides created")
    return ctx


if __name__ == "__main__":
    print("Value module — import and call run_value_suite(ctx)")
