"""Shared DCTR utilities -- calculations, categorization, breakdowns.

All functions are pure (no side effects, no ctx mutation).
Ported from ars_analysis-jupyter/dctr.py.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

# -- Category orders (used by by_dimension / crosstab) -----------------------

AGE_ORDER = [
    "0-6 months", "6-12 months", "1-2 years",
    "2-5 years", "5-10 years", "10+ years",
]
HOLDER_AGE_ORDER = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
BALANCE_ORDER = [
    "Negative", "$0-$499", "$500-$999", "$1K-$2.5K", "$2.5K-$5K",
    "$5K-$10K", "$10K-$25K", "$25K-$50K", "$50K-$100K", "$100K+",
]

# -- Core DCTR calculation ---------------------------------------------------


def dctr(df: pd.DataFrame, debit_col: str = "Debit?", yes: str = "Yes") -> tuple[int, int, float]:
    """Return (total, with_debit, rate) for a DataFrame."""
    total = len(df)
    with_debit = len(df[df[debit_col] == yes])
    return total, with_debit, (with_debit / total if total > 0 else 0.0)


def total_row(df: pd.DataFrame, label_col: str, label: str = "TOTAL") -> pd.DataFrame:
    """Append a TOTAL row. Recalculates DCTR % from With Debit / Total Accounts."""
    if df.empty:
        return df
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    totals: dict = {label_col: label}
    for c in num_cols:
        if "DCTR" in c or "%" in c:
            wd = df["With Debit"].sum() if "With Debit" in df.columns else 0
            ta = df["Total Accounts"].sum() if "Total Accounts" in df.columns else 0
            totals[c] = wd / ta if ta > 0 else 0
        else:
            totals[c] = df[c].sum()
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)


# -- Categorization functions ------------------------------------------------


def categorize_account_age(days: float) -> str:
    if pd.isna(days):
        return "Unknown"
    if days < 180:
        return "0-6 months"
    if days < 365:
        return "6-12 months"
    if days < 730:
        return "1-2 years"
    if days < 1825:
        return "2-5 years"
    if days < 3650:
        return "5-10 years"
    return "10+ years"


def categorize_holder_age(age: float) -> str:
    if pd.isna(age):
        return "Unknown"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"


def categorize_balance(bal: float) -> str:
    if pd.isna(bal):
        return "Unknown"
    if bal < 0:
        return "Negative"
    if bal < 500:
        return "$0-$499"
    if bal < 1000:
        return "$500-$999"
    if bal < 2500:
        return "$1K-$2.5K"
    if bal < 5000:
        return "$2.5K-$5K"
    if bal < 10000:
        return "$5K-$10K"
    if bal < 25000:
        return "$10K-$25K"
    if bal < 50000:
        return "$25K-$50K"
    if bal < 100000:
        return "$50K-$100K"
    return "$100K+"


def simplify_account_age(age_range: str) -> str:
    if age_range in ("0-6 months", "6-12 months"):
        return "New (0-1 year)"
    if age_range in ("1-2 years", "2-5 years"):
        return "Recent (1-5 years)"
    if age_range in ("5-10 years", "10+ years"):
        return "Mature (5+ years)"
    return "Unknown"


def map_to_decade(year: float) -> str | None:
    if pd.isna(year):
        return None
    recent = list(range(2020, 2027))
    if year < 1970:
        return "Before 1970"
    if int(year) in recent:
        return str(int(year))
    return f"{(int(year) // 10) * 10}s"


# -- L12M helpers ------------------------------------------------------------


def l12m_month_labels(end_date: date) -> list[str]:
    """Generate 12 month labels (e.g. 'Jan25') from end_date backwards."""
    labels = []
    for i in range(11, -1, -1):
        dt = end_date - relativedelta(months=i)
        labels.append(dt.strftime("%b%y"))
    return labels


def filter_l12m(
    df: pd.DataFrame, start_date: date, end_date: date,
) -> pd.DataFrame:
    """Filter DataFrame to L12M window using Date Opened."""
    if df is None or df.empty:
        return pd.DataFrame()
    dc = df.copy()
    dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
    mask = (dc["Date Opened"] >= str(start_date)) & (dc["Date Opened"] <= str(end_date))
    return dc[mask]


# -- Core analysis functions -------------------------------------------------


def analyze_historical_dctr(
    dataset: pd.DataFrame, name: str = "Eligible",
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Yearly + decade DCTR breakdown. Returns (yearly_df, decade_df, insights)."""
    empty_ins = {
        "total_accounts": 0, "with_debit_count": 0,
        "overall_dctr": 0, "recent_dctr": 0, "years_covered": 0,
    }
    if dataset.empty:
        return pd.DataFrame(), pd.DataFrame(), empty_ins

    df = dataset.copy()
    df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce")
    df["Year"] = df["Date Opened"].dt.year
    valid = df.dropna(subset=["Year"])
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame(), empty_ins

    valid = valid.copy()
    valid["Decade"] = valid["Year"].apply(map_to_decade)

    # Yearly breakdown
    rows = []
    for yr in sorted(valid["Year"].dropna().unique()):
        yd = valid[valid["Year"] == yr]
        t, w, d = dctr(yd)
        p = yd[yd["Business?"] == "No"]
        b = yd[yd["Business?"] == "Yes"]
        rows.append({
            "Year": int(yr), "Total Accounts": t, "With Debit": w,
            "Without Debit": t - w, "DCTR %": d,
            "Personal w/Debit": len(p[p["Debit?"] == "Yes"]),
            "Business w/Debit": len(b[b["Debit?"] == "Yes"]),
        })
    yearly = pd.DataFrame(rows)
    if not yearly.empty:
        yearly = total_row(yearly, "Year")

    # Decade breakdown
    drows = []
    decade_keys = sorted(
        valid["Decade"].dropna().unique(),
        key=lambda x: int(x) if x.isdigit() else (0 if "Before" in str(x) else int(str(x).replace("s", ""))),
    )
    for dec in decade_keys:
        dd = valid[valid["Decade"] == dec]
        t, w, d = dctr(dd)
        drows.append({
            "Decade": dec, "Total Accounts": t, "With Debit": w,
            "Without Debit": t - w, "DCTR %": d,
        })
    decade = pd.DataFrame(drows)

    t_all, w_all, o_dctr = dctr(valid)
    recent = valid[valid["Year"].isin([2023, 2024, 2025, 2026])]
    _, _, r_dctr = dctr(recent) if len(recent) else (0, 0, 0)

    return yearly, decade, {
        "total_accounts": t_all, "with_debit_count": w_all,
        "overall_dctr": o_dctr, "recent_dctr": r_dctr,
        "years_covered": len(rows),
    }


