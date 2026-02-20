"""Demographics analyses (ax14-ax21): Age, closures, balances, tiers, distributions."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.templates import (
    append_grand_total_row,
    binned_summary,
    grouped_summary,
    kpi_summary,
)
from ics_toolkit.analysis.utils import add_account_age, add_age_range
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_age_comparison(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax14: Compare ICS vs Non-ICS account age distributions using age bins."""
    data = ics_stat_o.copy()
    data = add_account_age(data)
    data = add_age_range(data, settings)

    result = binned_summary(
        data,
        value_col="Account Age Days",
        bins=settings.age_ranges.bins,
        labels=settings.age_ranges.labels,
        bin_name="Age Range",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
    )

    return AnalysisResult(
        name="Age Comparison",
        title="ICS Stat Code O - Account Age Distribution",
        df=result,
        sheet_name="14_Age_Comparison",
    )


def analyze_closures(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax15: ICS accounts closed (Stat Code C) grouped by month closed."""
    closed = ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)].copy()

    if "Date Closed" in closed.columns and not closed.empty:
        closed["Month Closed"] = closed["Date Closed"].dt.to_period("M").astype(str)
    else:
        closed["Month Closed"] = "Unknown"

    result = grouped_summary(
        closed,
        group_col="Month Closed",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
        sort_by="Month Closed",
        sort_ascending=True,
    )

    result = append_grand_total_row(result, label_col="Month Closed")

    return AnalysisResult(
        name="Closures",
        title="ICS Accounts - Closures by Month",
        df=result,
        sheet_name="15_Closures",
    )


def analyze_open_vs_close(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax16: ICS accounts by Open (O) vs Closed (C) status."""
    total = len(ics_all)
    open_count = len(ics_all[ics_all["Stat Code"].isin(settings.open_stat_codes)])
    closed_count = len(ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)])

    metrics = [
        ("Total ICS Accounts", total),
        ("Open (Stat Code O)", open_count),
        ("Closed (Stat Code C)", closed_count),
        ("% Open", safe_percentage(open_count, total)),
        ("% Closed", safe_percentage(closed_count, total)),
    ]

    result = kpi_summary(metrics)

    return AnalysisResult(
        name="Open vs Close",
        title="ICS Accounts - Open vs Closed",
        df=result,
        sheet_name="16_Open_vs_Close",
    )


