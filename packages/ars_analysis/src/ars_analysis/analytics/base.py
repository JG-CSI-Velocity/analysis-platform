"""Base class and result container for all analytics modules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from ars_analysis.pipeline.context import PipelineContext

SectionName = Literal[
    "overview", "dctr", "rege", "attrition", "value", "mailer",
    "transaction", "ics", "insights",
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

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Check prerequisites. Return error messages (empty = OK)."""
        errors: list[str] = []
        if ctx.data is None:
            errors.append("No data loaded in context")
            return errors
        missing_cols = set(self.required_columns) - set(ctx.data.columns)
        if missing_cols:
            errors.append(f"Missing columns: {', '.join(sorted(missing_cols))}")
        return errors
