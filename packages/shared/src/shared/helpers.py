"""Shared helper functions used across analysis pipelines."""

from __future__ import annotations

import pandas as pd


def safe_percentage(numerator: float, denominator: float) -> float:
    """Compute percentage with zero-division and NaN guard. Returns 0-100."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return round((numerator / denominator) * 100, 2)


def safe_ratio(numerator: float, denominator: float, decimals: int = 2) -> float:
    """Compute ratio with zero-division and NaN guard."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return round(numerator / denominator, decimals)
