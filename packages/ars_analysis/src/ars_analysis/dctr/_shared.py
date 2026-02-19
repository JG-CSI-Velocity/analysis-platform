"""Shared DCTR computation functions used by core and visualization modules."""

import pandas as pd

from ars_analysis.dctr._categories import map_to_decade
from ars_analysis.dctr._helpers import _dctr, _total_row

# =============================================================================
# CORE: analyze_historical_dctr
# =============================================================================


def analyze_historical_dctr(dataset, name="Eligible"):
    """Returns (yearly_df, decade_df, insights_dict)."""
    if dataset.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {"total_accounts": 0, "with_debit_count": 0, "overall_dctr": 0, "recent_dctr": 0},
        )

    df = dataset.copy()
    df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce")
    df["Year"] = df["Date Opened"].dt.year
    valid = df.dropna(subset=["Year"])
    if valid.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            {"total_accounts": 0, "with_debit_count": 0, "overall_dctr": 0, "recent_dctr": 0},
        )

    valid = valid.copy()
    valid["Decade"] = valid["Year"].apply(map_to_decade)

    # Yearly
    rows = []
    for yr in sorted(valid["Year"].dropna().unique()):
        yd = valid[valid["Year"] == yr]
        t, w, d = _dctr(yd)
        p = yd[yd["Business?"] == "No"]
        b = yd[yd["Business?"] == "Yes"]
        rows.append(
            {
                "Year": int(yr),
                "Total Accounts": t,
                "With Debit": w,
                "Without Debit": t - w,
                "DCTR %": d,
                "Personal w/Debit": len(p[p["Debit?"] == "Yes"]),
                "Business w/Debit": len(b[b["Debit?"] == "Yes"]),
            }
        )
    yearly = pd.DataFrame(rows)
    if not yearly.empty:
        yearly = _total_row(yearly, "Year")

    # Decade
    drows = []
    decade_keys = sorted(
        valid["Decade"].dropna().unique(),
        key=lambda x: (
            int(x) if x.isdigit() else (0 if "Before" in str(x) else int(str(x).replace("s", "")))
        ),
    )
    for dec in decade_keys:
        dd = valid[valid["Decade"] == dec]
        t, w, d = _dctr(dd)
        drows.append(
            {
                "Decade": dec,
                "Total Accounts": t,
                "With Debit": w,
                "Without Debit": t - w,
                "DCTR %": d,
            }
        )
    decade = pd.DataFrame(drows)

    # Overall insights
    t_all, w_all, o_dctr = _dctr(valid)
    recent = valid[valid["Year"].isin([2023, 2024, 2025, 2026])]
    _, _, r_dctr = _dctr(recent) if len(recent) else (0, 0, 0)

    return (
        yearly,
        decade,
        {
            "total_accounts": t_all,
            "with_debit_count": w_all,
            "overall_dctr": o_dctr,
            "recent_dctr": r_dctr,
            "years_covered": len(rows),
        },
    )


# =============================================================================
# CORE: L12M monthly breakdown
# =============================================================================


def _l12m_monthly(dataset, last_12_months):
    """Monthly DCTR table for L12M accounts."""
    if dataset.empty:
        return pd.DataFrame(), {"total_accounts": 0, "with_debit": 0, "dctr": 0, "months_active": 0}

    dc = dataset.copy()
    dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
    dc["Month_Year"] = dc["Date Opened"].dt.strftime("%b%y")

    rows = []
    for my in last_12_months:
        ma = dc[dc["Month_Year"] == my]
        t, w, d = _dctr(ma)
        rows.append(
            {"Month": my, "Total Accounts": t, "With Debit": w, "Without Debit": t - w, "DCTR %": d}
        )
    monthly = pd.DataFrame(rows)
    if not monthly.empty:
        monthly = _total_row(monthly, "Month")

    active = sum(1 for r in rows if r["Total Accounts"] > 0)
    ta = monthly[monthly["Month"] == "TOTAL"]["Total Accounts"].iloc[0] if not monthly.empty else 0
    tw = monthly[monthly["Month"] == "TOTAL"]["With Debit"].iloc[0] if not monthly.empty else 0
    return monthly, {
        "total_accounts": int(ta),
        "with_debit": int(tw),
        "dctr": tw / ta if ta else 0,
        "months_active": active,
    }


# =============================================================================
# CORE: branch DCTR
# =============================================================================


