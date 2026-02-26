"""Pipeline orchestrator -- dispatches to ARS, Transaction, and ICS runners."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from shared.context import PipelineContext
from shared.types import AnalysisResult

logger = logging.getLogger(__name__)

PIPELINE_NAMES = ("ars", "txn", "ics", "ics_append")


def run_pipeline(
    pipeline: str,
    *,
    input_files: dict[str, Path],
    output_dir: Path = Path("output"),
    client_id: str = "",
    client_name: str = "",
    client_config: dict | None = None,
    progress_callback: Callable[[str], None] | None = None,
    pre_loaded_data: pd.DataFrame | None = None,
) -> dict[str, AnalysisResult]:
    """Run a named pipeline and return results.

    Parameters
    ----------
    pipeline : str
        One of 'ars', 'txn', 'ics', 'ics_append'.
    input_files : dict
        Mapping of file role to Path (e.g. {"oddd": Path("..."), "tran": Path("...")}).
    output_dir : Path
        Where to write outputs.
    client_id, client_name : str
        Client identifiers.
    client_config : dict | None
        Pipeline-specific client config (e.g. ARS config_path).
    progress_callback : callable | None
        Optional progress callback.
    pre_loaded_data : DataFrame | None
        Pre-loaded DataFrame (e.g. multi-file TXN data already in memory).
        Skips file I/O when provided.

    Returns
    -------
    dict[str, AnalysisResult]
    """
    if pipeline not in PIPELINE_NAMES:
        raise ValueError(f"Unknown pipeline: {pipeline!r}. Choose from {PIPELINE_NAMES}")

    ctx = PipelineContext(
        client_id=client_id,
        client_name=client_name,
        input_files=input_files,
        output_dir=output_dir,
        chart_dir=output_dir / "charts",
        client_config=client_config or {},
        progress_callback=progress_callback,
        data=pre_loaded_data,
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    if pipeline == "ars":
        from ars_analysis.runner import run_ars

        return run_ars(ctx)
    elif pipeline == "txn":
        from txn_analysis.runner import run_txn

        results = run_txn(ctx)
        _ensure_deck(results, pipeline, client_id, client_name, output_dir, progress_callback)
        return results
    elif pipeline == "ics":
        from ics_toolkit.runner import run_ics

        results = run_ics(ctx)
        _ensure_deck(results, pipeline, client_id, client_name, output_dir, progress_callback)
        return results
    elif pipeline == "ics_append":
        from ics_toolkit.runner import run_ics_append

        return run_ics_append(ctx)
    else:
        raise ValueError(f"Unknown pipeline: {pipeline!r}")


def run_all(
    *,
    input_files: dict[str, Path],
    output_dir: Path = Path("output"),
    client_id: str = "",
    client_name: str = "",
    pipelines: list[str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, dict[str, AnalysisResult]]:
    """Run multiple pipelines and return combined results.

    Parameters
    ----------
    pipelines : list[str] | None
        Which pipelines to run. None means all applicable ones
        (determined by which input files are present).

    Returns
    -------
    dict[str, dict[str, AnalysisResult]]
        Outer key is pipeline name, inner is analysis results.
    """
    if pipelines is None:
        pipelines = _detect_pipelines(input_files)

    all_results: dict[str, dict[str, AnalysisResult]] = {}
    total = len(pipelines)

    for i, name in enumerate(pipelines, 1):
        if progress_callback:
            progress_callback(f"[{i}/{total}] Running {name} pipeline...")
        try:
            results = run_pipeline(
                name,
                input_files=input_files,
                output_dir=output_dir / name,
                client_id=client_id,
                client_name=client_name,
                progress_callback=progress_callback,
            )
            all_results[name] = results
            logger.info("Pipeline %s produced %d results", name, len(results))
        except Exception:
            logger.exception("Pipeline %s failed", name)
            all_results[name] = {}

    return all_results


def _ensure_deck(
    results: dict[str, AnalysisResult],
    pipeline: str,
    client_id: str,
    client_name: str,
    output_dir: Path,
    progress_callback: Callable[[str], None] | None = None,
) -> None:
    """Build a PPTX deck if the pipeline didn't already produce one."""
    if not results:
        return

    existing = list(output_dir.rglob("*.pptx"))
    if existing:
        logger.info("Pipeline %s already produced %d PPTX file(s)", pipeline, len(existing))
        return

    try:
        from shared.deck import build_deck_from_results

        if progress_callback:
            progress_callback(f"Building {pipeline} slide deck...")

        deck_path = build_deck_from_results(
            results,
            pipeline=pipeline,
            client_id=client_id,
            client_name=client_name,
            output_dir=output_dir,
        )
        if deck_path:
            logger.info("Universal deck built for %s: %s", pipeline, deck_path.name)
        else:
            logger.info("No chartable results for %s deck", pipeline)
    except Exception:
        logger.exception("Universal deck build failed for %s", pipeline)


def _detect_pipelines(input_files: dict[str, Path]) -> list[str]:
    """Auto-detect which pipelines to run based on available input files."""
    pipelines = []
    if "oddd" in input_files:
        pipelines.append("ars")
    if "tran" in input_files or ("txn_dir" in input_files and "odd" in input_files):
        pipelines.append("txn")
    if "ics" in input_files:
        pipelines.append("ics")
    return pipelines
