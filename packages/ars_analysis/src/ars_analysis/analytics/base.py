"""Base class and result container for all analytics modules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from ars_analysis.pipeline.context import PipelineContext

SectionName = Literal[
    "overview",
    "dctr",
    "rege",
    "attrition",
    "value",
    "mailer",
    "transaction",
    "ics",
    "insights",
]


@dataclass
class AnalysisResult:
    """Standard output container for one analysis."""

    slide_id: str
    title: str
    chart_path: Path | None = None
    excel_data: dict[str, pd.DataFrame] | None = None
    notes: str = ""
    success: bool = True
    error: str = ""
    layout_index: int = 8  # LAYOUT_CUSTOM (2025-CSI-PPT-Template)
    slide_type: str = "screenshot"
    kpis: dict[str, str] | None = None
    extra_charts: list[Path] | None = None
    bullets: list[str] | None = None


class AnalysisModule(ABC):
    """Base class for all analytics modules.

    At 300+ clients, the ABC provides:
    - Centralized column validation before wasting processing time
    - Uniform error isolation per module (one failure doesn't kill the batch)
    - Consistent logging of which modules ran/failed per client
    """

    module_id: str
    display_name: str
    section: SectionName

    # Subclasses override. Tuples prevent mutable default sharing.
    required_columns: tuple[str, ...] = ()
    required_ctx_keys: tuple[str, ...] = ()

    @abstractmethod
    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        """Execute all analyses. Return ordered results."""

    # Columns with auto-detection equivalents (don't fail validation for these)
    _FLEXIBLE_COLUMNS: dict[str, tuple[str, ...]] = {
        "Debit?": ("Debit?", "Debit", "DC Indicator", "DC_Indicator"),
    }

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Check prerequisites. Return error messages (empty = OK)."""
        errors: list[str] = []
        if ctx.data is None:
            errors.append("No data loaded in context")
            return errors
        data_cols = set(ctx.data.columns)
        for req_col in self.required_columns:
            if req_col in data_cols:
                continue
            # Check if any equivalent column exists
            equivalents = self._FLEXIBLE_COLUMNS.get(req_col, ())
            if equivalents and any(eq in data_cols for eq in equivalents):
                continue
            errors.append(f"Missing column: {req_col}")
        return errors
