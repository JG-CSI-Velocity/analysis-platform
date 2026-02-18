"""Base analysis infrastructure: AnalysisResult dataclass and helpers."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class AnalysisResult:
    """Result of a single analysis."""

    name: str
    title: str
    df: pd.DataFrame
    error: str | None = None
    sheet_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.sheet_name:
            self.sheet_name = self.name.replace(" ", "_")[:31]


def safe_percentage(numerator: float, denominator: float) -> float:
    """Compute percentage with zero-division guard. Returns 0-100."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return round((numerator / denominator) * 100, 2)


def safe_ratio(numerator: float, denominator: float, decimals: int = 2) -> float:
    """Compute ratio with zero-division guard."""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return round(numerator / denominator, decimals)
