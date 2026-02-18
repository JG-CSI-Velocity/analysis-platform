"""ARS pipeline runner — orchestrates all A1-A15 analyses.

Bridges the typed PipelineContext from the unified platform to the
dict-based ctx pattern used by the ported ARS analysis modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.context import PipelineContext
from shared.types import AnalysisResult


def run_ars(ctx: PipelineContext) -> dict[str, AnalysisResult]:
    """Run the full ARS pipeline and return results.

    Converts PipelineContext to the dict-based ctx expected by the
    ported pipeline module, runs all analyses, then extracts results
    back into AnalysisResult objects.
    """
    from ars_analysis.pipeline import run_pipeline

    # Build the raw ctx dict that pipeline.run_pipeline expects
    result_ctx = run_pipeline(
        file_path=str(ctx.input_files.get("oddd", "")),
        config_path=str(ctx.client_config.get("config_path", ""))
        if ctx.client_config.get("config_path")
        else None,
        base_paths=_build_base_paths(ctx),
        template_path=str(ctx.client_config.get("template_path", ""))
        if ctx.client_config.get("template_path")
        else None,
        progress_callback=ctx.progress_callback,
    )

    # Extract results from the raw ctx into typed AnalysisResult objects
    results = {}
    raw_results = result_ctx.get("results", {})
    for key, value in raw_results.items():
        if isinstance(value, dict):
            results[key] = AnalysisResult(
                name=key,
                data=_extract_dataframes(value),
                summary=str(value.get("insight", "")),
                metadata={k: v for k, v in value.items() if not _is_dataframe(v)},
            )
        else:
            results[key] = AnalysisResult(name=key, summary=str(value))

    # Copy slides and export log back to PipelineContext
    ctx.all_slides.extend(result_ctx.get("all_slides", []))
    ctx.results.update(results)

    return results


def run_ars_from_dict(ctx: dict[str, Any]) -> dict[str, Any]:
    """Run the ARS pipeline directly with a dict-based context.

    This is the simpler entry point when you already have a raw ctx dict
    (e.g., from the original pipeline workflow).
    """
    from ars_analysis.pipeline import run_pipeline

    file_path = ctx.get("file_path", "")
    config_path = ctx.get("config_path")
    progress_callback = ctx.get("_progress_callback")

    return run_pipeline(
        file_path=file_path,
        config_path=config_path,
        progress_callback=progress_callback,
    )


def _build_base_paths(ctx: PipelineContext) -> dict[str, Path] | None:
    """Build the base_paths dict from PipelineContext if configured."""
    if not ctx.output_dir:
        return None
    return {
        "presentations": ctx.output_dir,
        "archive": ctx.output_dir / "archive",
    }


def _extract_dataframes(d: dict) -> dict:
    """Extract DataFrame values from a dict."""
    import pandas as pd

    return {k: v for k, v in d.items() if isinstance(v, pd.DataFrame)}


def _is_dataframe(obj: object) -> bool:
    """Check if object is a pandas DataFrame without importing pandas."""
    return type(obj).__name__ == "DataFrame"
