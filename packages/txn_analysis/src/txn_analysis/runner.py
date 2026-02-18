"""Transaction pipeline runner -- bridges PipelineContext to txn_analysis pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from shared.context import PipelineContext
from shared.types import AnalysisResult as SharedResult

logger = logging.getLogger(__name__)


def run_txn(ctx: PipelineContext) -> dict[str, SharedResult]:
    """Run all transaction analyses via PipelineContext bridge.

    Converts PipelineContext -> Settings -> run_pipeline -> SharedResult dict.
    """
    from txn_analysis.pipeline import export_outputs, run_pipeline
    from txn_analysis.settings import Settings

    data_file = ctx.input_files.get("tran") or ctx.input_files.get("odd")
    if not data_file:
        raise FileNotFoundError("No 'tran' or 'odd' input file in PipelineContext")

    settings = Settings.from_args(
        data_file=Path(data_file),
        output_dir=ctx.output_dir,
        client_id=ctx.client_id or None,
        client_name=ctx.client_name or None,
    )

    def _progress_bridge(step: int, total: int, msg: str) -> None:
        if ctx.progress_callback:
            ctx.progress_callback(f"[{step}/{total}] {msg}")

    result = run_pipeline(settings, on_progress=_progress_bridge)
    export_outputs(result)

    return _convert_results(result.analyses)


def run_txn_from_settings(
    data_file: str | Path,
    output_dir: str | Path = "output/",
    **kwargs,
) -> dict[str, SharedResult]:
    """Run transaction analyses directly from file path (no PipelineContext)."""
    from txn_analysis.pipeline import export_outputs, run_pipeline
    from txn_analysis.settings import Settings

    settings = Settings.from_args(data_file=Path(data_file), output_dir=Path(output_dir), **kwargs)
    result = run_pipeline(settings)
    export_outputs(result)
    return _convert_results(result.analyses)


def run_txn_v4(ctx: PipelineContext) -> dict[str, SharedResult]:
    """Run V4 storyline analyses via PipelineContext bridge.

    This runs the txnv3 storyline pipeline (S1-S9, 99+ analyses) which
    requires both a transaction file (tran) and an ODD file (odd).
    """
    from txn_analysis.v4_data_loader import load_config
    from txn_analysis.v4_run import run_pipeline as v4_run_pipeline

    config_file = ctx.input_files.get("v4_config")
    if config_file:
        config = load_config(str(config_file))
    else:
        config = {}

    # Override config with PipelineContext values
    if ctx.output_dir:
        config["output_dir"] = str(ctx.output_dir)
    if ctx.client_id:
        config["client_id"] = ctx.client_id
    if ctx.client_name:
        config["client_name"] = ctx.client_name

    # Set data paths from PipelineContext input_files
    tran_file = ctx.input_files.get("tran")
    odd_file = ctx.input_files.get("odd")
    if tran_file:
        config["transaction_file"] = str(tran_file)
    if odd_file:
        config["odd_file"] = str(odd_file)

    if not config.get("transaction_file"):
        raise FileNotFoundError("No 'tran' input file in PipelineContext for V4 pipeline")

    def _progress_bridge(step: int, total: int, msg: str) -> None:
        if ctx.progress_callback:
            ctx.progress_callback(f"[V4 {step}/{total}] {msg}")

    results, excel_path, html_path = v4_run_pipeline(
        config,
        progress_cb=_progress_bridge,
    )
    return _convert_v4_results(results)


def _convert_results(analyses: list) -> dict[str, SharedResult]:
    """Convert txn_analysis AnalysisResult list to shared AnalysisResult dict."""
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


def _convert_v4_results(storyline_results: dict) -> dict[str, SharedResult]:
    """Convert V4 storyline results to shared AnalysisResult dict.

    V4 results are keyed by storyline ID (e.g. "s1_portfolio") and each
    contains sections with figures and tables.
    """
    results: dict[str, SharedResult] = {}
    for key, sr in storyline_results.items():
        data = {}
        for i, sheet in enumerate(sr.get("sheets", [])):
            sheet_name = sheet.get("name", f"sheet_{i}")
            data[sheet_name] = sheet["df"]

        meta = {
            "title": sr.get("title", key),
            "description": sr.get("description", ""),
            "section_count": len(sr.get("sections", [])),
            "chart_count": sum(len(s.get("figures", [])) for s in sr.get("sections", [])),
        }

        results[key] = SharedResult(
            name=key,
            data=data,
            summary=sr.get("title", key),
            metadata=meta,
        )
    return results
