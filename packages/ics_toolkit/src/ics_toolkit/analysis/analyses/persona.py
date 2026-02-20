"""Persona deep-dive analyses (ax55-ax62): classification, contribution, slicing."""

from datetime import datetime

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.cohort import (
    MILESTONE_OFFSETS,
    _cohort_month_offset,
    _prepare_cohort_data,
)
from ics_toolkit.analysis.analyses.templates import append_grand_total_row, kpi_summary
from ics_toolkit.analysis.utils import add_balance_tier
from ics_toolkit.settings import AnalysisSettings as Settings

PERSONA_ORDER = ["Fast Activator", "Slow Burner", "One and Done", "Never Activator"]


# ---------------------------------------------------------------------------
# Shared classifier
# ---------------------------------------------------------------------------


def _classify_accounts(
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> pd.DataFrame:
    """Return per-account DataFrame with Persona column + enrichment.

    Reuses cohort infrastructure. Adds: Persona, M1 Swipes, M3 Swipes,
    plus all original columns (Branch, Source, Curr Bal, L12M activity).
    """
    data = _prepare_cohort_data(ics_stat_o_debit, settings)
    if data.empty:
        return pd.DataFrame()

    cohorts = sorted(data["Opening Month"].unique())
    rows = []

    for cohort in cohorts:
        m1_tag = _cohort_month_offset(cohort, MILESTONE_OFFSETS["M1"])
        m3_tag = _cohort_month_offset(cohort, MILESTONE_OFFSETS["M3"])

        m1_col = f"{m1_tag} Swipes"
        m3_col = f"{m3_tag} Swipes"

        if m3_tag not in settings.last_12_months:
            continue
        if m3_col not in data.columns:
            continue

        cohort_data = data[data["Opening Month"] == cohort].copy()

        if m1_col in cohort_data.columns:
            cohort_data["_m1"] = cohort_data[m1_col].fillna(0).astype(int)
        else:
            cohort_data["_m1"] = 0

        cohort_data["_m3"] = cohort_data[m3_col].fillna(0).astype(int)

        for _, acct in cohort_data.iterrows():
            m1_val = acct["_m1"]
            m3_val = acct["_m3"]

            if m1_val > 0 and m3_val > 0:
                persona = "Fast Activator"
            elif m1_val == 0 and m3_val > 0:
                persona = "Slow Burner"
            elif m1_val > 0 and m3_val == 0:
                persona = "One and Done"
            else:
                persona = "Never Activator"

            row = {
                "Persona": persona,
                "M1 Swipes": m1_val,
                "M3 Swipes": m3_val,
                "Opening Month": cohort,
            }

            for col in ("Branch", "Source", "Curr Bal", "Date Opened"):
                if col in acct.index:
                    row[col] = acct[col]

            for col in ("Total L12M Swipes", "Total L12M Spend", "Active in L12M"):
                if col in acct.index:
                    row[col] = acct[col]

            rows.append(row)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _persona_pivot(classified: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Pivot classified accounts: group_col rows, persona count columns + Fast Activator %."""
    ct = pd.crosstab(classified[group_col], classified["Persona"])

    for p in PERSONA_ORDER:
        if p not in ct.columns:
            ct[p] = 0
    ct = ct[PERSONA_ORDER]

    ct["Total"] = ct.sum(axis=1)
    ct["Fast Activator %"] = ct.apply(
        lambda r: safe_percentage(r["Fast Activator"], r["Total"]), axis=1
    )

    result = ct.reset_index()
    result = result.sort_values("Total", ascending=False).reset_index(drop=True)
    return result


# ---------------------------------------------------------------------------
# ax55: Persona Overview
# ---------------------------------------------------------------------------


def analyze_persona_overview(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax55: Enhanced persona summary with rich per-persona metrics."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    cols = [
        "Persona",
        "Account Count",
        "% of Total",
        "Total M1 Swipes",
        "Total M3 Swipes",
        "Avg M1 Swipes",
        "Avg M3 Swipes",
        "Total L12M Spend",
        "Avg Balance",
    ]

    if classified.empty:
        return AnalysisResult(
            name="Persona Overview",
            title="Debit Activation Persona Overview",
            df=pd.DataFrame(columns=cols),
            sheet_name="55_Persona_Overview",
        )

    total_accounts = len(classified)
    rows = []

    for persona in PERSONA_ORDER:
        subset = classified[classified["Persona"] == persona]
        count = len(subset)
        if count == 0:
            rows.append(
                {
                    "Persona": persona,
                    "Account Count": 0,
                    "% of Total": 0.0,
                    "Total M1 Swipes": 0,
                    "Total M3 Swipes": 0,
                    "Avg M1 Swipes": 0.0,
                    "Avg M3 Swipes": 0.0,
                    "Total L12M Spend": 0.0,
                    "Avg Balance": 0.0,
                }
            )
            continue

        total_m1 = int(subset["M1 Swipes"].sum())
        total_m3 = int(subset["M3 Swipes"].sum())
        total_spend = float(subset["Total L12M Spend"].sum()) if "Total L12M Spend" in subset else 0
        avg_bal = float(subset["Curr Bal"].mean()) if "Curr Bal" in subset else 0

        rows.append(
            {
                "Persona": persona,
                "Account Count": count,
                "% of Total": safe_percentage(count, total_accounts),
                "Total M1 Swipes": total_m1,
                "Total M3 Swipes": total_m3,
                "Avg M1 Swipes": safe_ratio(total_m1, count),
                "Avg M3 Swipes": safe_ratio(total_m3, count),
                "Total L12M Spend": round(total_spend, 2),
                "Avg Balance": round(avg_bal, 2),
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Persona Overview",
        title="Debit Activation Persona Overview",
        df=result_df,
        sheet_name="55_Persona_Overview",
    )


# ---------------------------------------------------------------------------
# ax56: Persona Swipe Contribution
# ---------------------------------------------------------------------------


def analyze_persona_contribution(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax56: Concentration analysis -- % of accounts vs % of swipes/spend."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    cols = [
        "Persona",
        "% of Accounts",
        "% of M1 Swipes",
        "% of M3 Swipes",
        "% of L12M Swipes",
        "% of L12M Spend",
    ]

    if classified.empty:
        return AnalysisResult(
            name="Persona Swipe Contribution",
            title="Swipe Contribution by Persona",
            df=pd.DataFrame(columns=cols),
            sheet_name="56_Persona_Contrib",
        )

    total_accounts = len(classified)
    total_m1 = int(classified["M1 Swipes"].sum())
    total_m3 = int(classified["M3 Swipes"].sum())
    total_l12m_swipes = (
        int(classified["Total L12M Swipes"].sum()) if "Total L12M Swipes" in classified else 0
    )
    total_l12m_spend = (
        float(classified["Total L12M Spend"].sum()) if "Total L12M Spend" in classified else 0
    )

    rows = []
    for persona in PERSONA_ORDER:
        subset = classified[classified["Persona"] == persona]
        count = len(subset)
        m1 = int(subset["M1 Swipes"].sum())
        m3 = int(subset["M3 Swipes"].sum())
        l12m_sw = int(subset["Total L12M Swipes"].sum()) if "Total L12M Swipes" in subset else 0
        l12m_sp = float(subset["Total L12M Spend"].sum()) if "Total L12M Spend" in subset else 0

        rows.append(
            {
                "Persona": persona,
                "% of Accounts": safe_percentage(count, total_accounts),
                "% of M1 Swipes": safe_percentage(m1, total_m1),
                "% of M3 Swipes": safe_percentage(m3, total_m3),
                "% of L12M Swipes": safe_percentage(l12m_sw, total_l12m_swipes),
                "% of L12M Spend": safe_percentage(l12m_sp, total_l12m_spend),
            }
        )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Persona Swipe Contribution",
        title="Swipe Contribution by Persona",
        df=result_df,
        sheet_name="56_Persona_Contrib",
    )


# ---------------------------------------------------------------------------
# ax57: Persona by Branch
# ---------------------------------------------------------------------------


def analyze_persona_by_branch(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax57: Persona distribution by branch."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    pivot_cols = ["Branch"] + PERSONA_ORDER + ["Total", "Fast Activator %"]

    if classified.empty or "Branch" not in classified.columns:
        return AnalysisResult(
            name="Persona by Branch",
            title="Persona Distribution by Branch",
            df=pd.DataFrame(columns=pivot_cols),
            sheet_name="57_Persona_Branch",
        )

    result_df = _persona_pivot(classified, "Branch")
    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="Persona by Branch",
        title="Persona Distribution by Branch",
        df=result_df,
        sheet_name="57_Persona_Branch",
    )


# ---------------------------------------------------------------------------
# ax58: Persona by Source
# ---------------------------------------------------------------------------


def analyze_persona_by_source(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax58: Persona distribution by acquisition source."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    pivot_cols = ["Source"] + PERSONA_ORDER + ["Total", "Fast Activator %"]

    if classified.empty or "Source" not in classified.columns:
        return AnalysisResult(
            name="Persona by Source",
            title="Persona Distribution by Source",
            df=pd.DataFrame(columns=pivot_cols),
            sheet_name="58_Persona_Source",
        )

    result_df = _persona_pivot(classified, "Source")
    result_df = append_grand_total_row(result_df, label_col="Source")

    return AnalysisResult(
        name="Persona by Source",
        title="Persona Distribution by Source",
        df=result_df,
        sheet_name="58_Persona_Source",
    )


# ---------------------------------------------------------------------------
# ax59: Persona Revenue Impact
# ---------------------------------------------------------------------------


def analyze_persona_revenue(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax59: Revenue impact by persona with what-if scenario."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    if classified.empty or "Total L12M Spend" not in classified.columns:
        return AnalysisResult(
            name="Persona Revenue Impact",
            title="Persona Revenue Impact",
            df=kpi_summary([("No data", 0)]),
            sheet_name="59_Persona_Revenue",
        )

    interchange_rate = settings.interchange_rate
    total_spend = float(classified["Total L12M Spend"].sum())
    total_interchange = total_spend * interchange_rate

    fast = classified[classified["Persona"] == "Fast Activator"]
    slow = classified[classified["Persona"] == "Slow Burner"]
    never = classified[classified["Persona"] == "Never Activator"]

    fast_spend = float(fast["Total L12M Spend"].sum()) if len(fast) > 0 else 0
    slow_spend = float(slow["Total L12M Spend"].sum()) if len(slow) > 0 else 0

    fast_interchange = fast_spend * interchange_rate
    slow_interchange = slow_spend * interchange_rate

    avg_spend_fast = safe_ratio(fast_spend, len(fast))
    avg_spend_slow = safe_ratio(slow_spend, len(slow))

    never_count = len(never)

    # What-if: convert 25% of never activators to slow burner spend level
    revenue_lift = 0.25 * never_count * avg_spend_slow * interchange_rate

    metrics = [
        ("Total L12M Interchange", round(total_interchange, 2)),
        ("Fast Activator Interchange", round(fast_interchange, 2)),
        ("Fast Activator % of Interchange", safe_percentage(fast_interchange, total_interchange)),
        ("Slow Burner Interchange", round(slow_interchange, 2)),
        ("Avg Spend per Fast Activator", round(avg_spend_fast, 2)),
        ("Avg Spend per Slow Burner", round(avg_spend_slow, 2)),
        ("Never Activator Count", never_count),
        ("Revenue Lift (25% Never -> Slow)", round(revenue_lift, 2)),
    ]

    return AnalysisResult(
        name="Persona Revenue Impact",
        title="Persona Revenue Impact",
        df=kpi_summary(metrics),
        sheet_name="59_Persona_Revenue",
    )


# ---------------------------------------------------------------------------
# ax60: Persona by Balance Tier
# ---------------------------------------------------------------------------


def analyze_persona_by_balance(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax60: Persona distribution by balance tier."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    pivot_cols = ["Balance Tier"] + PERSONA_ORDER + ["Total", "Fast Activator %"]

    if classified.empty or "Curr Bal" not in classified.columns:
        return AnalysisResult(
            name="Persona by Balance Tier",
            title="Persona Distribution by Balance Tier",
            df=pd.DataFrame(columns=pivot_cols),
            sheet_name="60_Persona_Balance",
        )

    classified = add_balance_tier(classified, settings)

    if "Balance Tier" not in classified.columns:
        return AnalysisResult(
            name="Persona by Balance Tier",
            title="Persona Distribution by Balance Tier",
            df=pd.DataFrame(columns=pivot_cols),
            sheet_name="60_Persona_Balance",
        )

    # Use string for grouping to avoid categorical issues with crosstab
    classified["Balance Tier"] = classified["Balance Tier"].astype(str)
    result_df = _persona_pivot(classified, "Balance Tier")
    result_df = append_grand_total_row(result_df, label_col="Balance Tier")

    return AnalysisResult(
        name="Persona by Balance Tier",
        title="Persona Distribution by Balance Tier",
        df=result_df,
        sheet_name="60_Persona_Balance",
    )


# ---------------------------------------------------------------------------
# ax61: Persona Velocity
# ---------------------------------------------------------------------------


def analyze_persona_velocity(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax61: Days to first swipe bucketed by persona."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    cols = ["Persona", "Days Bucket", "Count", "% of Persona"]

    if classified.empty or "Date Opened" not in classified.columns:
        return AnalysisResult(
            name="Persona Velocity",
            title="Activation Velocity by Persona",
            df=pd.DataFrame(columns=cols),
            sheet_name="61_Persona_Velocity",
        )

    tags = settings.last_12_months
    tag_dates = {}
    for tag in tags:
        try:
            tag_dates[tag] = datetime.strptime(tag, "%b%y")
        except ValueError:
            continue

    buckets = [
        ("0-30 days", 0, 30),
        ("31-60 days", 31, 60),
        ("61-90 days", 61, 90),
        ("91-180 days", 91, 180),
        ("180+ days", 181, 999999),
    ]

    rows = []
    data = ics_stat_o_debit.copy()

    for persona in PERSONA_ORDER:
        subset = classified[classified["Persona"] == persona]
        persona_count = len(subset)

        if persona in ("Never Activator", "One and Done") or persona_count == 0:
            rows.append(
                {
                    "Persona": persona,
                    "Days Bucket": "N/A" if persona == "Never Activator" else "All",
                    "Count": persona_count,
                    "% of Persona": 100.0 if persona_count > 0 else 0.0,
                }
            )
            continue

        # For Fast Activator and Slow Burner, find first swipe month
        days_list = []
        for _, acct in subset.iterrows():
            opened = acct.get("Date Opened")
            if pd.isna(opened):
                days_list.append(None)
                continue

            opened_dt = pd.to_datetime(opened)
            first_use = None

            for tag in tags:
                swipe_col = f"{tag} Swipes"
                if swipe_col in data.columns:
                    # Look up the original account's swipe data
                    if (
                        tag in tag_dates
                        and acct.get("M1 Swipes", 0) > 0
                        or acct.get("M3 Swipes", 0) > 0
                    ):
                        # Simplified: use opening month + persona offset
                        if tag in tag_dates:
                            tag_dt = tag_dates[tag]
                            delta = (tag_dt - opened_dt).days
                            if delta >= 0:
                                first_use = tag_dt
                                break

            if first_use is None:
                days_list.append(None)
            else:
                delta = (first_use - opened_dt).days
                days_list.append(max(0, delta))

        for label, low, high in buckets:
            count = sum(1 for d in days_list if d is not None and low <= d <= high)
            rows.append(
                {
                    "Persona": persona,
                    "Days Bucket": label,
                    "Count": count,
                    "% of Persona": safe_percentage(count, persona_count),
                }
            )

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Persona Velocity",
        title="Activation Velocity by Persona",
        df=result_df,
        sheet_name="61_Persona_Velocity",
    )


# ---------------------------------------------------------------------------
# ax62: Persona Cohort Trend
# ---------------------------------------------------------------------------


def analyze_persona_cohort_trend(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax62: Persona distribution by opening cohort over time."""
    classified = _classify_accounts(ics_stat_o_debit, settings)

    cols = ["Opening Month"] + [f"{p} %" for p in PERSONA_ORDER] + ["Total"]

    if classified.empty or "Opening Month" not in classified.columns:
        return AnalysisResult(
            name="Persona Cohort Trend",
            title="Persona Trend by Opening Cohort",
            df=pd.DataFrame(columns=cols),
            sheet_name="62_Persona_Cohort",
        )

    cohorts = sorted(classified["Opening Month"].unique())
    rows = []

    for cohort in cohorts:
        cohort_data = classified[classified["Opening Month"] == cohort]
        total = len(cohort_data)
        if total == 0:
            continue

        row = {"Opening Month": cohort, "Total": total}
        for persona in PERSONA_ORDER:
            count = len(cohort_data[cohort_data["Persona"] == persona])
            row[f"{persona} %"] = safe_percentage(count, total)

        rows.append(row)

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Persona Cohort Trend",
        title="Persona Trend by Opening Cohort",
        df=result_df,
        sheet_name="62_Persona_Cohort",
    )
