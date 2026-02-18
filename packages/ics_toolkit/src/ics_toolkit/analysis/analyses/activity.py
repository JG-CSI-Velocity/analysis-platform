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
        name="L12M Activity Summary",
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
