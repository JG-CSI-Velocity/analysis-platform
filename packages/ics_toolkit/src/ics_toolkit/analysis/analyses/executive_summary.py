"""Executive Summary analysis (ax999): Aggregate KPIs from prior analysis results."""

from __future__ import annotations

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.analyses.benchmarks import traffic_light
from ics_toolkit.analysis.analyses.templates import kpi_summary
from ics_toolkit.settings import AnalysisSettings as Settings


def _find_result(prior_results: list[AnalysisResult], name: str) -> AnalysisResult | None:
    """Find an AnalysisResult by name from the prior results list."""
    for r in prior_results:
        if r.name == name and r.error is None:
            return r
    return None


def _extract_kpi_value(
    result: AnalysisResult | None,
    metric_name: str,
    default: str = "N/A",
) -> str:
    """Extract a value from a KPI-style Metric/Value table."""
    if result is None or result.df.empty:
        return default
    if "Metric" not in result.df.columns or "Value" not in result.df.columns:
        return default

    match = result.df[result.df["Metric"] == metric_name]
    if match.empty:
        return default
    return str(match["Value"].iloc[0])


def _extract_kpi_float(
    result: AnalysisResult | None,
    metric_name: str,
    default: float = 0.0,
) -> float:
    """Extract a numeric value from a KPI table."""
    raw = _extract_kpi_value(result, metric_name, "N/A")
    if raw == "N/A":
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def _extract_top_branch(
    result: AnalysisResult | None,
    rate_col: str = "Activation Rate",
    branch_col: str = "Branch",
    default: str = "N/A",
) -> str:
    """Extract the top branch by activation rate from a grouped result."""
    if result is None or result.df.empty:
        return default
    if rate_col not in result.df.columns or branch_col not in result.df.columns:
        return default

    filtered = result.df[result.df[branch_col] != "Total"].copy()
    if filtered.empty:
        return default

    numeric_rates = pd.to_numeric(filtered[rate_col], errors="coerce")
    valid = filtered[numeric_rates.notna()]
    if valid.empty:
        return default

    best_idx = numeric_rates[valid.index].idxmax()
    branch_name = valid.loc[best_idx, branch_col]
    rate_value = numeric_rates.loc[best_idx]
    return f"{branch_name} ({rate_value:.2%})"


def _extract_bottom_branch(
    result: AnalysisResult | None,
    rate_col: str = "Activation Rate",
    branch_col: str = "Branch",
    default: str = "N/A",
) -> str:
    """Extract the bottom branch by activation rate."""
    if result is None or result.df.empty:
        return default
    if rate_col not in result.df.columns or branch_col not in result.df.columns:
        return default

    filtered = result.df[result.df[branch_col] != "Total"].copy()
    if filtered.empty:
        return default

    numeric_rates = pd.to_numeric(filtered[rate_col], errors="coerce")
    valid = filtered[numeric_rates.notna()]
    if valid.empty:
        return default

    worst_idx = numeric_rates[valid.index].idxmin()
    branch_name = valid.loc[worst_idx, branch_col]
    rate_value = numeric_rates.loc[worst_idx]
    return f"{branch_name} ({rate_value:.2%})"


def _extract_persona_pct(
    result: AnalysisResult | None,
    category: str,
    default: str = "N/A",
) -> str:
    """Extract % of Total for a specific persona category."""
    if result is None or result.df.empty:
        return default
    if "Category" not in result.df.columns or "% of Total" not in result.df.columns:
        return default

    match = result.df[result.df["Category"] == category]
    if match.empty:
        return default

    val = match["% of Total"].iloc[0]
    return str(val)


def _extract_persona_count(
    result: AnalysisResult | None,
    category: str,
    default: int = 0,
) -> int:
    """Extract Account Count for a specific persona category."""
    if result is None or result.df.empty:
        return default
    if "Category" not in result.df.columns:
        return default

    match = result.df[result.df["Category"] == category]
    if match.empty or "Account Count" not in result.df.columns:
        return default

    try:
        return int(match["Account Count"].iloc[0])
    except (ValueError, TypeError):
        return default


def _build_narrative(
    active_rate: float,
    never_count: int,
    revenue_at_risk: float,
    top_branch: str,
    bottom_branch: str,
    debit_count: int,
) -> list[dict[str, str]]:
    """Build What / So What / Now What narrative bullets."""
    bullets = []

    if active_rate > 0:
        bullets.append(
            {
                "type": "what",
                "text": (
                    f"{active_rate:.1f}% of debit-carded ICS accounts "
                    f"were active in the last 12 months."
                ),
            }
        )

    if never_count > 0 and revenue_at_risk > 0:
        bullets.append(
            {
                "type": "so_what",
                "text": (
                    f"{never_count:,} accounts generated no interchange "
                    f"revenue -- ~${revenue_at_risk:,.0f} left on the table."
                ),
            }
        )

    now_what_parts = []
    if never_count > 0:
        now_what_parts.append("Target Never Activators with outreach")
    if bottom_branch != "N/A":
        now_what_parts.append(f"Branch {bottom_branch} has highest dormancy concentration")
    if now_what_parts:
        bullets.append(
            {
                "type": "now_what",
                "text": "; ".join(now_what_parts) + ".",
            }
        )

    return bullets


