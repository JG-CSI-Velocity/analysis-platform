"""Performance analyses: Days to First Use and Branch Performance Index."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.templates import append_grand_total_row
from ics_toolkit.analysis.utils import add_l12m_activity
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_days_to_first_use(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """Days from Date Opened to first month with swipes > 0."""
    data = ics_stat_o_debit.copy()

    if "Date Opened" not in data.columns or data.empty:
        return AnalysisResult.from_df(
            "Days to First Use",
            "ICS Days to First Use",
            pd.DataFrame(columns=["Days Bucket", "Count", "% of Total"]),
            sheet_name="43_Days_First_Use",
        )

    tags = settings.last_12_months
    if not tags:
        return AnalysisResult.from_df(
            "Days to First Use",
            "ICS Days to First Use",
            pd.DataFrame(columns=["Days Bucket", "Count", "% of Total"]),
            sheet_name="43_Days_First_Use",
        )

    # Parse month tags to datetime for comparison
    from datetime import datetime

    tag_dates = {}
    for tag in tags:
        try:
            tag_dates[tag] = datetime.strptime(tag, "%b%y")
        except ValueError:
            continue

    days_list = []
    for _, row in data.iterrows():
        opened = row.get("Date Opened")
        if pd.isna(opened):
            days_list.append(None)
            continue

        opened_dt = pd.to_datetime(opened)
        first_use = None

        for tag in tags:
            swipe_col = f"{tag} Swipes"
            if swipe_col in data.columns and row.get(swipe_col, 0) > 0:
                if tag in tag_dates:
                    first_use = tag_dates[tag]
                    break

        if first_use is None:
            days_list.append(None)
        else:
            delta = (first_use - opened_dt).days
            days_list.append(max(0, delta))

    data = data.copy()
    data["Days to First Use"] = days_list

    buckets = [
        ("0-30 days", 0, 30),
        ("31-60 days", 31, 60),
        ("61-90 days", 61, 90),
        ("91-180 days", 91, 180),
        ("180+ days", 181, 999999),
    ]

    total = len(data)
    rows = []
    used_count = 0

    for label, low, high in buckets:
        mask = data["Days to First Use"].between(low, high)
        count = int(mask.sum())
        used_count += count
        rows.append(
            {
                "Days Bucket": label,
                "Count": count,
                "% of Total": safe_percentage(count, total),
            }
        )

    never_count = total - used_count
    rows.append(
        {
            "Days Bucket": "Never Used",
            "Count": never_count,
            "% of Total": safe_percentage(never_count, total),
        }
    )

    result_df = pd.DataFrame(rows)

    return AnalysisResult.from_df(
        "Days to First Use",
        "ICS Days to First Use",
        result_df,
        sheet_name="43_Days_First_Use",
    )


def analyze_branch_performance_index(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """Branch performance normalized to CU average = 100."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)

    cols_needed = ["Branch", "Active in L12M", "Total L12M Swipes", "Total L12M Spend", "Curr Bal"]
    if data.empty or not all(c in data.columns for c in cols_needed):
        return AnalysisResult.from_df(
            "Branch Performance Index",
            "ICS Branch Performance Index",
            pd.DataFrame(
                columns=[
                    "Branch",
                    "Accounts",
                    "Activation Index",
                    "Swipes Index",
                    "Spend Index",
                    "Balance Index",
                    "Composite Score",
                ]
            ),
            sheet_name="44_Branch_Perf",
        )

    # CU-wide averages
    total_accounts = len(data)
    cu_activation = data["Active in L12M"].mean() if total_accounts > 0 else 0
    cu_swipes = data["Total L12M Swipes"].mean() if total_accounts > 0 else 0
    cu_spend = data["Total L12M Spend"].mean() if total_accounts > 0 else 0
    cu_balance = data["Curr Bal"].mean() if total_accounts > 0 else 0

    grouped = (
        data.groupby("Branch", dropna=False)
        .agg(
            accounts=("Branch", "size"),
            activation=("Active in L12M", "mean"),
            swipes=("Total L12M Swipes", "mean"),
            spend=("Total L12M Spend", "mean"),
            balance=("Curr Bal", "mean"),
        )
        .reset_index()
    )

    def _index(val, cu_avg):
        if cu_avg == 0:
            return 100.0
        return round((val / cu_avg) * 100, 1)

    grouped["Activation Index"] = grouped["activation"].apply(lambda v: _index(v, cu_activation))
    grouped["Swipes Index"] = grouped["swipes"].apply(lambda v: _index(v, cu_swipes))
    grouped["Spend Index"] = grouped["spend"].apply(lambda v: _index(v, cu_spend))
    grouped["Balance Index"] = grouped["balance"].apply(lambda v: _index(v, cu_balance))
    grouped["Composite Score"] = (
        (
            grouped["Activation Index"]
            + grouped["Swipes Index"]
            + grouped["Spend Index"]
            + grouped["Balance Index"]
        )
        / 4
    ).round(1)

    result_df = (
        grouped[
            [
                "Branch",
                "accounts",
                "Activation Index",
                "Swipes Index",
                "Spend Index",
                "Balance Index",
                "Composite Score",
            ]
        ]
        .rename(columns={"accounts": "Accounts"})
        .sort_values("Composite Score", ascending=False)
        .reset_index(drop=True)
    )

    return AnalysisResult.from_df(
        "Branch Performance Index",
        "ICS Branch Performance Index",
        result_df,
        sheet_name="44_Branch_Perf",
    )


def analyze_product_code_performance(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax81: Product code performance -- activation, swipes, spend by Prod Code."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)

    if data.empty or "Prod Code" not in data.columns:
        return AnalysisResult.from_df(
            "Product Code Performance",
            "ICS Product Code Performance",
            pd.DataFrame(
                columns=[
                    "Prod Code",
                    "Accounts",
                    "Active Count",
                    "Activation %",
                    "Avg Swipes",
                    "Avg Spend",
                    "Avg Balance",
                ]
            ),
            sheet_name="81_Prod_Perf",
        )

    grouped = (
        data.groupby("Prod Code", dropna=False)
        .agg(
            Accounts=("Prod Code", "size"),
            Active_Count=("Active in L12M", "sum"),
            Total_Swipes=("Total L12M Swipes", "sum"),
            Total_Spend=("Total L12M Spend", "sum"),
            Avg_Balance=("Curr Bal", "mean"),
        )
        .reset_index()
    )

    grouped["Active Count"] = grouped["Active_Count"].astype(int)
    grouped["Activation %"] = grouped.apply(
        lambda row: safe_percentage(row["Active_Count"], row["Accounts"]), axis=1
    )
    grouped["Avg Swipes"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Swipes"], row["Accounts"]), axis=1
    )
    grouped["Avg Spend"] = grouped.apply(
        lambda row: round(safe_ratio(row["Total_Spend"], row["Accounts"]), 2), axis=1
    )
    grouped["Avg Balance"] = grouped["Avg_Balance"].round(2)

    result_df = (
        grouped[
            [
                "Prod Code",
                "Accounts",
                "Active Count",
                "Activation %",
                "Avg Swipes",
                "Avg Spend",
                "Avg Balance",
            ]
        ]
        .sort_values("Accounts", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Prod Code")

    return AnalysisResult.from_df(
        "Product Code Performance",
        "ICS Product Code Performance",
        result_df,
        sheet_name="81_Prod_Perf",
    )
