"""ICS pipeline runner -- bridges PipelineContext to ICS toolkit pipelines."""

from __future__ import annotations

import logging
from pathlib import Path

from shared.context import PipelineContext
from shared.types import AnalysisResult as SharedResult

logger = logging.getLogger(__name__)


def run_ics(ctx: PipelineContext) -> dict[str, SharedResult]:
    """Run ICS analysis pipeline via PipelineContext bridge.

    Expects ctx.input_files to contain an 'ics' key pointing to the
    ICS data file (.xlsx or .csv).
    """
    from ics_toolkit.analysis.pipeline import export_outputs, run_pipeline
    from ics_toolkit.settings import Settings

    data_file = ctx.input_files.get("ics")
    if not data_file:
        raise FileNotFoundError("No 'ics' input file in PipelineContext")

    kwargs: dict = {"output_dir": ctx.output_dir}
    if ctx.client_id:
        kwargs["client_id"] = ctx.client_id
    if ctx.client_name:
        kwargs["client_name"] = ctx.client_name

    settings = Settings.for_analysis(data_file=Path(data_file), **kwargs)

    def _progress_bridge(msg: str, status: str = "") -> None:
        if ctx.progress_callback:
            ctx.progress_callback(f"[ICS] {msg}")

    result = run_pipeline(settings.analysis, on_progress=_progress_bridge)
    export_outputs(result)
    return _convert_results(result.analyses)


def run_ics_append(ctx: PipelineContext) -> dict[str, SharedResult]:
    """Run ICS append pipeline via PipelineContext bridge.

    Expects ctx.input_files to contain a 'base_dir' key pointing to
    the directory with ICS source files to organize and merge.
    """
    from ics_toolkit.append.pipeline import run_pipeline
    from ics_toolkit.settings import Settings

    base_dir = ctx.input_files.get("base_dir")
    if not base_dir:
        raise FileNotFoundError("No 'base_dir' input file in PipelineContext")

    ars_dir = ctx.input_files.get("ars_dir")
    settings = Settings.for_append(
        base_dir=Path(base_dir),
        ars_dir=Path(ars_dir) if ars_dir else None,
    )

    def _progress_bridge(msg: str, status: str = "") -> None:
        if ctx.progress_callback:
            ctx.progress_callback(f"[ICS Append] {msg}")

    result = run_pipeline(settings.append, on_progress=_progress_bridge)
    return {
        "append_result": SharedResult(
            name="ics_append",
            data={},
            summary=f"Append complete: {len(result.matched)} matched",
            metadata={"matched": len(result.matched), "unmatched": len(result.unmatched)},
        )
    }


def _convert_results(analyses: list) -> dict[str, SharedResult]:
    """Convert ICS AnalysisResult list to shared AnalysisResult dict."""
    results: dict[str, SharedResult] = {}
    for ar in analyses:
        if ar.error:
            logger.warning("Skipping failed analysis: %s (%s)", ar.name, ar.error)
            continue
        meta = dict(ar.metadata) if ar.metadata else {}
        meta["title"] = ar.title
        if ar.sheet_name:
            meta["sheet_name"] = ar.sheet_name
        results[ar.name] = SharedResult(
            name=ar.name,
            data={"main": ar.df},
            summary=ar.title,
            metadata=meta,
        )
    return results
