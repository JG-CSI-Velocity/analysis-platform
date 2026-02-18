"""Pipeline orchestrator -- dispatches to ARS, Transaction, and ICS runners."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from shared.context import PipelineContext
from shared.types import AnalysisResult

logger = logging.getLogger(__name__)

PIPELINE_NAMES = ("ars", "txn", "txn_v4", "ics", "ics_append")


def run_pipeline(
    pipeline: str,
    *,
    input_files: dict[str, Path],
    output_dir: Path = Path("output"),
    client_id: str = "",
    client_name: str = "",
    client_config: dict | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, AnalysisResult]:
    """Run a named pipeline and return results.

    Parameters
    ----------
    pipeline : str
        One of 'ars', 'txn', 'txn_v4', 'ics', 'ics_append'.
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
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    if pipeline == "ars":
        from ars_analysis.runner import run_ars

        return run_ars(ctx)
    elif pipeline == "txn":
        from txn_analysis.runner import run_txn

        return run_txn(ctx)
    elif pipeline == "txn_v4":
        from txn_analysis.runner import run_txn_v4

        return run_txn_v4(ctx)
    elif pipeline == "ics":
        from ics_toolkit.runner import run_ics

        return run_ics(ctx)
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


def _detect_pipelines(input_files: dict[str, Path]) -> list[str]:
    """Auto-detect which pipelines to run based on available input files."""
    pipelines = []
    if "oddd" in input_files:
        pipelines.append("ars")
    if "tran" in input_files:
        pipelines.append("txn")
        if "odd" in input_files:
            pipelines.append("txn_v4")
    if "ics" in input_files:
        pipelines.append("ics")
    return pipelines
