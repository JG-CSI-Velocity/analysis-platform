"""ARS v2 pipeline runner -- bridges shared PipelineContext to ARS internals.

This module is the only coupling point between the unified platform and the
ARS v2 modular pipeline. It converts shared types at the boundary so the
100+ ARS source files don't need to know about the shared package.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from shared.context import PipelineContext as SharedContext
from shared.types import AnalysisResult as SharedResult

logger = logging.getLogger(__name__)


def _load_client_config(raw_config: dict) -> dict:
    """Resolve client config: load from JSON file if config_path is present."""
    config_path = raw_config.get("config_path")
    if not config_path:
        return raw_config

    path = Path(config_path)
    if not path.exists():
        logger.warning("Config file not found: %s, using inline config", path)
        return raw_config

    all_clients = json.loads(path.read_text())
    client_id = raw_config.get("client_id", "")

    if client_id and client_id in all_clients:
        return all_clients[client_id]

    # If only one client in config, use it
    if len(all_clients) == 1:
        return next(iter(all_clients.values()))

    logger.warning("Client %s not found in config file, using inline config", client_id)
    return raw_config


def run_ars(ctx: SharedContext) -> dict[str, SharedResult]:
    """Run the full ARS v2 pipeline via the shared PipelineContext bridge.

    Converts shared context -> ARS internal context, runs load/subsets/analyze/generate,
    then converts ARS AnalysisResult objects back to shared AnalysisResult objects.
    """
    from ars_analysis.analytics.registry import load_all_modules
    from ars_analysis.pipeline.context import (
        ClientInfo,
        OutputPaths,
    )
    from ars_analysis.pipeline.context import (
        PipelineContext as ARSContext,
    )
    from ars_analysis.pipeline.runner import PipelineStep, run_pipeline
    from ars_analysis.pipeline.steps.analyze import step_analyze, step_analyze_selected
    from ars_analysis.pipeline.steps.generate import step_generate
    from ars_analysis.pipeline.steps.load import step_load_file
    from ars_analysis.pipeline.steps.subsets import step_subsets

    # Load all analytics modules (triggers @register decorators)
    load_all_modules()

    # 1. Build ARS ClientInfo from shared context
    ccfg = _load_client_config({**(ctx.client_config or {}), "client_id": ctx.client_id})
    month = ctx.analysis_date.strftime("%Y.%m") if ctx.analysis_date else ""

    client_info = ClientInfo(
        client_id=ctx.client_id,
        client_name=ctx.client_name or ctx.client_id,
        month=month,
        assigned_csm=ctx.csm,
        eligible_stat_codes=ccfg.get("EligibleStatusCodes", []),
        eligible_prod_codes=ccfg.get("EligibleProductCodes", []),
        eligible_mailable=ccfg.get("EligibleMailable", []),
        nsf_od_fee=_safe_float(ccfg.get("NSF_OD_Fee", 0)),
        ic_rate=_safe_float(ccfg.get("ICRate", 0)),
        dc_indicator=ccfg.get("DCIndicator", "DC Indicator"),
        reg_e_opt_in=ccfg.get("RegEOptInCode", []),
        reg_e_column=ccfg.get("RegEColumn", ""),
    )

    # 2. Build OutputPaths
    paths = OutputPaths.from_base(ctx.output_dir, ctx.client_id, month)

    # 3. Build ARS PipelineContext
    ars_ctx = ARSContext(client=client_info, paths=paths)

    # 4. Determine input file
    oddd_path = ctx.input_files.get("oddd")
    if not oddd_path:
        raise FileNotFoundError("No 'oddd' input file in PipelineContext")

    # 5. Build and run pipeline steps
    module_ids = ccfg.get("module_ids")

    if module_ids:
        analyze_step = PipelineStep(
            "run_analyses",
            lambda c, ids=module_ids: step_analyze_selected(c, ids),
        )
    else:
        analyze_step = PipelineStep("run_analyses", step_analyze)

    steps = [
        PipelineStep("load_data", lambda c, fp=Path(oddd_path): step_load_file(c, fp)),
        PipelineStep("create_subsets", step_subsets),
        analyze_step,
        PipelineStep("generate_output", step_generate),
    ]

    if ctx.progress_callback:
        ctx.progress_callback("Starting ARS v2 pipeline...")

    run_pipeline(ars_ctx, steps)

    if ctx.progress_callback:
        ctx.progress_callback(f"ARS complete: {len(ars_ctx.all_slides)} slides generated")

    # 6. Convert ARS AnalysisResult[] -> shared AnalysisResult{}
    results = _convert_results(ars_ctx)

    # 7. Copy back to shared context
    ctx.results.update(results)

    return results


def _convert_results(ars_ctx: Any) -> dict[str, SharedResult]:
    """Convert ARS AnalysisResult objects to shared AnalysisResult objects.

    ctx.results contains both module output lists (list[AnalysisResult]) and
    inter-module data (strings, DataFrames, tuples).  Only process the former.
    """
    from ars_analysis.analytics.base import AnalysisResult as ARSResult

    results: dict[str, SharedResult] = {}

    for module_id, ars_results in ars_ctx.results.items():
        if not isinstance(ars_results, list):
            continue
        for ar in ars_results:
            if not isinstance(ar, ARSResult):
                continue
            data = {}
            if ar.excel_data:
                data.update(ar.excel_data)

            charts: list[Path] = []
            if ar.chart_path and ar.chart_path.exists():
                charts.append(ar.chart_path)

            meta: dict[str, Any] = {
                "slide_id": ar.slide_id,
                "module_id": module_id,
                "success": ar.success,
            }
            if ar.error:
                meta["error"] = ar.error

            results[ar.slide_id] = SharedResult(
                name=ar.title,
                data=data,
                charts=charts,
                summary=ar.notes or ar.title,
                metadata=meta,
            )

    return results


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert a config value to float, returning default for empty/invalid."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
