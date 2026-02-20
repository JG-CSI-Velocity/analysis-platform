"""Portfolio analyses: Engagement Decay, Net Portfolio Growth, Concentration, Closures."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.analyses.templates import append_grand_total_row, kpi_summary
from ics_toolkit.analysis.utils import add_age_range, add_l12m_activity
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

    # Determine date range cutoff (use data_start_date or last 24 months)
    if settings.data_start_date:
        cutoff = pd.to_datetime(settings.data_start_date)
    elif settings.last_12_months:
        from datetime import datetime

        first_tag = settings.last_12_months[0]
        cutoff = datetime.strptime(first_tag, "%b%y")
    else:
        cutoff = None

    opened_dt = pd.to_datetime(data["Date Opened"], errors="coerce")
    data["Open Month"] = opened_dt.dt.to_period("M").astype(str)

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

    # Filter to months at or after cutoff
    if cutoff is not None:
        cutoff_period = pd.Timestamp(cutoff).to_period("M").strftime("%Y-%m")
        result = result[result["Month"] >= cutoff_period].reset_index(drop=True)

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


def _get_cutoff(settings: Settings):
    """Derive a date range cutoff from settings."""
    if settings.data_start_date:
        return pd.to_datetime(settings.data_start_date)
    if settings.last_12_months:
        from datetime import datetime

        return datetime.strptime(settings.last_12_months[0], "%b%y")
    return None


def analyze_closure_by_source(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax67: Closed ICS accounts broken down by Source channel."""
    closed = ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)].copy()

    if closed.empty or "Source" not in closed.columns:
        return AnalysisResult(
            name="Closure by Source",
            title="ICS Closures by Source Channel",
            df=pd.DataFrame(columns=["Source", "Closed Count", "% of Closures"]),
            sheet_name="67_Closure_Source",
        )

    total_closed = len(closed)
    grouped = closed.groupby("Source", dropna=False).size().reset_index(name="Closed Count")
    grouped["% of Closures"] = grouped["Closed Count"].apply(
        lambda x: safe_percentage(x, total_closed)
    )

    result_df = grouped.sort_values("Closed Count", ascending=False).reset_index(drop=True)
    result_df = append_grand_total_row(result_df, label_col="Source")

    return AnalysisResult(
        name="Closure by Source",
        title="ICS Closures by Source Channel",
        df=result_df,
        sheet_name="67_Closure_Source",
    )


def analyze_closure_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax68: Closed ICS accounts broken down by Branch."""
    closed = ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)].copy()

    if closed.empty or "Branch" not in closed.columns:
        return AnalysisResult(
            name="Closure by Branch",
            title="ICS Closures by Branch",
            df=pd.DataFrame(columns=["Branch", "Closed Count", "% of Closures"]),
            sheet_name="68_Closure_Branch",
        )

    total_closed = len(closed)
    grouped = closed.groupby("Branch", dropna=False).size().reset_index(name="Closed Count")
    grouped["% of Closures"] = grouped["Closed Count"].apply(
        lambda x: safe_percentage(x, total_closed)
    )

    result_df = grouped.sort_values("Closed Count", ascending=False).reset_index(drop=True)
    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="Closure by Branch",
        title="ICS Closures by Branch",
        df=result_df,
        sheet_name="68_Closure_Branch",
    )


def analyze_closure_by_account_age(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax69: Closed ICS accounts by account age at closure."""
    closed = ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)].copy()

    if closed.empty or "Date Opened" not in closed.columns:
        return AnalysisResult(
            name="Closure by Account Age",
            title="ICS Closures by Account Age at Closure",
            df=pd.DataFrame(columns=["Age Range", "Closed Count", "% of Closures"]),
            sheet_name="69_Closure_Age",
        )

    # Compute account age at closure (or at reference date for those missing Date Closed)
    if "Date Closed" in closed.columns:
        ref_dates = closed["Date Closed"].fillna(pd.Timestamp.now())
    else:
        ref_dates = pd.Timestamp.now()

    closed["Account Age Days"] = (
        (pd.to_datetime(ref_dates) - pd.to_datetime(closed["Date Opened"], errors="coerce"))
        .dt.days.fillna(0)
        .astype(int)
    )

    closed = add_age_range(closed, settings)

    if "Age Range" not in closed.columns:
        return AnalysisResult(
            name="Closure by Account Age",
            title="ICS Closures by Account Age at Closure",
            df=pd.DataFrame(columns=["Age Range", "Closed Count", "% of Closures"]),
            sheet_name="69_Closure_Age",
        )

    total_closed = len(closed)
    grouped = closed.groupby("Age Range", observed=True).size().reset_index(name="Closed Count")
    grouped["Age Range"] = grouped["Age Range"].astype(str)
    grouped["% of Closures"] = grouped["Closed Count"].apply(
        lambda x: safe_percentage(x, total_closed)
    )

    return AnalysisResult(
        name="Closure by Account Age",
        title="ICS Closures by Account Age at Closure",
        df=grouped,
        sheet_name="69_Closure_Age",
    )