def analyze_balance_tiers(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax17: ICS Stat O accounts binned by Curr Bal into balance tiers."""
    result = binned_summary(
        ics_stat_o,
        value_col="Curr Bal",
        bins=settings.balance_tiers.bins,
        labels=settings.balance_tiers.labels,
        bin_name="Balance Tier",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
    )

    return AnalysisResult(
        name="Balance Tiers",
        title="ICS Stat Code O - Balance Tier Distribution",
        df=result,
        sheet_name="17_Balance_Tiers",
    )


def analyze_stat_open_close(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax18: ICS accounts grouped by Stat Code with avg balance and count."""
    result = grouped_summary(
        ics_all,
        group_col="Stat Code",
        agg_specs={
            "Count": ("ICS Account", "size"),
            "Avg Curr Bal": ("Curr Bal", "mean"),
        },
        pct_of=["Count"],
    )

    result["Avg Curr Bal"] = result["Avg Curr Bal"].round(2)
    result = append_grand_total_row(result, label_col="Stat Code")

    return AnalysisResult(
        name="Stat Open Close",
        title="ICS Accounts - Open/Close by Stat Code",
        df=result,
        sheet_name="18_Stat_Open_Close",
    )


def analyze_age_vs_balance(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax19: ICS Stat O accounts, age bins with average balance per tier."""
    data = ics_stat_o.copy()
    data = add_account_age(data)

    result = binned_summary(
        data,
        value_col="Account Age Days",
        bins=settings.age_ranges.bins,
        labels=settings.age_ranges.labels,
        bin_name="Age Range",
        agg_specs={
            "Count": ("ICS Account", "size"),
            "Avg Curr Bal": ("Curr Bal", "mean"),
        },
    )

    result["Avg Curr Bal"] = result["Avg Curr Bal"].round(2)

    return AnalysisResult(
        name="Age vs Balance",
        title="ICS Stat Code O - Age vs Average Balance",
        df=result,
        sheet_name="19_Age_vs_Balance",
    )


def analyze_balance_tier_detail(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax20: ICS Stat O Debit accounts binned by balance with usage detail."""
    data = ics_stat_o_debit.copy()

    # Ensure L12M columns exist for aggregation
    if "Total L12M Swipes" not in data.columns:
        data["Total L12M Swipes"] = 0
    if "Total L12M Spend" not in data.columns:
        data["Total L12M Spend"] = 0.0

    result = binned_summary(
        data,
        value_col="Curr Bal",
        bins=settings.balance_tiers.bins,
        labels=settings.balance_tiers.labels,
        bin_name="Balance Tier",
        agg_specs={
            "Count": ("ICS Account", "size"),
            "Avg Swipes": ("Total L12M Swipes", "mean"),
            "Avg Spend": ("Total L12M Spend", "mean"),
        },
        pct_of=["Count"],
    )

    result["Avg Swipes"] = result["Avg Swipes"].round(1)
    result["Avg Spend"] = result["Avg Spend"].round(2)

    return AnalysisResult(
        name="Balance Tier Detail",
        title="ICS Stat Code O Debit - Balance Tier Detail",
        df=result,
        sheet_name="20_Bal_Tier_Detail",
    )


def analyze_age_dist(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax21: ICS Stat O accounts by age range with count and percentage."""
    data = ics_stat_o.copy()
    data = add_account_age(data)

    result = binned_summary(
        data,
        value_col="Account Age Days",
        bins=settings.age_ranges.bins,
        labels=settings.age_ranges.labels,
        bin_name="Age Range",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
    )

    return AnalysisResult(
        name="Age Distribution",
        title="ICS Stat Code O - Age Distribution",
        df=result,
        sheet_name="21_Age_Dist",
    )


def analyze_balance_trajectory(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax83: Balance trajectory -- Avg Bal vs Curr Bal by branch.

    Shows whether accounts are growing or draining balances.
    """
    if "Avg Bal" not in ics_stat_o.columns:
        return AnalysisResult(
            name="Balance Trajectory",
            title="ICS Balance Trajectory (Avg Bal vs Curr Bal)",
            df=kpi_summary([("Status", "No Avg Bal column in data")]),
            sheet_name="83_Bal_Trajectory",
        )

    data = ics_stat_o.copy()

    if "Branch" not in data.columns:
        data["Branch"] = "All"

    grouped = (
        data.groupby("Branch", dropna=False)
        .agg(
            Accounts=("Branch", "size"),
            Avg_AvgBal=("Avg Bal", "mean"),
            Avg_CurrBal=("Curr Bal", "mean"),
        )
        .reset_index()
    )

    grouped["Avg Bal"] = grouped["Avg_AvgBal"].round(2)
    grouped["Curr Bal"] = grouped["Avg_CurrBal"].round(2)
    grouped["Change ($)"] = (grouped["Avg_CurrBal"] - grouped["Avg_AvgBal"]).round(2)
    grouped["Change (%)"] = grouped.apply(
        lambda row: (
            round(safe_ratio(row["Change ($)"], row["Avg Bal"]) * 100, 1)
            if row["Avg Bal"] != 0
            else 0.0
        ),
        axis=1,
    )

    result_df = (
        grouped[["Branch", "Accounts", "Avg Bal", "Curr Bal", "Change ($)", "Change (%)"]]
        .sort_values("Accounts", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="Balance Trajectory",
        title="ICS Balance Trajectory (Avg Bal vs Curr Bal)",
        df=result_df,
        sheet_name="83_Bal_Trajectory",
    )
