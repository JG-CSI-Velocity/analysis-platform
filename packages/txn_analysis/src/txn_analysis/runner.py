"""Transaction pipeline runner -- bridges PipelineContext to txn_analysis pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from shared.context import PipelineContext
from shared.types import AnalysisResult as SharedResult

logger = logging.getLogger(__name__)


def run_txn(ctx: PipelineContext) -> dict[str, SharedResult]:
    """Run all transaction analyses via PipelineContext bridge.

    Supports three input modes:
      - Pre-loaded DataFrame: ctx.data (multi-file data already in memory)
      - Single file: ctx.input_files["tran"] (CSV/Excel)
      - Transaction dir + ODD: ctx.input_files["txn_dir"] + ctx.input_files["odd"]

    Converts PipelineContext -> Settings -> run_pipeline -> SharedResult dict.
    """
    from txn_analysis.pipeline import export_outputs, run_pipeline
    from txn_analysis.settings import Settings

    has_preloaded = ctx.data is not None
    data_file = ctx.input_files.get("tran")
    txn_dir = ctx.input_files.get("txn_dir")
    odd_file = ctx.input_files.get("odd")

    if not has_preloaded and not data_file and not txn_dir:
        raise FileNotFoundError("No 'tran' or 'txn_dir' input file in PipelineContext")

    kwargs: dict = {
        "output_dir": ctx.output_dir,
        "client_id": ctx.client_id or None,
        "client_name": ctx.client_name or None,
    }
    # Only set data_file if we have a real path (not the "(preloaded)" sentinel)
    if data_file and not has_preloaded:
        kwargs["data_file"] = Path(data_file)
    if txn_dir:
        kwargs["transaction_dir"] = Path(txn_dir)
    if odd_file:
        kwargs["odd_file"] = Path(odd_file)

    # Pass segment config from client_config if present
    client_cfg = ctx.client_config or {}
    seg_cfg = client_cfg.get("segments", {})
    if seg_cfg:
        from txn_analysis.settings import SegmentConfig

        kwargs["segments"] = SegmentConfig(**seg_cfg)

    settings = Settings(**kwargs)

    # TXN pipeline has 3 internal steps (load=0, analyze=1, charts=2).
    # We add export as step 3, giving 4 total for smooth progress.
    _total = 4

    def _progress_bridge(step: int, _internal_total: int, msg: str) -> None:
        if ctx.progress_callback:
            ctx.progress_callback(f"[{step}/{_total}] {msg}")

    # Pass pre-loaded DataFrame if available (skips file I/O in pipeline)
    result = run_pipeline(settings, on_progress=_progress_bridge, pre_loaded_df=ctx.data)

    if ctx.progress_callback:
        ctx.progress_callback(f"[3/{_total}] Exporting results...")
    export_outputs(result)
    if ctx.progress_callback:
        n = len([a for a in result.analyses if a.error is None])
        ctx.progress_callback(f"[3/{_total}] Export complete -- {n} analyses")

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
