"""Strategic analyses: Activation Funnel and Revenue Impact."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.analyses.benchmarks import INTERCHANGE_RATE
from ics_toolkit.analysis.analyses.templates import kpi_summary
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
    total_accounts = len(df)
    ics_count = len(ics_all)
    stat_o_count = len(ics_stat_o)
    debit_count = len(ics_stat_o_debit)

    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)
    active_count = int(data["Active in L12M"].sum()) if "Active in L12M" in data.columns else 0

    stages = [
        ("Total Accounts", total_accounts),
        ("ICS Accounts", ics_count),
        ("Stat Code O", stat_o_count),
        ("With Debit Card", debit_count),
        ("Active in L12M", active_count),
    ]

    rows = []
    for i, (stage, count) in enumerate(stages):
        pct_of_total = safe_percentage(count, total_accounts)
        if i == 0:
            dropoff = 0.0
        else:
            prev_count = stages[i - 1][1]
            dropoff = safe_percentage(prev_count - count, prev_count) if prev_count > 0 else 0.0

        rows.append(
            {
                "Stage": stage,
                "Count": count,
                "% of Total": pct_of_total,
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

    estimated_interchange = total_spend * INTERCHANGE_RATE
    revenue_per_active = estimated_interchange / active_count if active_count > 0 else 0

    # Revenue at risk: inactive accounts' potential at avg active spend
    avg_active_spend = (
        float(data.loc[active_mask, "Total L12M Spend"].mean()) if active_count > 0 else 0
    )
    revenue_at_risk = inactive_count * avg_active_spend * INTERCHANGE_RATE

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
