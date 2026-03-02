"""ARS v2 pipeline runner -- bridges shared PipelineContext to ARS internals.

This module is the only coupling point between the unified platform and the
ARS v2 modular pipeline. It converts shared types at the boundary so the
100+ ARS source files don't need to know about the shared package.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from shared.context import PipelineContext as SharedContext
from shared.types import AnalysisResult as SharedResult

logger = logging.getLogger(__name__)


def _load_client_config(raw_config: dict) -> dict:
    """Resolve client config: load from JSON file if config_path is present.

    Falls back to ics_toolkit.client_registry resolution if no explicit path.
    """
    config_path = raw_config.get("config_path")

    # Fallback: resolve config path independently if none provided
    if not config_path:
        config_path = _resolve_config_fallback()

    if not config_path:
        logger.warning("No config file found -- using inline config (may be empty)")
        return raw_config

    path = Path(config_path)
    if not path.exists():
        logger.warning("Config file not found: %s, using inline config", path)
        return raw_config

    logger.info("Loading client config from: %s", path)
    all_clients = json.loads(path.read_text())
    client_id = raw_config.get("client_id", "")

    if client_id and client_id in all_clients:
        logger.info(
            "Found config for client %s (%d fields)", client_id, len(all_clients[client_id])
        )
        return all_clients[client_id]

    # If only one client in config, use it
    if len(all_clients) == 1:
        return next(iter(all_clients.values()))

    logger.warning(
        "Client %s not found in config file (%d clients available)", client_id, len(all_clients)
    )
    return raw_config


def _resolve_template_path() -> Path | None:
    """Find the PPTX template on the M: drive or known locations."""
    import platform as _platform

    candidates = (
        [
            Path(r"M:\ARS\Presentations\2025-CSI-PPT-Template.pptx"),
            Path(r"M:\ARS\Presentations\Template12.25.pptx"),
            Path(r"M:\ARS\Presentations\Template 12.25.pptx"),
        ]
        if _platform.system() == "Windows"
        else [
            Path("/Volumes/M/ARS/Presentations/2025-CSI-PPT-Template.pptx"),
            Path("/Volumes/M/ARS/Presentations/Template12.25.pptx"),
            Path("/Volumes/M/ARS/Presentations/Template 12.25.pptx"),
        ]
    )
    for p in candidates:
        if p.exists():
            logger.info("Found PPTX template: %s", p)
            return p
    return None


def _resolve_config_fallback() -> str | None:
    """Try to find clients_config.json via client_registry or known paths."""
    try:
        from ics_toolkit.client_registry import resolve_master_config_path

        resolved = resolve_master_config_path()
        if resolved:
            return str(resolved)
    except ImportError:
        pass

    # Direct fallback for known ARS locations
    import platform as _platform

    _fallback_paths = (
        [
            Path(r"M:\ARS\Config\clients_config.json"),
            Path(r"M:\ICS\Config\clients_config.json"),
            Path(r"M:\Config\clients_config.json"),
        ]
        if _platform.system() == "Windows"
        else [
            Path("/Volumes/M/ARS/Config/clients_config.json"),
            Path("/Volumes/M/ICS/Config/clients_config.json"),
            Path("/Volumes/M/Config/clients_config.json"),
        ]
    )
    for p in _fallback_paths:
        if p.exists():
            return str(p)

    return None


# Map UI module keys → ARS internal module ID prefixes.
# Overview modules always run (fast, foundational).
_UI_KEY_TO_PREFIXES: dict[str, list[str]] = {
    "ars_attrition": ["attrition."],
    "ars_reg_e": ["rege."],
    "ars_value": ["value."],
    "ars_mailer_impact": ["mailer.impact"],
    "ars_mailer_response": ["mailer.response"],
    "ars_mailer_insights": ["mailer.insights"],
    "ars_dctr": ["dctr."],
    "ars_insights": ["insights."],
}
_ALWAYS_RUN_PREFIXES = ["overview."]


def _expand_ui_keys(ui_keys: list[str]) -> list[str]:
    """Expand UI module keys to internal ARS module IDs.

    E.g. ["ars_attrition", "ars_dctr"] ->
         ["overview.stat_codes", "overview.product_codes", "overview.eligibility",
          "attrition.rates", "attrition.dimensions", "attrition.impact",
          "dctr.penetration", "dctr.trends", "dctr.branches", "dctr.funnel", "dctr.overlays"]
    """
    from ars_analysis.analytics.registry import ordered_modules

    # Collect prefixes from selected UI keys
    prefixes = list(_ALWAYS_RUN_PREFIXES)
    for key in ui_keys:
        if key in _UI_KEY_TO_PREFIXES:
            prefixes.extend(_UI_KEY_TO_PREFIXES[key])

    # Expand to actual registered module IDs
    all_mods = ordered_modules()
    expanded = []
    for mod_cls in all_mods:
        mid = mod_cls().module_id
        if any(mid.startswith(pfx) for pfx in prefixes):
            expanded.append(mid)

    return expanded


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

    # 0. Capture module_ids from caller BEFORE _load_client_config replaces them
    _ui_module_ids = (ctx.client_config or {}).get("module_ids")

    # 1. Build ARS ClientInfo from shared context
    ccfg = _load_client_config({**(ctx.client_config or {}), "client_id": ctx.client_id})
    month = ctx.analysis_date.strftime("%Y.%m") if ctx.analysis_date else ""

    _stat_codes = _ensure_list(ccfg.get("EligibleStatusCodes", []))
    _prod_codes = _ensure_list(ccfg.get("EligibleProductCodes", []))
    _rege_opt = _ensure_list(ccfg.get("RegEOptInCode", []))

    logger.info(
        "Client config for %s: stat_codes=%s, prod_codes=%s, rege_opt=%s, ic_rate=%s, dc=%s",
        ctx.client_id,
        _stat_codes,
        _prod_codes,
        _rege_opt,
        ccfg.get("ICRate", 0),
        ccfg.get("DCIndicator", "DC Indicator"),
    )

    client_info = ClientInfo(
        client_id=ctx.client_id,
        client_name=ctx.client_name or ctx.client_id,
        month=month,
        assigned_csm=ctx.csm,
        eligible_stat_codes=_stat_codes,
        eligible_prod_codes=_prod_codes,
        eligible_mailable=_ensure_list(ccfg.get("EligibleMailCode", [])),
        nsf_od_fee=_safe_float(ccfg.get("NSF_OD_Fee", 0)),
        ic_rate=_safe_float(ccfg.get("ICRate", 0)),
        dc_indicator=ccfg.get("DCIndicator", "DC Indicator"),
        reg_e_opt_in=_rege_opt,
        reg_e_column=ccfg.get("RegEColumn", ""),
        data_start_date=ccfg.get("DataStartDate"),
    )

    # 2. Build OutputPaths -- use output_dir directly (caller already scoped it)
    paths = OutputPaths.from_dir(ctx.output_dir)

    # 3. Build ARS PipelineContext
    ars_ctx = ARSContext(
        client=client_info,
        paths=paths,
        progress_callback=ctx.progress_callback,
    )

    # 3b. Resolve PPTX template (M: drive > config > embedded fallback)
    _tpl = ccfg.get("TemplatePath")
    if _tpl and Path(_tpl).exists():
        tpl_path = Path(_tpl)
    else:
        tpl_path = _resolve_template_path()
    # Build settings namespace with template + branch mapping
    _branch_map = ccfg.get("BranchMapping") or ccfg.get("branch_mapping")
    ars_ctx.settings = SimpleNamespace(
        paths=SimpleNamespace(template_path=tpl_path)
        if tpl_path
        else SimpleNamespace(template_path=None),
        branch_mapping=_branch_map if isinstance(_branch_map, dict) else None,
    )
    if tpl_path:
        logger.info("Using PPTX template: %s", tpl_path)
    if _branch_map:
        logger.info("Branch mapping: %d entries", len(_branch_map))

    # 4. Determine input file
    oddd_path = ctx.input_files.get("oddd")
    if not oddd_path:
        raise FileNotFoundError("No 'oddd' input file in PipelineContext")

    # 5. Build and run pipeline steps
    #    _ui_module_ids comes from the Streamlit UI (e.g. ["ars_attrition", "ars_dctr"])
    #    and must be expanded to internal ARS module IDs (e.g. ["attrition.rates", ...])
    module_ids = _expand_ui_keys(_ui_module_ids) if _ui_module_ids else None

    if module_ids:
        logger.info("Selected modules: %s -> %s", _ui_module_ids, module_ids)
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


def _ensure_list(value: object) -> list[str]:
    """Wrap a scalar string as a single-element list; pass through lists."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert a config value to float, returning default for empty/invalid."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
