"""Base types and helpers for all analyses.

Canonical types and helpers live in the ``shared`` package.
Re-exported here so existing TXN code needs zero import changes.
``add_grand_total`` is TXN-specific and stays here.
"""

from __future__ import annotations

import pandas as pd

from shared.helpers import safe_percentage
from shared.types import AnalysisResult

__all__ = ["AnalysisResult", "safe_percentage", "add_grand_total"]


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
