"""M9: Portfolio health scorecard with benchmark comparison."""

from __future__ import annotations

import pandas as pd

from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.settings import Settings

# PULSE 2024 Debit Issuer Study benchmarks (national averages).
# Updated annually when PULSE publishes new data.
PULSE_2024_BENCHMARKS = {
    "annual_spend_per_card": {"national": 17_274, "cu_avg": 9_291},
    "txn_per_card_month": {"national": 34.6, "cu_avg": 20.2},
    "avg_ticket": {"national": 46.89, "cu_avg": 40.0},
    "penetration_rate": {"national": 80.5, "cu_avg": 77.5},
    "active_card_rate": {"national": 66.3, "cu_avg": 62.5},
    "cnp_pct_of_spend": {"national": 45.0, "cu_avg": 37.5},
    "digital_wallet_pct": {"national": 38.0, "cu_avg": 27.5},
}


def analyze_portfolio_scorecard(
    df: pd.DataFrame,
    business_df: pd.DataFrame,
    personal_df: pd.DataFrame,
    settings: Settings,
    context: dict | None = None,
) -> AnalysisResult:
    """Build a 10-KPI executive scorecard from prior analysis results.

    Reads from context['interchange_summary'], context['member_segments'],
    context['completed_results'] to aggregate KPIs without recomputation.
    """
    if df.empty:
        return _empty_result()

    ctx = context or {}
    ic_info = ctx.get("interchange_summary", {})
    seg_info = ctx.get("member_segments", {})
    completed = ctx.get("completed_results", {})

    total_accounts = df["primary_account_num"].nunique()
    total_spend = df["amount"].sum()
    total_txns = len(df)

    # Compute months in dataset for annualization
    months_in_data = df["year_month"].nunique() if "year_month" in df.columns else 1

    rows: list[dict] = []

    # KPI 1: Total Active Accounts
    rows.append(_kpi("Active Accounts", total_accounts, benchmark=None))

    # KPI 2: Avg Spend per Account per Month
    avg_spend_month = total_spend / max(total_accounts, 1) / max(months_in_data, 1)
    benchmark_spend = PULSE_2024_BENCHMARKS["annual_spend_per_card"]["cu_avg"] / 12
    rows.append(
        _kpi(
            "Avg Spend/Account/Month",
            round(avg_spend_month, 2),
            benchmark=round(benchmark_spend, 2),
            fmt="$",
        )
    )

    # KPI 3: Avg Transaction Frequency (per account per month)
    avg_freq = total_txns / max(total_accounts, 1) / max(months_in_data, 1)
    rows.append(
        _kpi(
            "Avg Txn/Account/Month",
            round(avg_freq, 1),
            benchmark=PULSE_2024_BENCHMARKS["txn_per_card_month"]["cu_avg"],
        )
    )

    # KPI 4: Average Ticket
    avg_ticket = total_spend / max(total_txns, 1)
    rows.append(
        _kpi(
            "Average Ticket",
            round(avg_ticket, 2),
            benchmark=PULSE_2024_BENCHMARKS["avg_ticket"]["cu_avg"],
            fmt="$",
        )
    )

    # KPI 5: Estimated Annual Interchange Revenue
    ic_revenue = ic_info.get("total_ic_revenue", 0.0)
    annualized_ic = ic_revenue / max(months_in_data, 1) * 12 if ic_revenue > 0 else 0.0
    rows.append(
        _kpi(
            "Est. Annual Interchange Revenue",
            round(annualized_ic, 2),
            benchmark=None,
            fmt="$",
        )
    )

    # KPI 6: Competitor Exposure %
    comp_result = completed.get("competitor_high_level")
    comp_accounts = 0
    if comp_result is not None and not comp_result.df.empty:
        comp_col = "unique_accounts"
        if comp_col in comp_result.df.columns:
            comp_accounts = comp_result.df[comp_col].sum()
    comp_pct = comp_accounts / max(total_accounts, 1) * 100
    rows.append(_kpi("Competitor Exposure %", round(comp_pct, 1), benchmark=None, fmt="%"))

    # KPI 7: Financial Services Leakage %
    fs_result = completed.get("financial_services_detection")
    fs_accounts = 0
    if fs_result is not None and not fs_result.df.empty:
        if "unique_accounts" in fs_result.df.columns:
            fs_accounts = fs_result.df["unique_accounts"].sum()
    fs_pct = fs_accounts / max(total_accounts, 1) * 100
    rows.append(_kpi("Financial Services Leakage %", round(fs_pct, 1), benchmark=None, fmt="%"))

    # KPI 8: Top Merchant Concentration (top 10 = X% of spend)
    top10_pct = 0.0
    m1_result = completed.get("top_merchants_by_spend")
    if m1_result is not None and not m1_result.df.empty:
        non_total = m1_result.df[
            m1_result.df.get("merchant_consolidated", pd.Series()) != "Grand Total"
        ]
        if "pct_of_total_amount" in non_total.columns:
            top10_pct = non_total.head(10)["pct_of_total_amount"].sum()
    rows.append(
        _kpi(
            "Top 10 Merchant Concentration %",
            round(top10_pct, 1),
            benchmark=None,
            fmt="%",
        )
    )

    # KPI 9: Business vs Personal Split
    biz_pct = business_df["amount"].sum() / max(total_spend, 1) * 100
    rows.append(_kpi("Business Spend %", round(biz_pct, 1), benchmark=None, fmt="%"))

    # KPI 10: Dormant Accounts
    dormant_count = seg_info.get("dormant_count", 0)
    dormant_pct = dormant_count / max(total_accounts, 1) * 100
    rows.append(_kpi("Dormant Accounts (90+ days)", dormant_count, benchmark=None))
    rows.append(_kpi("Dormant %", round(dormant_pct, 1), benchmark=None, fmt="%"))

    result = pd.DataFrame(rows)

    return AnalysisResult(
        name="portfolio_scorecard",
        title="Portfolio Health Scorecard",
        df=result,
        sheet_name="M9 Scorecard",
        metadata={
            "months_in_data": months_in_data,
            "ic_rate": ic_info.get("ic_rate", 0.0),
            "benchmark_source": "PULSE 2024 Debit Issuer Study",
        },
    )


def _kpi(
    metric: str,
    value: float | int,
    benchmark: float | int | None = None,
    fmt: str = "",
) -> dict:
    """Build a single KPI row."""
    status = ""
    if benchmark is not None and benchmark > 0:
        ratio = value / benchmark
        if ratio >= 1.0:
            status = "Above"
        elif ratio >= 0.85:
            status = "At"
        else:
            status = "Below"

    return {
        "metric": metric,
        "value": value,
        "benchmark": benchmark if benchmark is not None else "",
        "status": status,
        "format": fmt,
    }


def _empty_result() -> AnalysisResult:
    return AnalysisResult(
        name="portfolio_scorecard",
        title="Portfolio Health Scorecard",
        df=pd.DataFrame(),
        sheet_name="M9 Scorecard",
    )
