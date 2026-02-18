"""Transaction pipeline runner — orchestrates all storyline modules."""

from __future__ import annotations

from shared.context import PipelineContext
from shared.types import AnalysisResult


def run_txn(ctx: PipelineContext) -> dict[str, AnalysisResult]:
    """Run all transaction storyline analyses.

    TODO: Port from txnv3 (Phase 4).
    """
    raise NotImplementedError("Transaction analysis not yet ported — see Phase 4 of the plan")
