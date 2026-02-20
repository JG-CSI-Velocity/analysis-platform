"""Cohort analyses (ax27, ax28): Activation and heatmap. Detail analyses in cohort_detail.py."""

from datetime import datetime

import pandas as pd
from dateutil.relativedelta import relativedelta

from ics_toolkit.analysis.analyses.base import AnalysisResult, safe_percentage
from ics_toolkit.analysis.utils import add_l12m_activity, add_opening_month
from ics_toolkit.settings import AnalysisSettings as Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prepare_cohort_data(
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> pd.DataFrame:
    """Add Opening Month, filter to >= cohort_start, add L12M activity."""
    data = ics_stat_o_debit.copy()
    data = add_opening_month(data)

    if "Opening Month" not in data.columns:
        return pd.DataFrame()

    if settings.cohort_start:
        data = data[data["Opening Month"] >= settings.cohort_start].copy()

    data = add_l12m_activity(data, settings.last_12_months)
    return data


def _cohort_month_offset(opening_month: str, offset_months: int) -> str:
    """Given 'YYYY-MM' and an offset, return the month tag (e.g. 'Feb25')."""
    dt = datetime.strptime(opening_month, "%Y-%m")
    target = dt + relativedelta(months=offset_months)
    return target.strftime("%b%y")


MILESTONE_OFFSETS = {
    "M1": 0,
    "M3": 2,
    "M6": 5,
    "M12": 11,
}


# ---------------------------------------------------------------------------
# ax27: Cohort Activation
# ---------------------------------------------------------------------------


def analyze_cohort_activation(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax27: Cohort Activation by Opening Month with milestone activation rates."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    if data.empty:
        cols = [
            "Opening Month",
            "Cohort Size",
            "Avg Bal",
            "M1 Active",
            "M1 Activation %",
            "M3 Active",
            "M3 Activation %",
            "M6 Active",
            "M6 Activation %",
            "M12 Active",
            "M12 Activation %",
        ]
        return AnalysisResult(
            name="Cohort Activation",
            title="ICS Stat O Debit - Cohort Activation",
            df=pd.DataFrame(columns=cols),
            sheet_name="27_Cohort_Activ",
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

            if tag in settings.last_12_months and swipe_col in cohort_data.columns:
                active = int((cohort_data[swipe_col] > 0).sum())
                row[f"{milestone} Active"] = active
                row[f"{milestone} Activation %"] = safe_percentage(active, size)
            else:
                row[f"{milestone} Active"] = None
                row[f"{milestone} Activation %"] = None

        rows.append(row)

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Cohort Activation",
        title="ICS Stat O Debit - Cohort Activation",
        df=result_df,
        sheet_name="27_Cohort_Activ",
    )


# ---------------------------------------------------------------------------
# ax28: Cohort Heatmap
# ---------------------------------------------------------------------------


def analyze_cohort_heatmap(
    df: pd.DataFrame,
    ics_all: pd.DataFrame,
    ics_stat_o: pd.DataFrame,
    ics_stat_o_debit: pd.DataFrame,
    settings: Settings,
) -> AnalysisResult:
    """ax28: Cohort Heatmap -- total swipes per L12M month for each cohort."""
    data = _prepare_cohort_data(ics_stat_o_debit, settings)

    if data.empty:
        cols = ["Opening Month"] + settings.last_12_months
        return AnalysisResult(
            name="Cohort Heatmap",
            title="ICS Stat O Debit - Cohort Heatmap",
            df=pd.DataFrame(columns=cols),
            sheet_name="28_Cohort_Heatmap",
        )

    cohorts = sorted(data["Opening Month"].unique())
    rows = []

    for cohort in cohorts:
        cohort_data = data[data["Opening Month"] == cohort]
        cohort_date = datetime.strptime(cohort, "%Y-%m")
        row = {"Opening Month": cohort}

        for tag in settings.last_12_months:
            tag_date = datetime.strptime(tag, "%b%y")
            if tag_date < cohort_date:
                # Month before this cohort existed -- leave blank
                row[tag] = None
            else:
                swipe_col = f"{tag} Swipes"
                if swipe_col in cohort_data.columns:
                    row[tag] = int(cohort_data[swipe_col].sum())
                else:
                    row[tag] = None

        rows.append(row)

    result_df = pd.DataFrame(rows)

    return AnalysisResult(
        name="Cohort Heatmap",
        title="ICS Stat O Debit - Cohort Heatmap",
        df=result_df,
        sheet_name="28_Cohort_Heatmap",
    )
