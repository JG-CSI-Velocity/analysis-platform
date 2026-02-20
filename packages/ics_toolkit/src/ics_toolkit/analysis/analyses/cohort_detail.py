"""Cohort detail analyses (ax29, ax31, ax32, ax34, ax36): milestones, growth, personas, branch."""

import pandas as pd

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage, safe_ratio
from ics_toolkit.analysis.analyses.cohort import (
    MILESTONE_OFFSETS,
    _cohort_month_offset,
    _prepare_cohort_data,
)
from ics_toolkit.analysis.analyses.templates import (
    append_grand_total_row,
    kpi_summary,
)
from ics_toolkit.settings import AnalysisSettings as Settings

# ---------------------------------------------------------------------------
# ax29: Cohort Milestones
# ---------------------------------------------------------------------------


def analyze_cohort_milestones(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax29: Cohort Milestones -- activation plus avg swipes/spend at each milestone."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    milestone_cols = []
    for m in MILESTONE_OFFSETS:
        milestone_cols.extend(
            [
                f"{m} Active",
                f"{m} Activation %",
                f"{m} Avg Swipes",
                f"{m} Avg Spend",
            ]
        )

    if data.empty:
        cols = ["Opening Month", "Cohort Size", "Avg Bal"] + milestone_cols
        return AnalysisResult(
            name="Cohort Milestones",
            title="ICS Stat O Debit - Cohort Milestones",
            df=pd.DataFrame(columns=cols),
            sheet_name="29_Cohort_Miles",
        )

    cohorts = sorted(data["Opening Month"].unique())
    rows = []

    for cohort in cohorts:
        cohort_data = data[data["Opening Month"] == cohort]
        size = len(cohort_data)
        if size == 0:
            continue
        avg_bal = round(cohort_data["Curr Bal"].mean(), 2)

        row = {
            "Opening Month": cohort,
            "Cohort Size": size,
            "Avg Bal": avg_bal,
        }

        for milestone, offset in MILESTONE_OFFSETS.items():
            tag = _cohort_month_offset(cohort, offset)
            swipe_col = f"{tag} Swipes"
            spend_col = f"{tag} Spend"

            if tag in settings.last_12_months and swipe_col in cohort_data.columns:
                active = int((cohort_data[swipe_col] > 0).sum())
                total_swipes = int(cohort_data[swipe_col].sum())
                total_spend = (
                    float(cohort_data[spend_col].sum()) if spend_col in cohort_data.columns else 0.0
                )

                row[f"{milestone} Active"] = active
                row[f"{milestone} Activation %"] = safe_percentage(active, size)
                row[f"{milestone} Avg Swipes"] = safe_ratio(total_swipes, size)
                row[f"{milestone} Avg Spend"] = round(safe_ratio(total_spend, size), 2)
            else:
                row[f"{milestone} Active"] = None
                row[f"{milestone} Activation %"] = None
                row[f"{milestone} Avg Swipes"] = None
                row[f"{milestone} Avg Spend"] = None

        rows.append(row)

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Cohort Milestones",
        title="ICS Stat O Debit - Cohort Milestones",
        df=result_df,
        sheet_name="29_Cohort_Miles",
    )


# ---------------------------------------------------------------------------
# ax31: Activation Summary
# ---------------------------------------------------------------------------


def analyze_activation_summary(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax31: Aggregate activation rates at M1, M3, M6, M12 across all cohorts."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    if data.empty:
        metrics = [
            ("M1 Activation Rate", None),
            ("M3 Activation Rate", None),
            ("M6 Activation Rate", None),
            ("M12 Activation Rate", None),
        ]
        return AnalysisResult(
            name="Activation Summary",
            title="ICS Stat O Debit - Activation Summary",
            df=kpi_summary(metrics),
            sheet_name="31_Activ_Summary",
        )

    cohorts = sorted(data["Opening Month"].unique())
    milestone_active = {m: 0 for m in MILESTONE_OFFSETS}
    milestone_eligible = {m: 0 for m in MILESTONE_OFFSETS}

    for cohort in cohorts:
        cohort_data = data[data["Opening Month"] == cohort]
        size = len(cohort_data)

        for milestone, offset in MILESTONE_OFFSETS.items():
            tag = _cohort_month_offset(cohort, offset)
            swipe_col = f"{tag} Swipes"

            if tag in settings.last_12_months and swipe_col in cohort_data.columns:
                milestone_eligible[milestone] += size
                milestone_active[milestone] += int((cohort_data[swipe_col] > 0).sum())

    metrics = []
    for milestone in MILESTONE_OFFSETS:
        eligible = milestone_eligible[milestone]
        active = milestone_active[milestone]
        rate = safe_percentage(active, eligible) if eligible > 0 else None
        metrics.append((f"{milestone} Activation Rate", rate))

    result_df = kpi_summary(metrics)

    return AnalysisResult(
        name="Activation Summary",
        title="ICS Stat O Debit - Activation Summary",
        df=result_df,
        sheet_name="31_Activ_Summary",
    )


# ---------------------------------------------------------------------------
# ax32: Growth Patterns
# ---------------------------------------------------------------------------


def analyze_growth_patterns(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax32: Month-over-month swipe growth between milestones for each cohort."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    growth_cols = [
        "Opening Month",
        "Cohort Size",
        "M1 Swipes",
        "M3 Swipes",
        "M6 Swipes",
        "M12 Swipes",
        "M1->M3 Growth",
        "M3->M6 Growth",
        "M6->M12 Growth",
    ]

    if data.empty:
        return AnalysisResult(
            name="Growth Patterns",
            title="ICS Stat O Debit - Growth Patterns",
            df=pd.DataFrame(columns=growth_cols),
            sheet_name="32_Growth",
        )

    cohorts = sorted(data["Opening Month"].unique())
    rows = []

    for cohort in cohorts:
        cohort_data = data[data["Opening Month"] == cohort]
        size = len(cohort_data)
        if size == 0:
            continue
        row = {"Opening Month": cohort, "Cohort Size": size}

        milestone_swipes = {}
        for milestone, offset in MILESTONE_OFFSETS.items():
            tag = _cohort_month_offset(cohort, offset)
            swipe_col = f"{tag} Swipes"

            if tag in settings.last_12_months and swipe_col in cohort_data.columns:
                milestone_swipes[milestone] = int(cohort_data[swipe_col].sum())
            else:
                milestone_swipes[milestone] = None

            row[f"{milestone} Swipes"] = milestone_swipes[milestone]

        growth_pairs = [("M1", "M3"), ("M3", "M6"), ("M6", "M12")]
        for start, end in growth_pairs:
            s_val = milestone_swipes.get(start)
            e_val = milestone_swipes.get(end)
            if s_val is not None and e_val is not None and s_val > 0:
                growth = round((e_val - s_val) / s_val, 4)
                row[f"{start}->{end} Growth"] = growth
            else:
                row[f"{start}->{end} Growth"] = None

        rows.append(row)

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Growth Patterns",
        title="ICS Stat O Debit - Growth Patterns",
        df=result_df,
        sheet_name="32_Growth",
    )


