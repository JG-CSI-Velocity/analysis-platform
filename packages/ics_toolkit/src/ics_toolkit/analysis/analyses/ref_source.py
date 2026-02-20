"""REF Source deep-dive analyses (ax73-ax80), parallel to DM Deep-Dive."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.templates import append_grand_total_row, kpi_summary
from ics_toolkit.analysis.utils import add_l12m_activity
from ics_toolkit.settings import AnalysisSettings as Settings

REF = "REF"


def _ref_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Source == 'REF' rows."""
    return df[df["Source"] == REF].copy()


def analyze_ref_overview(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax73: REF Overview KPIs -- total, open/closed, debit, balance, L12M activity."""
    ref_all = _ref_filter(ics_all)
    ref_open = ref_all[ref_all["Stat Code"].isin(settings.open_stat_codes)]
    ref_closed = ref_all[~ref_all["Stat Code"].isin(settings.open_stat_codes)]
    ref_debit = ref_open[ref_open["Debit?"] == "Yes"]

    total_ref = len(ref_all)
    total_ics = len(ics_all)
    open_count = len(ref_open)
    closed_count = len(ref_closed)
    debit_count = len(ref_debit)

    ref_open_activity = add_l12m_activity(ref_open.copy(), settings.last_12_months)
    if not ref_open_activity.empty:
        total_swipes = int(ref_open_activity["Total L12M Swipes"].sum())
        total_spend = round(float(ref_open_activity["Total L12M Spend"].sum()), 2)
    else:
        total_swipes = 0
        total_spend = 0.0

    metrics = [
        ("Total REF Accounts", total_ref),
        ("% of All ICS", safe_percentage(total_ref, total_ics)),
        ("Open Accounts", open_count),
        ("Closed Accounts", closed_count),
        ("Open %", safe_percentage(open_count, total_ref)),
        ("Debit Card Count (Open)", debit_count),
        ("Debit Card %", safe_percentage(debit_count, open_count)),
        ("Avg Balance (Open)", round(ref_open["Curr Bal"].mean(), 2) if open_count > 0 else 0.0),
        ("Total L12M Swipes", total_swipes),
        ("Total L12M Spend", total_spend),
    ]

    return AnalysisResult.from_df(
        "REF Overview",
        "Referral Source - Overview KPIs",
        kpi_summary(metrics),
        sheet_name="73_REF_Overview",
    )


def analyze_ref_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax74: REF open accounts by Branch with debit penetration."""
    data = _ref_filter(ics_stat_o)

    if data.empty:
        return AnalysisResult.from_df(
            "REF by Branch",
            "REF Open Accounts by Branch",
            pd.DataFrame(
                columns=["Branch", "Count", "% of REF", "Debit Count", "Debit %", "Avg Balance"]
            ),
            sheet_name="74_REF_Branch",
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

    total_ref = grouped["Count"].sum()
    grouped["% of REF"] = grouped["Count"].apply(lambda c: safe_percentage(c, total_ref))
    grouped["Debit Count"] = grouped["Debit_Count"].astype(int)
    grouped["Debit %"] = grouped.apply(
        lambda row: safe_percentage(row["Debit_Count"], row["Count"]), axis=1
    )
    grouped["Avg Balance"] = grouped["Avg_Balance"].round(2)

    result_df = (
        grouped[["Branch", "Count", "% of REF", "Debit Count", "Debit %", "Avg Balance"]]
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult.from_df(
        "REF by Branch",
        "REF Open Accounts by Branch",
        result_df,
        sheet_name="74_REF_Branch",
    )


def analyze_ref_by_debit(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax75: REF open accounts by Debit status with activity comparison."""
    data = _ref_filter(ics_stat_o)
    data = add_l12m_activity(data, settings.last_12_months)

    if data.empty:
        return AnalysisResult.from_df(
            "REF by Debit Status",
            "REF Open Accounts by Debit Status",
            pd.DataFrame(
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
            sheet_name="75_REF_Debit",
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

    return AnalysisResult.from_df(
        "REF by Debit Status",
        "REF Open Accounts by Debit Status",
        result_df,
        sheet_name="75_REF_Debit",
    )


def analyze_ref_by_product(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax76: REF open accounts by Product Code with debit penetration."""
    data = _ref_filter(ics_stat_o)

    if data.empty:
        return AnalysisResult.from_df(
            "REF by Product",
            "REF Open Accounts by Product Code",
            pd.DataFrame(columns=["Prod Code", "Count", "%", "Debit Count", "Debit %"]),
            sheet_name="76_REF_Product",
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

    return AnalysisResult.from_df(
        "REF by Product",
        "REF Open Accounts by Product Code",
        result_df,
        sheet_name="76_REF_Product",
    )


def analyze_ref_by_year(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax77: REF open accounts by Year Opened with debit penetration."""
    data = _ref_filter(ics_stat_o)

    if data.empty:
        return AnalysisResult.from_df(
            "REF by Year Opened",
            "REF Open Accounts by Year Opened",
            pd.DataFrame(
                columns=["Year Opened", "Count", "%", "Debit Count", "Debit %", "Avg Balance"]
            ),
            sheet_name="77_REF_Year",
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

    return AnalysisResult.from_df(
        "REF by Year Opened",
        "REF Open Accounts by Year Opened",
        result_df,
        sheet_name="77_REF_Year",
    )


def analyze_ref_activity(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax78: REF Activity KPIs for open REF accounts with debit cards."""
    data = _ref_filter(ics_stat_o_debit)
    data = add_l12m_activity(data, settings.last_12_months)

    total_accounts = len(data)
    active_mask = data["Active in L12M"] if not data.empty else pd.Series(dtype=bool)
    active_count = int(active_mask.sum()) if not data.empty else 0

    total_swipes = int(data["Total L12M Swipes"].sum()) if not data.empty else 0
    total_spend = float(data["Total L12M Spend"].sum()) if not data.empty else 0.0

    active_data = data[active_mask] if not data.empty else data

    metrics = [
        ("Total REF Debit Accounts", total_accounts),
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

    return AnalysisResult.from_df(
        "REF Activity Summary",
        "REF Debit Accounts - L12M Activity KPIs",
        kpi_summary(metrics),
        sheet_name="78_REF_Activity",
    )


def analyze_ref_activity_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax79: REF debit account activity by Branch."""
    data = _ref_filter(ics_stat_o_debit)
    data = add_l12m_activity(data, settings.last_12_months)

    if data.empty:
        return AnalysisResult.from_df(
            "REF Activity by Branch",
            "REF Debit Accounts - Activity by Branch",
            pd.DataFrame(
                columns=[
                    "Branch",
                    "Count",
                    "Active Count",
                    "Activation %",
                    "Avg Swipes",
                    "Avg Spend",
                ]
            ),
            sheet_name="79_REF_Act_Branch",
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

    return AnalysisResult.from_df(
        "REF Activity by Branch",
        "REF Debit Accounts - Activity by Branch",
        result_df,
        sheet_name="79_REF_Act_Branch",
    )


def analyze_ref_monthly_trends(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax80: Monthly Trends for REF debit accounts across L12M."""
    data = _ref_filter(ics_stat_o_debit)
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

    return AnalysisResult.from_df(
        "REF Monthly Trends",
        "REF Debit Accounts - Monthly Activity Trends",
        pd.DataFrame(rows),
        sheet_name="80_REF_Monthly",
    )