def analyze_net_growth_by_source(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax70: Net portfolio growth (opens - closes) broken down by source."""
    data = ics_all.copy()

    if "Date Opened" not in data.columns or "Source" not in data.columns:
        return AnalysisResult(
            name="Net Growth by Source",
            title="ICS Net Portfolio Growth by Source",
            df=pd.DataFrame(columns=["Source", "Opens", "Closes", "Net"]),
            sheet_name="70_Net_Growth_Source",
        )

    cutoff = _get_cutoff(settings)

    # Opens by source
    opened_dt = pd.to_datetime(data["Date Opened"], errors="coerce")
    data = data.copy()
    data["Open Month"] = opened_dt.dt.to_period("M").astype(str)

    if cutoff is not None:
        cutoff_period = pd.Timestamp(cutoff).to_period("M").strftime("%Y-%m")
        data = data[data["Open Month"] >= cutoff_period]

    opens = data.groupby("Source", dropna=False).size().reset_index(name="Opens")

    # Closes by source
    if "Date Closed" in data.columns:
        closed = ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)].copy()
        if cutoff is not None and "Date Closed" in closed.columns:
            closed["Close Month"] = (
                pd.to_datetime(closed["Date Closed"], errors="coerce").dt.to_period("M").astype(str)
            )
            closed = closed[closed["Close Month"] >= cutoff_period]
        closes = closed.groupby("Source", dropna=False).size().reset_index(name="Closes")
    else:
        closes = pd.DataFrame(columns=["Source", "Closes"])

    result_df = opens.merge(closes, on="Source", how="outer").fillna(0)
    result_df["Opens"] = result_df["Opens"].astype(int)
    result_df["Closes"] = result_df["Closes"].astype(int)
    result_df["Net"] = result_df["Opens"] - result_df["Closes"]

    result_df = result_df.sort_values("Net", ascending=False).reset_index(drop=True)
    result_df = append_grand_total_row(result_df, label_col="Source")

    return AnalysisResult(
        name="Net Growth by Source",
        title="ICS Net Portfolio Growth by Source",
        df=result_df,
        sheet_name="70_Net_Growth_Source",
    )


def analyze_closure_rate_trend(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax82: Monthly closure rate trend -- closures per month as % of portfolio."""
    if "Date Closed" not in ics_all.columns:
        return AnalysisResult(
            name="Closure Rate Trend",
            title="ICS Monthly Closure Rate Trend",
            df=pd.DataFrame(columns=["Month", "Closures", "Portfolio Size", "Closure Rate %"]),
            sheet_name="82_Closure_Rate",
        )

    closed = ics_all[ics_all["Stat Code"].isin(settings.closed_stat_codes)].copy()
    if closed.empty or closed["Date Closed"].isna().all():
        return AnalysisResult(
            name="Closure Rate Trend",
            title="ICS Monthly Closure Rate Trend",
            df=pd.DataFrame(columns=["Month", "Closures", "Portfolio Size", "Closure Rate %"]),
            sheet_name="82_Closure_Rate",
        )

    closed["Close Month"] = (
        pd.to_datetime(closed["Date Closed"], errors="coerce").dt.to_period("M").astype(str)
    )
    closed = closed.dropna(subset=["Close Month"])

    # Count closures per month
    monthly = closed.groupby("Close Month").size().reset_index(name="Closures")
    monthly = monthly.sort_values("Close Month").reset_index(drop=True)

    # Portfolio size = total ICS at each point (approximate as total minus cumulative closures)
    total_ics = len(ics_all)
    monthly["Cumulative Closures"] = monthly["Closures"].cumsum()
    monthly["Portfolio Size"] = total_ics - monthly["Cumulative Closures"] + monthly["Closures"]
    monthly["Closure Rate %"] = monthly.apply(
        lambda row: safe_percentage(row["Closures"], row["Portfolio Size"]), axis=1
    )

    result_df = monthly[["Close Month", "Closures", "Portfolio Size", "Closure Rate %"]].rename(
        columns={"Close Month": "Month"}
    )

    return AnalysisResult(
        name="Closure Rate Trend",
        title="ICS Monthly Closure Rate Trend",
        df=result_df,
        sheet_name="82_Closure_Rate",
    )
