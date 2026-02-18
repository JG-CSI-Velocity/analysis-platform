"""ICS pipeline runner — orchestrates all ICS analyses."""

from __future__ import annotations

from shared.context import PipelineContext
from shared.types import AnalysisResult


def run_ics(ctx: PipelineContext) -> dict[str, AnalysisResult]:
    """Run all ICS analyses.

    TODO: Port from ics_toolkit (Phase 5).
    """
    raise NotImplementedError("ICS analysis not yet ported — see Phase 5 of the plan")