def analyze_executive_summary(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
    prior_results: list[AnalysisResult] | None = None,
) -> AnalysisResult:
    """ax999: Executive Summary aggregating key metrics from prior analyses."""
    if prior_results is None:
        prior_results = []

    total_accounts = len(df)
    ics_count = len(ics_all) if not ics_all.empty else 0
    stat_o_count = len(ics_stat_o) if not ics_stat_o.empty else 0
    debit_count = len(ics_stat_o_debit) if not ics_stat_o_debit.empty else 0

    penetration_rate = safe_percentage(ics_count, total_accounts)

    # Active rate from activity summary
    activity_result = _find_result(prior_results, "Activity Summary")
    active_rate_str = _extract_kpi_value(activity_result, "% Active", "N/A")
    try:
        active_rate = float(active_rate_str)
    except (ValueError, TypeError):
        active_rate = 0.0

    total_swipes = _extract_kpi_value(activity_result, "Total Swipes", "N/A")
    total_spend = _extract_kpi_value(activity_result, "Total Spend", "N/A")

    # Revenue impact
    revenue_result = _find_result(prior_results, "Revenue Impact")
    estimated_interchange = _extract_kpi_float(revenue_result, "Estimated Annual Interchange")
    revenue_at_risk = _extract_kpi_float(revenue_result, "Revenue at Risk (Dormant)")

    # Branch activation
    branch_result = _find_result(prior_results, "Branch Activation")
    branch_activity = _find_result(prior_results, "Activity by Branch")
    top_branch_src = branch_result if branch_result else branch_activity
    rate_col = (
        "Activation Rate"
        if top_branch_src and "Activation Rate" in top_branch_src.df.columns
        else "Activation %"
    )
    top_branch = _extract_top_branch(top_branch_src, rate_col=rate_col)
    bottom_branch = _extract_bottom_branch(top_branch_src, rate_col=rate_col)

    # Personas
    persona_result = _find_result(prior_results, "Activation Personas")
    fast_activator_pct = _extract_persona_pct(persona_result, "Fast Activator")
    never_activator_pct = _extract_persona_pct(persona_result, "Never Activator")
    never_activator_count = _extract_persona_count(persona_result, "Never Activator")

    # Build KPI table
    metrics = [
        ("Total ICS Accounts", ics_count),
        ("Penetration Rate", penetration_rate),
        ("Stat O Count", stat_o_count),
        ("Active Rate (L12M)", active_rate_str),
        ("Estimated Interchange", f"${estimated_interchange:,.2f}"),
        ("Total Swipes (L12M)", total_swipes),
        ("Total Spend (L12M)", total_spend),
        ("Top Branch", top_branch),
        ("Bottom Branch", bottom_branch),
        ("Fast Activator %", fast_activator_pct),
        ("Never Activator %", never_activator_pct),
        ("Never Activator Count", never_activator_count),
        ("Revenue at Risk", f"${revenue_at_risk:,.2f}"),
    ]
    result_df = kpi_summary(metrics)

    # Build metadata for PPTX KPI slides
    hero_kpis = {
        "Total ICS Accounts": ics_count,
        "Penetration Rate": penetration_rate,
        "Active Rate": active_rate,
        "Estimated Interchange": estimated_interchange,
        "Never Activator Count": never_activator_count,
        "Revenue at Risk": revenue_at_risk,
    }

    traffic_lights = {
        "Penetration Rate": traffic_light(penetration_rate, "penetration_rate"),
        "Active Rate": traffic_light(active_rate, "active_rate"),
    }

    narrative = _build_narrative(
        active_rate=active_rate,
        never_count=never_activator_count,
        revenue_at_risk=revenue_at_risk,
        top_branch=top_branch,
        bottom_branch=bottom_branch,
        debit_count=debit_count,
    )

    return AnalysisResult(
        name="Executive Summary",
        title="Executive Summary - Key ICS Metrics",
        df=result_df,
        sheet_name="99_Exec_Summary",
        metadata={
            "hero_kpis": hero_kpis,
            "traffic_lights": traffic_lights,
            "narrative": narrative,
        },
    )