def _branch_dctr(dataset, branch_mapping=None):
    if dataset.empty:
        return pd.DataFrame(), {}
    dc = dataset.copy()
    if branch_mapping:
        dc["Branch Name"] = dc["Branch"].map(branch_mapping).fillna(dc["Branch"])
    else:
        dc["Branch Name"] = dc["Branch"]

    rows = []
    for bn in sorted(dc["Branch Name"].unique()):
        ba = dc[dc["Branch Name"] == bn]
        t, w, d = _dctr(ba)
        rows.append(
            {
                "Branch": bn,
                "Total Accounts": t,
                "With Debit": w,
                "Without Debit": t - w,
                "DCTR %": d,
            }
        )
    bdf = pd.DataFrame(rows).sort_values("DCTR %", ascending=False)
    if not bdf.empty:
        bdf = _total_row(bdf, "Branch")

    dr = bdf[bdf["Branch"] != "TOTAL"]
    ins = {}
    if not dr.empty:
        best = dr.loc[dr["DCTR %"].idxmax()]
        worst = dr.loc[dr["DCTR %"].idxmin()]
        ins = {
            "total_branches": len(dr),
            "best_branch": best["Branch"],
            "best_dctr": best["DCTR %"],
            "worst_branch": worst["Branch"],
            "worst_dctr": worst["DCTR %"],
        }
    return bdf, ins


# =============================================================================
# CORE: dimension DCTR
# =============================================================================


def _by_dimension(dataset, col, cat_fn, order, label):
    if dataset.empty:
        return pd.DataFrame(), {}
    dc = dataset.copy()
    dc[label] = dc[col].apply(cat_fn)
    valid = dc[dc[label] != "Unknown"]

    rows = []
    for cat in order:
        seg = valid[valid[label] == cat]
        if len(seg) == 0:
            continue
        t, w, d = _dctr(seg)
        p = seg[seg["Business?"] == "No"]
        b = seg[seg["Business?"] == "Yes"]
        rows.append(
            {
                label: cat,
                "Total Accounts": t,
                "With Debit": w,
                "Without Debit": t - w,
                "DCTR %": d,
                "Personal w/Debit": len(p[p["Debit?"] == "Yes"]),
                "Business w/Debit": len(b[b["Debit?"] == "Yes"]),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = _total_row(df, label)

    dr = df[df[label] != "TOTAL"]
    ins = {}
    if not dr.empty:
        hi = dr.loc[dr["DCTR %"].idxmax()]
        lo = dr.loc[dr["DCTR %"].idxmin()]
        ins = {
            "highest": hi[label],
            "highest_dctr": hi["DCTR %"],
            "lowest": lo[label],
            "lowest_dctr": lo["DCTR %"],
            "spread": hi["DCTR %"] - lo["DCTR %"],
            "total_with_data": len(valid),
            "coverage": len(valid) / len(dataset) if len(dataset) else 0,
        }
    return df, ins


# =============================================================================
# CORE: cross-tab
# =============================================================================


def _crosstab(dataset, rc, rfn, ro, rl, cc, cfn, co, cl):
    if dataset.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}
    dc = dataset.copy()
    dc[rl] = dc[rc].apply(rfn)
    dc[cl] = dc[cc].apply(cfn)
    valid = dc[(dc[rl] != "Unknown") & (dc[cl] != "Unknown")]

    rows = []
    for r in ro:
        for c in co:
            seg = valid[(valid[rl] == r) & (valid[cl] == c)]
            if len(seg) > 0:
                t, w, d = _dctr(seg)
                rows.append({rl: r, cl: c, "Total Accounts": t, "With Debit": w, "DCTR %": d})
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, pd.DataFrame(), pd.DataFrame(), {}

    dp = detail.pivot_table(index=rl, columns=cl, values="DCTR %")
    cp = detail.pivot_table(index=rl, columns=cl, values="Total Accounts")
    dp = dp.reindex(
        index=[x for x in ro if x in dp.index], columns=[x for x in co if x in dp.columns]
    )
    cp = cp.reindex(
        index=[x for x in ro if x in cp.index], columns=[x for x in co if x in cp.columns]
    )

    meaningful = detail[detail["Total Accounts"] > 10]
    ins = {}
    if not meaningful.empty:
        hi = meaningful.loc[meaningful["DCTR %"].idxmax()]
        lo = meaningful.loc[meaningful["DCTR %"].idxmin()]
        ins = {
            "highest_seg": f"{hi[rl]} × {hi[cl]}",
            "highest_dctr": hi["DCTR %"],
            "lowest_seg": f"{lo[rl]} × {lo[cl]}",
            "lowest_dctr": lo["DCTR %"],
            "segments": len(detail),
        }
    return detail, dp, cp, ins