# ---------------------------------------------------------------------------
# ax34: Activation Personas
# ---------------------------------------------------------------------------


def analyze_activation_personas(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax34: Categorize accounts into activation personas based on M1 and M3 behaviour."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    persona_cols = [
        "Category",
        "Account Count",
        "Total M1 Swipes",
        "Total M3 Swipes",
        "% of Total",
    ]

    if data.empty:
        return AnalysisResult(
            name="Activation Personas",
            title="ICS Stat O Debit - Activation Personas",
            df=pd.DataFrame(columns=persona_cols),
            sheet_name="34_Personas",
        )

    cohorts = sorted(data["Opening Month"].unique())
    categorized = []

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

        if m1_col not in cohort_data.columns:
            cohort_data["_m1"] = 0
        else:
            cohort_data["_m1"] = cohort_data[m1_col].fillna(0).astype(int)

        cohort_data["_m3"] = cohort_data[m3_col].fillna(0).astype(int)

        for _, acct in cohort_data.iterrows():
            m1_val = acct["_m1"]
            m3_val = acct["_m3"]

            if m1_val > 0 and m3_val > 0:
                category = "Fast Activator"
            elif m1_val == 0 and m3_val > 0:
                category = "Slow Burner"
            elif m1_val > 0 and m3_val == 0:
                category = "One and Done"
            else:
                category = "Never Activator"

            categorized.append(
                {
                    "Category": category,
                    "M1 Swipes": m1_val,
                    "M3 Swipes": m3_val,
                }
            )

    if not categorized:
        return AnalysisResult(
            name="Activation Personas",
            title="ICS Stat O Debit - Activation Personas",
            df=pd.DataFrame(columns=persona_cols),
            sheet_name="34_Personas",
        )

    cat_df = pd.DataFrame(categorized)
    total_accounts = len(cat_df)

    summary = (
        cat_df.groupby("Category")
        .agg(
            account_count=("Category", "size"),
            total_m1=("M1 Swipes", "sum"),
            total_m3=("M3 Swipes", "sum"),
        )
        .reset_index()
    )

    summary.columns = ["Category", "Account Count", "Total M1 Swipes", "Total M3 Swipes"]
    summary["% of Total"] = summary["Account Count"].apply(
        lambda x: safe_percentage(x, total_accounts)
    )

    category_order = ["Fast Activator", "Slow Burner", "One and Done", "Never Activator"]
    summary["Category"] = pd.Categorical(
        summary["Category"], categories=category_order, ordered=True
    )
    summary = summary.sort_values("Category").reset_index(drop=True)
    summary["Category"] = summary["Category"].astype(str)

    return AnalysisResult(
        name="Activation Personas",
        title="ICS Stat O Debit - Activation Personas",
        df=summary,
        sheet_name="34_Personas",
    )


# ---------------------------------------------------------------------------
# ax36: Branch Activation
# ---------------------------------------------------------------------------


def analyze_branch_activation(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax36: Branch-level activation for ICS Stat O Debit cohort accounts."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    if data.empty:
        result_df = pd.DataFrame(
            columns=[
                "Branch",
                "Cohort Size",
                "Active Count",
                "Activation Rate",
            ]
        )
        return AnalysisResult(
            name="Branch Activation",
            title="ICS Stat O Debit - Branch Activation",
            df=result_df,
            sheet_name="36_Branch_Activ",
        )

    grouped = (
        data.groupby("Branch", dropna=False)
        .agg(
            cohort_size=("ICS Account", "size"),
            active_count=("Active in L12M", "sum"),
        )
        .reset_index()
    )

    grouped["Active Count"] = grouped["active_count"].astype(int)
    grouped["Cohort Size"] = grouped["cohort_size"]
    grouped["Activation Rate"] = grouped.apply(
        lambda row: safe_percentage(row["active_count"], row["cohort_size"]), axis=1
    )

    result_df = (
        grouped[["Branch", "Cohort Size", "Active Count", "Activation Rate"]]
        .sort_values("Cohort Size", ascending=False)
        .reset_index(drop=True)
    )

    result_df = append_grand_total_row(result_df, label_col="Branch")

    return AnalysisResult(
        name="Branch Activation",
        title="ICS Stat O Debit - Branch Activation",
        df=result_df,
        sheet_name="36_Branch_Activ",
    )
