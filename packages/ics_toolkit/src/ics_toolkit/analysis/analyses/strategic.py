"""Strategic analyses: Activation Funnel and Revenue Impact."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.templates import append_grand_total_row, kpi_summary
from ics_toolkit.analysis.utils import add_l12m_activity
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_activation_funnel(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """Activation funnel: Total -> ICS -> Stat O -> Debit -> Active L12M."""
    ics_count = len(ics_all)
    stat_o_count = len(ics_stat_o)
    debit_count = len(ics_stat_o_debit)

    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)
    active_count = int(data["Active in L12M"].sum()) if "Active in L12M" in data.columns else 0

    stages = [
        ("ICS Accounts", ics_count),
        ("Stat Code O", stat_o_count),
        ("With Debit Card", debit_count),
        ("Active in L12M", active_count),
    ]

    rows = []
    for i, (stage, count) in enumerate(stages):
        pct_of_ics = safe_percentage(count, ics_count)
        if i == 0:
            dropoff = 0.0
        else:
            prev_count = stages[i - 1][1]
            dropoff = safe_percentage(prev_count - count, prev_count) if prev_count > 0 else 0.0

        rows.append(
            {
                "Stage": stage,
                "Count": count,
                "% of ICS": pct_of_ics,
                "Drop-off %": dropoff,
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Activation Funnel",
        title="ICS Activation Funnel",
        df=result_df,
        sheet_name="38_Activ_Funnel",
    )


def analyze_revenue_impact(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """Revenue impact: estimated interchange from debit card spend."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)

    if "Total L12M Spend" in data.columns:
        total_spend = float(data["Total L12M Spend"].sum())
    else:
        total_spend = 0.0
    if "Active in L12M" in data.columns:
        active_mask = data["Active in L12M"]
    else:
        active_mask = pd.Series(dtype=bool)
    active_count = int(active_mask.sum())
    inactive_count = len(data) - active_count

    interchange_rate = settings.interchange_rate
    estimated_interchange = total_spend * interchange_rate
    revenue_per_active = estimated_interchange / active_count if active_count > 0 else 0

    # Revenue at risk: inactive accounts' potential at avg active spend
    avg_active_spend = (
        float(data.loc[active_mask, "Total L12M Spend"].mean()) if active_count > 0 else 0
    )
    revenue_at_risk = inactive_count * avg_active_spend * interchange_rate

    metrics = [
        ("Estimated Annual Interchange", round(estimated_interchange, 2)),
        ("Revenue per Active Card", round(revenue_per_active, 2)),
        ("Never-Activator Count", inactive_count),
        ("Revenue at Risk (Dormant)", round(revenue_at_risk, 2)),
        ("Activation Campaign Potential", round(revenue_at_risk, 2)),
    ]

    result_df = kpi_summary(metrics)

    return AnalysisResult(
        name="Revenue Impact",
        title="ICS Revenue Impact Analysis",
        df=result_df,
        sheet_name="39_Revenue_Impact",
    )


def analyze_revenue_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax65: Estimated interchange revenue by branch."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)
    interchange_rate = settings.interchange_rate

    if data.empty or "Branch" not in data.columns:
        return AnalysisResult(
            name="Revenue by Branch",
            title="Estimated Interchange Revenue by Branch",
            df=pd.DataFrame(
                columns=["Branch", "Accounts", "Total L12M Spend", "Est. Interchange", "Avg Spend"]
            ),
            sheet_name="65_Revenue_Branch",
        )

    grouped = (
        data.groupby("Branch", dropna=False)
        .agg(
            Accounts=("Branch", "size"),
            Total_Spend=("Total L12M Spend", "sum"),
        )
        .reset_index()
    )

    grouped["Est. Interchange"] = (grouped["Total_Spend"] * interchange_rate).round(2)
    grouped["Avg Spend"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Spend"], row["Accounts"]), axis=1
    )
    grouped["Total L12M Spend"] = grouped["Total_Spend"].round(2)

    result_df = (
        grouped[["Branch", "Accounts", "Total L12M Spend", "Est. Interchange", "Avg Spend"]]
        .sort_values("Est. Interchange", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="Revenue by Branch",
        title="Estimated Interchange Revenue by Branch",
        df=result_df,
        sheet_name="65_Revenue_Branch",
    )


def analyze_revenue_by_source(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax66: Estimated interchange revenue by source channel."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)
    interchange_rate = settings.interchange_rate

    if data.empty or "Source" not in data.columns:
        return AnalysisResult(
            name="Revenue by Source",
            title="Estimated Interchange Revenue by Source",
            df=pd.DataFrame(
                columns=["Source", "Accounts", "Total L12M Spend", "Est. Interchange", "Avg Spend"]
            ),
            sheet_name="66_Revenue_Source",
        )

    grouped = (
        data.groupby("Source", dropna=False)
        .agg(
            Accounts=("Source", "size"),
            Total_Spend=("Total L12M Spend", "sum"),
        )
        .reset_index()
    )

    grouped["Est. Interchange"] = (grouped["Total_Spend"] * interchange_rate).round(2)
    grouped["Avg Spend"] = grouped.apply(
        lambda row: safe_ratio(row["Total_Spend"], row["Accounts"]), axis=1
    )
    grouped["Total L12M Spend"] = grouped["Total_Spend"].round(2)

    result_df = (
        grouped[["Source", "Accounts", "Total L12M Spend", "Est. Interchange", "Avg Spend"]]
        .sort_values("Est. Interchange", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Source")

    return AnalysisResult(
        name="Revenue by Source",
        title="Estimated Interchange Revenue by Source",
        df=result_df,
        sheet_name="66_Revenue_Source",
    )


def analyze_dormant_high_balance(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax84: Dormant high-balance accounts -- inactive with Curr Bal >= $10K."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)
    threshold = 10000

    if data.empty:
        return AnalysisResult(
            name="Dormant High-Balance",
            title="Dormant High-Balance Accounts",
            df=kpi_summary([("Status", "No debit accounts")]),
            sheet_name="84_Dormant_HiBal",
        )

    dormant = data[(~data["Active in L12M"]) & (data["Curr Bal"] >= threshold)]
    active = data[data["Active in L12M"]]

    dormant_count = len(dormant)
    total_inactive = int((~data["Active in L12M"]).sum())
    total_balance = round(float(dormant["Curr Bal"].sum()), 2) if dormant_count > 0 else 0.0
    avg_balance = round(float(dormant["Curr Bal"].mean()), 2) if dormant_count > 0 else 0.0

    avg_active_spend = (
        round(float(active["Total L12M Spend"].mean()), 2) if len(active) > 0 else 0.0
    )
    interchange_rate = settings.interchange_rate
    potential_interchange = round(dormant_count * avg_active_spend * interchange_rate, 2)

    metrics = [
        ("Total Debit Accounts", len(data)),
        ("Inactive Accounts", total_inactive),
        (f"Dormant with Bal >= ${threshold:,}", dormant_count),
        ("% of All Inactive", safe_percentage(dormant_count, total_inactive)),
        ("Total Balance (Dormant)", total_balance),
        ("Avg Balance (Dormant)", avg_balance),
        ("Avg L12M Spend (Active Accts)", avg_active_spend),
        ("Est. Interchange if Activated", potential_interchange),
    ]

    return AnalysisResult(
        name="Dormant High-Balance",
        title="Dormant High-Balance Accounts",
        df=kpi_summary(metrics),
        sheet_name="84_Dormant_HiBal",
    )
