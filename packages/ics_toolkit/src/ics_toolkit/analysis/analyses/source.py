"""Source analyses (ax08-ax13): Source distribution, cross-tabs, account type, year opened."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.analyses.templates import (
    append_grand_total_row,
    crosstab_summary,
    grouped_summary,
)
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_source_dist(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax08: ICS accounts grouped by Source with count and percentage."""
    result = grouped_summary(
        ics_all,
        group_col="Source",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
    )

    result = append_grand_total_row(result, label_col="Source")

    return AnalysisResult(
        name="Source Distribution",
        title="ICS Accounts - Source Distribution",
        df=result,
        sheet_name="08_Source_Dist",
    )


def analyze_source_by_stat(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax09: Cross-tab of Source x Stat Code for ICS accounts."""
    result = crosstab_summary(
        ics_all,
        row_col="Source",
        col_col="Stat Code",
        add_totals=True,
    )

    return AnalysisResult(
        name="Source x Stat Code",
        title="ICS Accounts - Source by Stat Code",
        df=result,
        sheet_name="09_Source_x_Stat",
    )


def analyze_source_by_prod(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax10: Cross-tab of Source x Prod Code for ICS Stat O accounts."""
    result = crosstab_summary(
        ics_stat_o,
        row_col="Source",
        col_col="Prod Code",
        add_totals=True,
    )

    return AnalysisResult(
        name="Source x Prod Code",
        title="ICS Stat Code O - Source by Product Code",
        df=result,
        sheet_name="10_Source_x_Prod",
    )


def analyze_source_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax11: Cross-tab of Source x Branch for ICS Stat O accounts."""
    result = crosstab_summary(
        ics_stat_o,
        row_col="Source",
        col_col="Branch",
        add_totals=True,
    )

    return AnalysisResult(
        name="Source x Branch",
        title="ICS Stat Code O - Source by Branch",
        df=result,
        sheet_name="11_Source_x_Branch",
    )


def analyze_account_type(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax12: ICS Stat O accounts by account type (Business/Personal)."""
    result = grouped_summary(
        ics_stat_o,
        group_col="Business?",
        agg_specs={"Count": ("ICS Account", "size")},
        pct_of=["Count"],
        label_map={"Yes": "Business", "No": "Personal"},
    )

    result = append_grand_total_row(result, label_col="Business?")

    return AnalysisResult(
        name="Account Type",
        title="ICS Stat Code O - Account Type Distribution",
        df=result,
        sheet_name="12_Account_Type",
    )


def analyze_source_by_year(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax13: ICS Stat O accounts cross-tabbed by Source and Year Opened."""
    data = ics_stat_o.copy()

    if "Date Opened" in data.columns:
        data["Year Opened"] = data["Date Opened"].dt.year.astype(str)
    else:
        data["Year Opened"] = "Unknown"

    result = crosstab_summary(
        data,
        row_col="Source",
        col_col="Year Opened",
        add_totals=True,
    )

    return AnalysisResult(
        name="Source by Year",
        title="ICS Stat Code O - Source by Year Opened",
        df=result,
        sheet_name="13_Source_x_Year",
    )
