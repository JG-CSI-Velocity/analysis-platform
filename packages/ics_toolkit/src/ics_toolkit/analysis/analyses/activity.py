"""Activity analyses (ax22-ax26): L12M activity KPIs, by source/balance/branch, monthly trends."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.templates import (
    append_grand_total_row,
    kpi_summary,
)
from ics_toolkit.analysis.utils import add_balance_tier, add_l12m_activity
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_activity_summary(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax22: L12M Activity KPIs for ICS Stat O Debit accounts."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)

    total_accounts = len(data)
    active_mask = data["Active in L12M"]
    active_count = int(active_mask.sum())
    pct_active = safe_percentage(active_count, total_accounts)

    total_swipes = int(data["Total L12M Swipes"].sum())
    total_spend = float(data["Total L12M Spend"].sum())

    avg_swipes_all = safe_ratio(total_swipes, total_accounts)
    avg_spend_all = safe_ratio(total_spend, total_accounts)

    active_data = data[active_mask]
    avg_swipes_active = safe_ratio(total_swipes, active_count)
    avg_spend_active = safe_ratio(total_spend, active_count)

    avg_spend_per_swipe = safe_ratio(total_spend, total_swipes)

    avg_bal_all = round(data["Curr Bal"].mean(), 2) if total_accounts > 0 else 0.0
    avg_bal_active = round(active_data["Curr Bal"].mean(), 2) if active_count > 0 else 0.0

    metrics = [
        ("Total Accounts", total_accounts),
        ("Active Accounts", active_count),
        ("% Active", pct_active),
        ("Total Swipes", total_swipes),
        ("Total Spend", round(total_spend, 2)),
        ("Avg Swipes per Account", avg_swipes_all),
        ("Avg Spend per Account", round(avg_spend_all, 2)),
        ("Avg Swipes per Active Account", avg_swipes_active),
        ("Avg Spend per Active Account", round(avg_spend_active, 2)),
        ("Avg Spend per Swipe", round(avg_spend_per_swipe, 2)),
        ("Avg Current Balance (All)", avg_bal_all),
        ("Avg Current Balance (Active)", avg_bal_active),
    ]

    result_df = kpi_summary(metrics)

    return AnalysisResult(
        name="Activity Summary",
        title="ICS Stat O Debit - L12M Activity KPIs",
        df=result_df,
        sheet_name="22_Activity_KPIs",
    )


def analyze_activity_by_debit_source(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax23: Activity breakdown by Debit+Source (ICS Stat O grouped by Source)."""
    data = add_l12m_activity(ics_stat_o.copy(), settings.last_12_months)

    if data.empty:
        result_df = pd.DataFrame(
            columns=[
                "Source",
                "Count",
                "Active Count",
                "Activation Rate",
                "Avg Swipes",
                "Avg Spend",
            ]
        )
        return AnalysisResult(
            name="Activity by Debit+Source",
            title="ICS Stat O - Activity by Source",
            df=result_df,
            sheet_name="23_Activity_Source",
        )

    grouped = (
        data.groupby("Source", dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Active_Count=("Active in L12M", "sum"),
            Total_Swipes=("Total L12M Swipes", "sum"),
            Total_Spend=("Total L12M Spend", "sum"),
        )
        .reset_index()
    )

    grouped["Active Count"] = grouped["Active_Count"].astype(int)
    grouped["Activation Rate"] = grouped.apply(
        lambda row: safe_percentage(row["Active_Count"], row["Count"]), axis=1
    )
    grouped["Avg Swipes"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Swipes"], row["Count"]), axis=1
    )
    grouped["Avg Spend"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Spend"], row["Count"]), axis=1
    )

    result_df = (
        grouped[["Source", "Count", "Active Count", "Activation Rate", "Avg Swipes", "Avg Spend"]]
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Source")

    return AnalysisResult(
        name="Activity by Debit+Source",
        title="ICS Stat O - Activity by Source",
        df=result_df,
        sheet_name="23_Activity_Source",
    )


def analyze_activity_by_balance(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax24: Activity by Balance Tier for ICS Stat O Debit accounts."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)
    data = add_balance_tier(data, settings)

    if data.empty or "Balance Tier" not in data.columns:
        result_df = pd.DataFrame(
            columns=[
                "Balance Tier",
                "Count",
                "Active Count",
                "Activation Rate",
                "Avg Swipes",
            ]
        )
        return AnalysisResult(
            name="Activity by Balance",
            title="ICS Stat O Debit - Activity by Balance Tier",
            df=result_df,
            sheet_name="24_Activity_Bal",
        )

    grouped = (
        data.groupby("Balance Tier", observed=True, dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Active_Count=("Active in L12M", "sum"),
            Total_Swipes=("Total L12M Swipes", "sum"),
        )
        .reset_index()
    )

    grouped["Balance Tier"] = grouped["Balance Tier"].astype(str)
    grouped["Active Count"] = grouped["Active_Count"].astype(int)
    grouped["Activation Rate"] = grouped.apply(
        lambda row: safe_percentage(row["Active_Count"], row["Count"]), axis=1
    )
    grouped["Avg Swipes"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Swipes"], row["Count"]), axis=1
    )

    result_df = grouped[
        ["Balance Tier", "Count", "Active Count", "Activation Rate", "Avg Swipes"]
    ].reset_index(drop=True)

    return AnalysisResult(
        name="Activity by Balance",
        title="ICS Stat O Debit - Activity by Balance Tier",
        df=result_df,
        sheet_name="24_Activity_Bal",
    )


def analyze_activity_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax25: Activity by Branch for ICS Stat O Debit accounts."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)

    if data.empty:
        result_df = pd.DataFrame(
            columns=[
                "Branch",
                "Count",
                "Active Count",
                "Activation %",
                "Avg Swipes",
                "Avg Spend",
            ]
        )
        return AnalysisResult(
            name="Activity by Branch",
            title="ICS Stat O Debit - Activity by Branch",
            df=result_df,
            sheet_name="25_Activity_Branch",
        )

    grouped = (
        data.groupby("Branch", dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Active_Count=("Active in L12M", "sum"),
            Total_Swipes=("Total L12M Swipes", "sum"),
            Total_Spend=("Total L12M Spend", "sum"),
        )
        .reset_index()
    )

    grouped["Active Count"] = grouped["Active_Count"].astype(int)
    grouped["Activation %"] = grouped.apply(
        lambda row: safe_percentage(row["Active_Count"], row["Count"]), axis=1
    )
    grouped["Avg Swipes"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Swipes"], row["Count"]), axis=1
    )
    grouped["Avg Spend"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Spend"], row["Count"]), axis=1
    )

    result_df = (
        grouped[["Branch", "Count", "Active Count", "Activation %", "Avg Swipes", "Avg Spend"]]
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="Activity by Branch",
        title="ICS Stat O Debit - Activity by Branch",
        df=result_df,
        sheet_name="25_Activity_Branch",
    )


def analyze_monthly_trends(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax26: Monthly Trends for ICS Stat O Debit accounts across L12M."""
    data = ics_stat_o_debit.copy()
    rows = []

    for tag in settings.last_12_months:
        swipe_col = f"{tag} Swipes"
        spend_col = f"{tag} Spend"

        total_swipes = 0
        total_spend = 0.0
        active_accounts = 0

        if swipe_col in data.columns:
            total_swipes = int(data[swipe_col].sum())
            active_accounts = int((data[swipe_col] > 0).sum())

        if spend_col in data.columns:
            total_spend = round(float(data[spend_col].sum()), 2)

        rows.append(
            {
                "Month": tag,
                "Total Swipes": total_swipes,
                "Total Spend": total_spend,
                "Active Accounts": active_accounts,
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Monthly Trends",
        title="ICS Stat O Debit - Monthly Activity Trends",
        df=result_df,
        sheet_name="26_Monthly_Trends",
    )


def _source_activity_kpis(
    data: pd.DataFrame, tags: list[str], source_label: str
) -> dict[str, object]:
    """Compute L12M activity KPIs for a single source slice."""
    data = add_l12m_activity(data.copy(), tags)

    total = len(data)
    active_mask = data["Active in L12M"] if not data.empty else pd.Series(dtype=bool)
    active = int(active_mask.sum()) if not data.empty else 0

    swipes = int(data["Total L12M Swipes"].sum()) if not data.empty else 0
    spend = float(data["Total L12M Spend"].sum()) if not data.empty else 0.0

    active_data = data[active_mask] if not data.empty else data

    return {
        "Total Accounts": total,
        "Active Accounts": active,
        "% Active": safe_percentage(active, total),
        "Total Swipes": swipes,
        "Total Spend": round(spend, 2),
        "Avg Swipes / Account": safe_ratio(swipes, total),
        "Avg Spend / Account": round(safe_ratio(spend, total), 2),
        "Avg Swipes / Active": safe_ratio(swipes, active),
        "Avg Spend / Active": round(safe_ratio(spend, active), 2),
        "Avg Spend / Swipe": round(safe_ratio(spend, swipes), 2),
        "Avg Balance (All)": (round(data["Curr Bal"].mean(), 2) if total > 0 else 0.0),
        "Avg Balance (Active)": (round(active_data["Curr Bal"].mean(), 2) if active > 0 else 0.0),
    }


def analyze_activity_by_source_comparison(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax63: L12M Activity KPIs side-by-side for DM vs Referral sources."""
    tags = settings.last_12_months

    dm_data = ics_stat_o_debit[ics_stat_o_debit["Source"] == "DM"]
    ref_data = ics_stat_o_debit[ics_stat_o_debit["Source"] == "REF"]

    dm_kpis = _source_activity_kpis(dm_data, tags, "DM")
    ref_kpis = _source_activity_kpis(ref_data, tags, "REF")

    rows = []
    for metric in dm_kpis:
        rows.append(
            {
                "Metric": metric,
                "DM": dm_kpis[metric],
                "Referral": ref_kpis[metric],
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Activity by Source Comparison",
        title="L12M Activity KPIs - DM vs Referral",
        df=result_df,
        sheet_name="63_Activity_DM_Ref",
    )


def analyze_monthly_interchange(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax71: Monthly interchange revenue trend (spend * interchange_rate)."""
    data = ics_stat_o_debit.copy()
    interchange_rate = settings.interchange_rate
    rows = []

    for tag in settings.last_12_months:
        spend_col = f"{tag} Spend"
        swipe_col = f"{tag} Swipes"

        total_spend = 0.0
        total_swipes = 0

        if spend_col in data.columns:
            total_spend = round(float(data[spend_col].sum()), 2)
        if swipe_col in data.columns:
            total_swipes = int(data[swipe_col].sum())

        interchange = round(total_spend * interchange_rate, 2)

        rows.append(
            {
                "Month": tag,
                "Total Spend": total_spend,
                "Total Swipes": total_swipes,
                "Est. Interchange": interchange,
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Monthly Interchange Trend",
        title="ICS Monthly Interchange Revenue Trend",
        df=result_df,
        sheet_name="71_Monthly_Interchange",
    )


def analyze_business_vs_personal(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax72: Activity KPIs comparing Business vs Personal accounts."""
    if "Business?" not in ics_stat_o_debit.columns:
        return AnalysisResult(
            name="Business vs Personal",
            title="Business vs Personal Card Activity",
            df=kpi_summary([("Status", "No Business? column in data")]),
            sheet_name="72_Biz_vs_Personal",
        )

    tags = settings.last_12_months
    biz_data = ics_stat_o_debit[ics_stat_o_debit["Business?"] == "Yes"]
    pers_data = ics_stat_o_debit[ics_stat_o_debit["Business?"] == "No"]

    biz_kpis = _source_activity_kpis(biz_data, tags, "Business")
    pers_kpis = _source_activity_kpis(pers_data, tags, "Personal")

    rows = []
    for metric in biz_kpis:
        rows.append(
            {
                "Metric": metric,
                "Business": biz_kpis[metric],
                "Personal": pers_kpis[metric],
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Business vs Personal",
        title="Business vs Personal Card Activity",
        df=result_df,
        sheet_name="72_Biz_vs_Personal",
    )
