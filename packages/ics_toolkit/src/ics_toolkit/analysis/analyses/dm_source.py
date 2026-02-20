"""DM Source deep-dive analyses (ax45-ax52)."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.templates import append_grand_total_row, kpi_summary
from ics_toolkit.analysis.utils import add_l12m_activity
from ics_toolkit.settings import AnalysisSettings as Settings

DM = "DM"


def _dm_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Source == 'DM' rows."""
    return df[df["Source"] == DM].copy()


def analyze_dm_overview(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax45: DM Overview KPIs -- total, open/closed, debit, balance, L12M activity."""
    dm_all = _dm_filter(ics_all)
    dm_open = dm_all[dm_all["Stat Code"].isin(settings.open_stat_codes)]
    dm_closed = dm_all[~dm_all["Stat Code"].isin(settings.open_stat_codes)]
    dm_debit = dm_open[dm_open["Debit?"] == "Yes"]

    total_dm = len(dm_all)
    total_ics = len(ics_all)
    open_count = len(dm_open)
    closed_count = len(dm_closed)
    debit_count = len(dm_debit)

    dm_open_activity = add_l12m_activity(dm_open.copy(), settings.last_12_months)
    if not dm_open_activity.empty:
        total_swipes = int(dm_open_activity["Total L12M Swipes"].sum())
        total_spend = round(float(dm_open_activity["Total L12M Spend"].sum()), 2)
    else:
        total_swipes = 0
        total_spend = 0.0

    metrics = [
        ("Total DM Accounts", total_dm),
        ("% of All ICS", safe_percentage(total_dm, total_ics)),
        ("Open Accounts", open_count),
        ("Closed Accounts", closed_count),
        ("Open %", safe_percentage(open_count, total_dm)),
        ("Debit Card Count (Open)", debit_count),
        ("Debit Card %", safe_percentage(debit_count, open_count)),
        ("Avg Balance (Open)", round(dm_open["Curr Bal"].mean(), 2) if open_count > 0 else 0.0),
        ("Total L12M Swipes", total_swipes),
        ("Total L12M Spend", total_spend),
    ]

    return AnalysisResult(
        name="DM Overview",
        title="Direct Mail Source - Overview KPIs",
        df=kpi_summary(metrics),
        sheet_name="45_DM_Overview",
    )


def analyze_dm_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax46: DM open accounts by Branch with debit penetration."""
    data = _dm_filter(ics_stat_o)

    if data.empty:
        return AnalysisResult(
            name="DM by Branch",
            title="DM Open Accounts by Branch",
            df=pd.DataFrame(
                columns=["Branch", "Count", "% of DM", "Debit Count", "Debit %", "Avg Balance"]
            ),
            sheet_name="46_DM_Branch",
        )

    grouped = (
        data.groupby("Branch", dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Debit_Count=("Debit?", lambda x: (x == "Yes").sum()),
            Avg_Balance=("Curr Bal", "mean"),
        )
        .reset_index()
    )

    total_dm = grouped["Count"].sum()
    grouped["% of DM"] = grouped["Count"].apply(lambda c: safe_percentage(c, total_dm))
    grouped["Debit Count"] = grouped["Debit_Count"].astype(int)
    grouped["Debit %"] = grouped.apply(
        lambda row: safe_percentage(row["Debit_Count"], row["Count"]), axis=1
    )
    grouped["Avg Balance"] = grouped["Avg_Balance"].round(2)

    result_df = (
        grouped[["Branch", "Count", "% of DM", "Debit Count", "Debit %", "Avg Balance"]]
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="DM by Branch",
        title="DM Open Accounts by Branch",
        df=result_df,
        sheet_name="46_DM_Branch",
    )


def analyze_dm_by_debit(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax47: DM open accounts by Debit status with activity comparison."""
    data = _dm_filter(ics_stat_o)
    data = add_l12m_activity(data, settings.last_12_months)

    if data.empty:
        return AnalysisResult(
            name="DM by Debit Status",
            title="DM Open Accounts by Debit Status",
            df=pd.DataFrame(
                columns=[
                    "Debit?",
                    "Count",
                    "%",
                    "Avg Balance",
                    "Total L12M Swipes",
                    "Avg L12M Swipes",
                    "Total L12M Spend",
                    "Avg L12M Spend",
                ]
            ),
            sheet_name="47_DM_Debit",
        )

    grouped = (
        data.groupby("Debit?", dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Avg_Balance=("Curr Bal", "mean"),
            Total_Swipes=("Total L12M Swipes", "sum"),
            Total_Spend=("Total L12M Spend", "sum"),
        )
        .reset_index()
    )

    total = grouped["Count"].sum()
    grouped["%"] = grouped["Count"].apply(lambda c: safe_percentage(c, total))
    grouped["Avg Balance"] = grouped["Avg_Balance"].round(2)
    grouped["Total L12M Swipes"] = grouped["Total_Swipes"].astype(int)
    grouped["Avg L12M Swipes"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Swipes"], row["Count"]), axis=1
    )
    grouped["Total L12M Spend"] = grouped["Total_Spend"].round(2)
    grouped["Avg L12M Spend"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Spend"], row["Count"]), axis=1
    )

    debit_cols = [
        "Debit?",
        "Count",
        "%",
        "Avg Balance",
        "Total L12M Swipes",
        "Avg L12M Swipes",
        "Total L12M Spend",
        "Avg L12M Spend",
    ]
    result_df = grouped[debit_cols].reset_index(drop=True)

    result_df = append_grand_total_row(result_df, label_col="Debit?")

    return AnalysisResult(
        name="DM by Debit Status",
        title="DM Open Accounts by Debit Status",
        df=result_df,
        sheet_name="47_DM_Debit",
    )


def analyze_dm_by_product(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax48: DM open accounts by Product Code with debit penetration."""
    data = _dm_filter(ics_stat_o)

    if data.empty:
        return AnalysisResult(
            name="DM by Product",
            title="DM Open Accounts by Product Code",
            df=pd.DataFrame(columns=["Prod Code", "Count", "%", "Debit Count", "Debit %"]),
            sheet_name="48_DM_Product",
        )

    grouped = (
        data.groupby("Prod Code", dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Debit_Count=("Debit?", lambda x: (x == "Yes").sum()),
        )
        .reset_index()
    )

    total = grouped["Count"].sum()
    grouped["%"] = grouped["Count"].apply(lambda c: safe_percentage(c, total))
    grouped["Debit Count"] = grouped["Debit_Count"].astype(int)
    grouped["Debit %"] = grouped.apply(
        lambda row: safe_percentage(row["Debit_Count"], row["Count"]), axis=1
    )

    result_df = (
        grouped[["Prod Code", "Count", "%", "Debit Count", "Debit %"]]
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Prod Code")

    return AnalysisResult(
        name="DM by Product",
        title="DM Open Accounts by Product Code",
        df=result_df,
        sheet_name="48_DM_Product",
    )


def analyze_dm_by_year(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax49: DM open accounts by Year Opened with debit penetration."""
    data = _dm_filter(ics_stat_o)

    if data.empty:
        return AnalysisResult(
            name="DM by Year Opened",
            title="DM Open Accounts by Year Opened",
            df=pd.DataFrame(
                columns=["Year Opened", "Count", "%", "Debit Count", "Debit %", "Avg Balance"]
            ),
            sheet_name="49_DM_Year",
        )

    if "Date Opened" in data.columns:
        data["Year Opened"] = data["Date Opened"].dt.year.astype(str)
    else:
        data["Year Opened"] = "Unknown"

    grouped = (
        data.groupby("Year Opened", dropna=False)
        .agg(
            Count=("ICS Account", "size"),
            Debit_Count=("Debit?", lambda x: (x == "Yes").sum()),
            Avg_Balance=("Curr Bal", "mean"),
        )
        .reset_index()
    )

    total = grouped["Count"].sum()
    grouped["%"] = grouped["Count"].apply(lambda c: safe_percentage(c, total))
    grouped["Debit Count"] = grouped["Debit_Count"].astype(int)
    grouped["Debit %"] = grouped.apply(
        lambda row: safe_percentage(row["Debit_Count"], row["Count"]), axis=1
    )
    grouped["Avg Balance"] = grouped["Avg_Balance"].round(2)

    result_df = (
        grouped[["Year Opened", "Count", "%", "Debit Count", "Debit %", "Avg Balance"]]
        .sort_values("Year Opened")
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Year Opened")

    return AnalysisResult(
        name="DM by Year Opened",
        title="DM Open Accounts by Year Opened",
        df=result_df,
        sheet_name="49_DM_Year",
    )


def analyze_dm_activity(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax50: DM Activity KPIs for open DM accounts with debit cards."""
    data = _dm_filter(ics_stat_o_debit)
    data = add_l12m_activity(data, settings.last_12_months)

    total_accounts = len(data)
    active_mask = data["Active in L12M"] if not data.empty else pd.Series(dtype=bool)
    active_count = int(active_mask.sum()) if not data.empty else 0

    total_swipes = int(data["Total L12M Swipes"].sum()) if not data.empty else 0
    total_spend = float(data["Total L12M Spend"].sum()) if not data.empty else 0.0

    active_data = data[active_mask] if not data.empty else data

    metrics = [
        ("Total DM Debit Accounts", total_accounts),
        ("Active Accounts (L12M)", active_count),
        ("% Active", safe_percentage(active_count, total_accounts)),
        ("Total Swipes", total_swipes),
        ("Total Spend", round(total_spend, 2)),
        ("Avg Swipes per Account", safe_ratio(total_swipes, total_accounts)),
        ("Avg Spend per Account", round(safe_ratio(total_spend, total_accounts), 2)),
        ("Avg Swipes per Active Account", safe_ratio(total_swipes, active_count)),
        ("Avg Spend per Active Account", round(safe_ratio(total_spend, active_count), 2)),
        ("Avg Spend per Swipe", round(safe_ratio(total_spend, total_swipes), 2)),
        (
            "Avg Balance (All)",
            round(data["Curr Bal"].mean(), 2) if total_accounts > 0 else 0.0,
        ),
        (
            "Avg Balance (Active)",
            round(active_data["Curr Bal"].mean(), 2) if active_count > 0 else 0.0,
        ),
    ]

    return AnalysisResult(
        name="DM Activity Summary",
        title="DM Debit Accounts - L12M Activity KPIs",
        df=kpi_summary(metrics),
        sheet_name="50_DM_Activity",
    )


def analyze_dm_activity_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax51: DM debit account activity by Branch."""
    data = _dm_filter(ics_stat_o_debit)
    data = add_l12m_activity(data, settings.last_12_months)

    if data.empty:
        return AnalysisResult(
            name="DM Activity by Branch",
            title="DM Debit Accounts - Activity by Branch",
            df=pd.DataFrame(
                columns=[
                    "Branch",
                    "Count",
                    "Active Count",
                    "Activation %",
                    "Avg Swipes",
                    "Avg Spend",
                ]
            ),
            sheet_name="51_DM_Act_Branch",
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
        name="DM Activity by Branch",
        title="DM Debit Accounts - Activity by Branch",
        df=result_df,
        sheet_name="51_DM_Act_Branch",
    )


def analyze_dm_monthly_trends(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax52: Monthly Trends for DM debit accounts across L12M."""
    data = _dm_filter(ics_stat_o_debit)
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

    return AnalysisResult(
        name="DM Monthly Trends",
        title="DM Debit Accounts - Monthly Activity Trends",
        df=pd.DataFrame(rows),
        sheet_name="52_DM_Monthly",
    )
