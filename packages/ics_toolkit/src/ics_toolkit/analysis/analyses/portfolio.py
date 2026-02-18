"""Portfolio analyses: Engagement Decay, Net Portfolio Growth, Concentration."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.analyses.templates import kpi_summary
from ics_toolkit.analysis.utils import add_l12m_activity
from ics_toolkit.settings import AnalysisSettings as Settings


def analyze_engagement_decay(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """Accounts active in first half of L12M but inactive in second half."""
    tags = settings.last_12_months
    if len(tags) < 4:
        return AnalysisResult(
            name="Engagement Decay",
            title="ICS Engagement Decay Analysis",
            df=kpi_summary([("Status", "Insufficient L12M data")]),
            sheet_name="40_Engagement_Decay",
        )

    mid = len(tags) // 2
    first_half = tags[:mid]
    second_half = tags[mid:]

    data = ics_stat_o_debit.copy()

    def _has_activity(row, month_tags):
        for tag in month_tags:
            col = f"{tag} Swipes"
            if col in data.columns and row.get(col, 0) > 0:
                return True
        return False

    categories = []
    for _, row in data.iterrows():
        active_first = _has_activity(row, first_half)
        active_second = _has_activity(row, second_half)

        if active_first and active_second:
            categories.append("Active")
        elif active_first and not active_second:
            categories.append("Decayed")
        elif not active_first and active_second:
            categories.append("Late Activator")
        else:
            categories.append("Never Active")

    data = data.copy()
    data["Decay Category"] = categories
    total = len(data)

    summary = data.groupby("Decay Category").size().reset_index(name="Count")
    summary["% of Total"] = summary["Count"].apply(lambda x: safe_percentage(x, total))

    order = ["Active", "Decayed", "Late Activator", "Never Active"]
    summary["Decay Category"] = pd.Categorical(
        summary["Decay Category"], categories=order, ordered=True
    )
    summary = summary.sort_values("Decay Category").reset_index(drop=True)
    summary["Decay Category"] = summary["Decay Category"].astype(str)

    return AnalysisResult(
        name="Engagement Decay",
        title="ICS Engagement Decay Analysis",
        df=summary,
        sheet_name="40_Engagement_Decay",
    )


def analyze_net_portfolio_growth(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """Monthly opens minus closes for ICS accounts."""
    data = ics_all.copy()

    if "Date Opened" not in data.columns:
        return AnalysisResult(
            name="Net Portfolio Growth",
            title="ICS Net Portfolio Growth",
            df=pd.DataFrame(columns=["Month", "Opens", "Closes", "Net", "Cumulative"]),
            sheet_name="41_Net_Growth",
        )

    data["Open Month"] = (
        pd.to_datetime(data["Date Opened"], errors="coerce").dt.to_period("M").astype(str)
    )

    opens = data.groupby("Open Month").size().reset_index(name="Opens")

    if "Date Closed" in data.columns:
        closed = data[data["Date Closed"].notna()].copy()
        closed["Close Month"] = (
            pd.to_datetime(closed["Date Closed"], errors="coerce").dt.to_period("M").astype(str)
        )
        closes = closed.groupby("Close Month").size().reset_index(name="Closes")
        closes.columns = ["Month", "Closes"]
    else:
        closes = pd.DataFrame(columns=["Month", "Closes"])

    opens.columns = ["Month", "Opens"]

    result = opens.merge(closes, on="Month", how="outer").fillna(0)
    result = result.sort_values("Month").reset_index(drop=True)
    result["Opens"] = result["Opens"].astype(int)
    result["Closes"] = result["Closes"].astype(int)
    result["Net"] = result["Opens"] - result["Closes"]
    result["Cumulative"] = result["Net"].cumsum()

    return AnalysisResult(
        name="Net Portfolio Growth",
        title="ICS Net Portfolio Growth",
        df=result,
        sheet_name="41_Net_Growth",
    )


def analyze_concentration(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """What % of total spend comes from top 10/20/50% of accounts."""
    data = add_l12m_activity(ics_stat_o_debit.copy(), settings.last_12_months)

    if "Total L12M Spend" not in data.columns or data.empty:
        return AnalysisResult(
            name="Spend Concentration",
            title="ICS Spend Concentration",
            df=pd.DataFrame(columns=["Percentile", "Account Count", "Spend Share %"]),
            sheet_name="42_Concentration",
        )

    total_spend = data["Total L12M Spend"].sum()
    if total_spend == 0:
        return AnalysisResult(
            name="Spend Concentration",
            title="ICS Spend Concentration",
            df=pd.DataFrame(columns=["Percentile", "Account Count", "Spend Share %"]),
            sheet_name="42_Concentration",
        )

    sorted_data = data.sort_values("Total L12M Spend", ascending=False).reset_index(drop=True)
    n = len(sorted_data)

    percentiles = [("Top 10%", 0.10), ("Top 20%", 0.20), ("Top 50%", 0.50)]
    rows = []
    for label, pct in percentiles:
        count = max(1, int(n * pct))
        top_spend = sorted_data.head(count)["Total L12M Spend"].sum()
        share = safe_percentage(top_spend, total_spend)
        rows.append(
            {
                "Percentile": label,
                "Account Count": count,
                "Spend Share %": share,
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Spend Concentration",
        title="ICS Spend Concentration",
        df=result_df,
        sheet_name="42_Concentration",
    )
