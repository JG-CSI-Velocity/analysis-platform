"""Common types and result containers used across all pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class AnalysisResult:
    """Immutable container for a single analysis output.

    This is the canonical result type shared across all pipelines (ARS, TXN, ICS).
    Each pipeline's runner converts internal results to this type at the boundary.

    Fields:
        name: Unique identifier for the analysis (e.g., "top_merchants_by_spend").
        title: Human-readable display title (e.g., "Top Merchants by Spend").
        data: Dict of DataFrames. Use ``{"main": df}`` for single-DataFrame results.
        charts: List of chart image paths (PNG).
        error: Error message if the analysis failed; None on success.
        summary: Brief text summary of findings.
        metadata: Arbitrary extra data (sheet_name, slide_id, counts, etc.).
    """

    name: str
    title: str = ""
    data: dict[str, pd.DataFrame] = field(default_factory=dict)
    charts: list[Path] = field(default_factory=list)
    error: str | None = None
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """True if the analysis completed without error."""
        return self.error is None

    @property
    def df(self) -> pd.DataFrame:
        """Convenience: return the 'main' DataFrame, or empty if missing."""
        return self.data.get("main", pd.DataFrame())

    @property
    def sheet_name(self) -> str:
        """Convenience: return sheet_name from metadata, or derive from name."""
        return self.metadata.get("sheet_name", self.name.replace(" ", "_")[:31])

    @classmethod
    def from_df(
        cls,
        name: str,
        title: str,
        df: pd.DataFrame,
        *,
        error: str | None = None,
        sheet_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        """Create a result from a single DataFrame (convenience for ICS/TXN)."""
        meta = dict(metadata) if metadata else {}
        if sheet_name is not None:
            meta["sheet_name"] = sheet_name
        elif "sheet_name" not in meta:
            meta["sheet_name"] = name.replace(" ", "_")[:31]
        return cls(
            name=name,
            title=title,
            data={"main": df} if df is not None else {},
            error=error,
            metadata=meta,
        )
