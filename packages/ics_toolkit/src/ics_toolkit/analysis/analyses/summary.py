"""Summary analyses (ax01-ax07): Total ICS, Open, Stat Code, Prod Code, Debit, cross-tabs."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.analyses.templates import (
    append_grand_total_row,
    crosstab_summary,
    grouped_summary,
)
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_total_ics(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax01: Total ICS accounts in entire dataset."""
    total = len(df)
    ics_count = len(ics_all)
    non_ics = total - ics_count

    result = pd.DataFrame(
        {
            "Category": ["Total Accounts", "ICS Accounts", "Non-ICS Accounts"],
            "Count": [total, ics_count, non_ics],
            "% of Total": [1.0, safe_percentage(ics_count, total), safe_percentage(non_ics, total)],
        }
    )

    return AnalysisResult(
        name="Total ICS Accounts",
        title="ICS Accounts - Total Dataset",
        df=result,
        sheet_name="01_Total_ICS",
    )


def analyze_open_ics(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax02: ICS accounts among open (Stat Code O) accounts."""
    open_accts = df[df["Stat Code"].isin(settings.open_stat_codes)]
    total_open = len(open_accts)
    ics_open = len(ics_stat_o)
    non_ics_open = total_open - ics_open

    result = pd.DataFrame(
        {
            "Category": ["Total Open Accounts", "ICS Accounts", "Non-ICS Accounts"],
            "Count": [total_open, ics_open, non_ics_open],
            "% of Open": [
                1.0,
                safe_percentage(ics_open, total_open),
                safe_percentage(non_ics_open, total_open),
            ],
        }
    )

    return AnalysisResult(
        name="Open ICS Accounts",
        title="ICS Accounts - Open Accounts",
        df=result,
        sheet_name="02_Open_ICS",
    )


def analyze_stat_code(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax03: ICS accounts by Stat Code with optional 'Not in Data Dump'."""
    result = grouped_summary(
        ics_all,
        group_col="Stat Code",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
    )

    # Optionally add "Not in Data Dump" row
    if settings.ics_not_in_dump > 0:
        total_ics = result["Count"].sum()
        not_in_dump = pd.DataFrame(
            {
                "Stat Code": ["Not in Data Dump"],
                "Count": [settings.ics_not_in_dump],
                "% of Count": [safe_percentage(settings.ics_not_in_dump, total_ics)],
            }
        )
        # Put data rows first, then not-in-dump
        result = pd.concat([result, not_in_dump], ignore_index=True)

    result = append_grand_total_row(result, label_col="Stat Code")

    return AnalysisResult(
        name="ICS by Stat Code",
        title="ICS Accounts - Status Code Distribution",
        df=result,
        sheet_name="03_Stat_Code",
    )


def analyze_prod_code(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax04: ICS Stat O accounts by Product Code."""
    result = grouped_summary(
        ics_stat_o,
        group_col="Prod Code",
        agg_specs={"Account Count": ("ICS Account", "size")},
        pct_of=["Account Count"],
    )

    result = append_grand_total_row(result, label_col="Prod Code")

    return AnalysisResult(
        name="Product Code Distribution",
        title="ICS Stat Code O - Product Code Distribution",
        df=result,
        sheet_name="04_Prod_Code",
    )


def analyze_debit_dist(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax05: ICS Stat O accounts by Debit Card status."""
    result = grouped_summary(
        ics_stat_o,
        group_col="Debit?",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
        label_map={"Yes": "Yes", "No": "No"},
    )

    result = append_grand_total_row(result, label_col="Debit?")

    return AnalysisResult(
        name="Debit Distribution",
        title="ICS Stat Code O - Debit Card Distribution",
        df=result,
        sheet_name="05_Debit_Dist",
    )


def analyze_debit_by_prod(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax06: ICS Stat O Debit by Product Code (cross-tab)."""
    result = crosstab_summary(
        ics_stat_o,
        row_col="Prod Code",
        col_col="Debit?",
        add_totals=True,
        add_rate_col="% with Debit",
        rate_numerator="Yes",
    )

    return AnalysisResult(
        name="Debit x Prod Code",
        title="ICS Stat Code O - Debit by Product Code",
        df=result,
        sheet_name="06_Debit_x_Prod",
    )


def analyze_debit_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax07: ICS Stat O Debit by Branch (cross-tab)."""
    result = crosstab_summary(
        ics_stat_o,
        row_col="Branch",
        col_col="Debit?",
        add_totals=True,
        add_rate_col="% with Debit",
        rate_numerator="Yes",
    )

    return AnalysisResult(
        name="Debit x Branch",
        title="ICS Stat Code O - Debit by Branch",
        df=result,
        sheet_name="07_Debit_x_Branch",
    )


def analyze_penetration_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax64: ICS penetration rate by branch (ICS accounts / total accounts)."""
    if "Branch" not in df.columns:
        return AnalysisResult(
            name="ICS Penetration by Branch",
            title="ICS Penetration by Branch",
            df=pd.DataFrame(columns=["Branch", "Total Accounts", "ICS Accounts", "Penetration %"]),
            sheet_name="64_Penetration_Branch",
        )

    total_by_branch = df.groupby("Branch", dropna=False).size().reset_index(name="Total Accounts")
    ics_by_branch = ics_all.groupby("Branch", dropna=False).size().reset_index(name="ICS Accounts")

    result_df = total_by_branch.merge(ics_by_branch, on="Branch", how="left").fillna(0)
    result_df["ICS Accounts"] = result_df["ICS Accounts"].astype(int)
    result_df["Penetration %"] = result_df.apply(
        lambda row: safe_percentage(row["ICS Accounts"], row["Total Accounts"]), axis=1
    )

    result_df = result_df.sort_values("Total Accounts", ascending=False).reset_index(drop=True)
    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="ICS Penetration by Branch",
        title="ICS Penetration Rate by Branch",
        df=result_df,
        sheet_name="64_Penetration_Branch",
    )