def l12m_monthly(
    dataset: pd.DataFrame, months: list[str],
) -> tuple[pd.DataFrame, dict]:
    """Monthly DCTR table for L12M accounts."""
    empty_ins = {"total_accounts": 0, "with_debit": 0, "dctr": 0, "months_active": 0}
    if dataset.empty:
        return pd.DataFrame(), empty_ins

    dc = dataset.copy()
    dc["Date Opened"] = pd.to_datetime(dc["Date Opened"], errors="coerce")
    dc["Month_Year"] = dc["Date Opened"].dt.strftime("%b%y")

    rows = []
    for my in months:
        ma = dc[dc["Month_Year"] == my]
        t, w, d = dctr(ma)
        rows.append({
            "Month": my, "Total Accounts": t, "With Debit": w,
            "Without Debit": t - w, "DCTR %": d,
        })
    monthly = pd.DataFrame(rows)
    if not monthly.empty:
        monthly = total_row(monthly, "Month")

    active = sum(1 for r in rows if r["Total Accounts"] > 0)
    ta = monthly[monthly["Month"] == "TOTAL"]["Total Accounts"].iloc[0] if not monthly.empty else 0
    tw = monthly[monthly["Month"] == "TOTAL"]["With Debit"].iloc[0] if not monthly.empty else 0
    return monthly, {
        "total_accounts": int(ta), "with_debit": int(tw),
        "dctr": tw / ta if ta else 0, "months_active": active,
    }


