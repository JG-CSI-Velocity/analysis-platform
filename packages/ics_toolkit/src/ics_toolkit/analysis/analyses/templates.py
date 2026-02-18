"""Parameterized analysis templates.

Templates:
- grouped_summary: group by an existing column, aggregate, add percentages
- binned_summary: bin a numeric column, then run grouped aggregation
- crosstab_summary: cross-tabulate two categorical columns
- kpi_summary: build a two-column Metric/Value KPI table
- append_grand_total_row: add a Grand Total row to any summary DataFrame
"""

from typing import Any

import numpy as np
import pandas as pd

from ics_toolkit.analysis.analyses.base import safe_percentage


def grouped_summary(
    df: pd.DataFrame,
    group_col: str,
    agg_specs: dict[str, tuple[str, str]],
    pct_of: list[str] | None = None,
    label_map: dict | None = None,
    sort_by: str | None = None,
    sort_ascending: bool = False,
) -> pd.DataFrame:
    """Run a grouped aggregation with optional percentages.

    Args:
        df: Input DataFrame.
        group_col: Column to group by.
        agg_specs: {output_col: (source_col, agg_func)} for pandas named agg.
        pct_of: Column names to compute '% of {col}' as share of total (0-100).
        label_map: Optional mapping to rename group labels.
        sort_by: Column to sort by. Defaults to first agg column.
        sort_ascending: Sort direction.
    """
    if df.empty:
        cols = [group_col] + list(agg_specs.keys())
        if pct_of:
            cols += [f"% of {c}" for c in pct_of]
        return pd.DataFrame(columns=cols)

    result = df.groupby(group_col, dropna=False).agg(**agg_specs).reset_index()

    if label_map:
        result[group_col] = result[group_col].map(label_map).fillna(result[group_col])

    if pct_of:
        for col in pct_of:
            total = result[col].sum()
            result[f"% of {col}"] = result[col].apply(lambda x: safe_percentage(x, total))

    if sort_by and sort_by in result.columns:
        result = result.sort_values(sort_by, ascending=sort_ascending).reset_index(drop=True)
    elif not sort_by and agg_specs:
        first_col = list(agg_specs.keys())[0]
        result = result.sort_values(first_col, ascending=False).reset_index(drop=True)

    return result


def binned_summary(
    df: pd.DataFrame,
    value_col: str,
    bins: list,
    labels: list[str],
    bin_name: str,
    agg_specs: dict[str, tuple[str, str]],
    pct_of: list[str] | None = None,
) -> pd.DataFrame:
    """Bin a numeric column, then run grouped aggregation on the bins."""
    if df.empty:
        cols = [bin_name] + list(agg_specs.keys())
        if pct_of:
            cols += [f"% of {c}" for c in pct_of]
        return pd.DataFrame(columns=cols)

    df = df.copy()
    df[bin_name] = pd.cut(df[value_col], bins=bins, labels=labels, include_lowest=True)

    result = df.groupby(bin_name, observed=True).agg(**agg_specs).reset_index()
    result[bin_name] = result[bin_name].astype(str)

    if pct_of:
        for col in pct_of:
            total = result[col].sum()
            result[f"% of {col}"] = result[col].apply(lambda x: safe_percentage(x, total))

    return result


def crosstab_summary(
    df: pd.DataFrame,
    row_col: str,
    col_col: str,
    add_totals: bool = True,
    add_rate_col: str | None = None,
    rate_numerator: str | None = None,
) -> pd.DataFrame:
    """Cross-tabulate two categorical columns.

    Args:
        df: Input DataFrame.
        row_col: Column for rows.
        col_col: Column for columns.
        add_totals: Add row and column totals.
        add_rate_col: Name for a rate column (e.g., '% with Debit').
        rate_numerator: Which column value to use as numerator for rate.
    """
    if df.empty:
        return pd.DataFrame(columns=[row_col])

    ct = pd.crosstab(
        df[row_col],
        df[col_col],
        margins=add_totals,
        margins_name="Total",
    ).reset_index()

    if add_rate_col and rate_numerator and rate_numerator in ct.columns:
        ct[add_rate_col] = np.where(
            ct["Total"] > 0,
            ((ct[rate_numerator] / ct["Total"]) * 100).round(2),
            0.0,
        )

    # Sort by Total descending (excluding the Total row)
    if add_totals and "Total" in ct.columns:
        total_row = ct[ct[row_col] == "Total"]
        data_rows = ct[ct[row_col] != "Total"].sort_values("Total", ascending=False)
        ct = pd.concat([data_rows, total_row], ignore_index=True)

    return ct


def kpi_summary(metrics: list[tuple[str, Any]]) -> pd.DataFrame:
    """Build a two-column Metric/Value table from a list of (name, value) tuples."""
    return pd.DataFrame(metrics, columns=["Metric", "Value"])


def append_grand_total_row(
    summary_df: pd.DataFrame,
    label_col: str,
    label: str = "Total",
) -> pd.DataFrame:
    """Append a Grand Total row to a summary DataFrame.

    Sum columns get summed. Percentage columns get 100.0.
    Average/ratio columns get the mean.
    """
    if summary_df.empty:
        return summary_df

    totals: dict[str, Any] = {}
    for col in summary_df.columns:
        if col == label_col:
            totals[col] = label
        elif "%" in col or "Pct" in col:
            totals[col] = 100.0
        elif "Avg" in col or "Average" in col or "Mean" in col:
            totals[col] = summary_df[col].mean()
        elif "Ratio" in col:
            totals[col] = summary_df[col].mean()
        else:
            try:
                totals[col] = summary_df[col].sum()
            except TypeError:
                totals[col] = ""

    total_row = pd.DataFrame([totals])
    return pd.concat([summary_df, total_row], ignore_index=True)
