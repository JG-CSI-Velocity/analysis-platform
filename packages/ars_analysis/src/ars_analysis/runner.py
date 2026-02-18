"""ARS pipeline runner — orchestrates all A1-A15 analyses."""

from __future__ import annotations

from shared.context import PipelineContext
from shared.types import AnalysisResult


def run_ars(ctx: PipelineContext) -> dict[str, AnalysisResult]:
    """Run all ARS analyses and return results keyed by analysis ID.

    TODO: Port analysis logic from ars_analysis-jupyter (Phase 3).
    """
    raise NotImplementedError("ARS analysis not yet ported — see Phase 3 of the plan")