def branch_dctr(
    dataset: pd.DataFrame, branch_mapping: dict | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Per-branch DCTR breakdown. Returns (branch_df, insights)."""
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
        t, w, d = dctr(ba)
        rows.append({
            "Branch": bn, "Total Accounts": t, "With Debit": w,
            "Without Debit": t - w, "DCTR %": d,
        })
    bdf = pd.DataFrame(rows).sort_values("DCTR %", ascending=False)
    if not bdf.empty:
        bdf = total_row(bdf, "Branch")

    dr = bdf[bdf["Branch"] != "TOTAL"]
    ins: dict = {}
    if not dr.empty:
        best = dr.loc[dr["DCTR %"].idxmax()]
        worst = dr.loc[dr["DCTR %"].idxmin()]
        ins = {
            "total_branches": len(dr),
            "best_branch": best["Branch"], "best_dctr": best["DCTR %"],
            "worst_branch": worst["Branch"], "worst_dctr": worst["DCTR %"],
        }
    return bdf, ins


def by_dimension(
    dataset: pd.DataFrame, col: str, cat_fn, order: list[str], label: str,
) -> tuple[pd.DataFrame, dict]:
    """Generic dimensional DCTR breakdown with P/B split."""
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
        t, w, d = dctr(seg)
        p = seg[seg["Business?"] == "No"]
        b = seg[seg["Business?"] == "Yes"]
        rows.append({
            label: cat, "Total Accounts": t, "With Debit": w,
            "Without Debit": t - w, "DCTR %": d,
            "Personal w/Debit": len(p[p["Debit?"] == "Yes"]),
            "Business w/Debit": len(b[b["Debit?"] == "Yes"]),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = total_row(df, label)

    dr = df[df[label] != "TOTAL"]
    ins: dict = {}
    if not dr.empty:
        hi = dr.loc[dr["DCTR %"].idxmax()]
        lo = dr.loc[dr["DCTR %"].idxmin()]
        ins = {
            "highest": hi[label], "highest_dctr": hi["DCTR %"],
            "lowest": lo[label], "lowest_dctr": lo["DCTR %"],
            "spread": hi["DCTR %"] - lo["DCTR %"],
            "total_with_data": len(valid),
            "coverage": len(valid) / len(dataset) if len(dataset) else 0,
        }
    return df, ins


def crosstab_dctr(
    dataset: pd.DataFrame,
    row_col: str, row_fn, row_order: list[str], row_label: str,
    col_col: str, col_fn, col_order: list[str], col_label: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Cross-tab DCTR: detail, DCTR pivot, count pivot, insights."""
    if dataset.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}
    dc = dataset.copy()
    dc[row_label] = dc[row_col].apply(row_fn)
    dc[col_label] = dc[col_col].apply(col_fn)
    valid = dc[(dc[row_label] != "Unknown") & (dc[col_label] != "Unknown")]

    rows = []
    for r in row_order:
        for c in col_order:
            seg = valid[(valid[row_label] == r) & (valid[col_label] == c)]
            if len(seg) > 0:
                t, w, d = dctr(seg)
                rows.append({row_label: r, col_label: c, "Total Accounts": t, "With Debit": w, "DCTR %": d})
    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, pd.DataFrame(), pd.DataFrame(), {}

    dp = detail.pivot_table(index=row_label, columns=col_label, values="DCTR %")
    cp = detail.pivot_table(index=row_label, columns=col_label, values="Total Accounts")
    dp = dp.reindex(index=[x for x in row_order if x in dp.index],
                    columns=[x for x in col_order if x in dp.columns])
    cp = cp.reindex(index=[x for x in row_order if x in cp.index],
                    columns=[x for x in col_order if x in cp.columns])

    meaningful = detail[detail["Total Accounts"] > 10]
    ins: dict = {}
    if not meaningful.empty:
        hi = meaningful.loc[meaningful["DCTR %"].idxmax()]
        lo = meaningful.loc[meaningful["DCTR %"].idxmin()]
        ins = {
            "highest_seg": f"{hi[row_label]} x {hi[col_label]}",
            "highest_dctr": hi["DCTR %"],
            "lowest_seg": f"{lo[row_label]} x {lo[col_label]}",
            "lowest_dctr": lo["DCTR %"],
            "segments": len(detail),
        }
    return detail, dp, cp, ins
