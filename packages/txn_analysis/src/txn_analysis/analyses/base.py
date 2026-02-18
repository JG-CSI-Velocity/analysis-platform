"""Base types and helpers for all analyses."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AnalysisResult:
    """Outcome of a single analysis function."""

    name: str
    title: str
    df: pd.DataFrame
    error: str | None = None
    sheet_name: str | None = None
    metadata: dict = field(default_factory=dict)


def safe_percentage(part: float, total: float) -> float:
    """Return part/total * 100 without ZeroDivisionError."""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def add_grand_total(df: pd.DataFrame, label_col: str) -> pd.DataFrame:
    """Append a Grand Total row to *df*, summing numeric columns.

    Uses pd.to_numeric(errors='coerce') to avoid object-dtype corruption.
    """
    if df.empty:
        return df

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    totals = {col: pd.to_numeric(df[col], errors="coerce").sum() for col in numeric_cols}
    totals[label_col] = "Grand Total"

    total_row = pd.DataFrame([totals])
    result = pd.concat([df, total_row], ignore_index=True)

    for col in numeric_cols:
        result[col] = pd.to_numeric(result[col], errors="coerce")

    return result
