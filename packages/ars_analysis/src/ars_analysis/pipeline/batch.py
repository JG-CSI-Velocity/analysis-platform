"""Batch processing -- run pipeline for multiple clients."""

from __future__ import annotations

import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from rich.console import Console

from ars_analysis.config import ARSSettings
from ars_analysis.logging_setup import get_username
from ars_analysis.pipeline.context import ClientInfo, OutputPaths, PipelineContext
from ars_analysis.pipeline.runner import PipelineStep, run_pipeline
from ars_analysis.pipeline.steps.analyze import step_analyze, step_analyze_selected
from ars_analysis.pipeline.steps.generate import step_archive, step_generate
from ars_analysis.pipeline.steps.load import step_load_file
from ars_analysis.pipeline.steps.scan import ScannedFile
from ars_analysis.pipeline.steps.subsets import step_subsets


def _safe_float(value: object, default: float = 0.0) -> float:
    """Convert a config value to float, returning default for empty/invalid."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


console = Console()


@dataclass
class BatchResult:
    """Outcome of processing one client in a batch."""

    client_id: str
    client_name: str
    success: bool
    elapsed: float
    slide_count: int
    error: str = ""


def _build_client_info(
    scanned: ScannedFile,
    settings: ARSSettings,
) -> ClientInfo:
    """Build ClientInfo from a scanned file + settings."""
    clients = getattr(settings, "clients", {}) or {}
    cfg = clients.get(scanned.client_id, {})

    return ClientInfo(
        client_id=scanned.client_id,
        client_name=cfg.get("ClientName", scanned.client_id),
        month=scanned.month,
        assigned_csm=scanned.csm_name,
        eligible_stat_codes=cfg.get("EligibleStatusCodes", []),
        eligible_prod_codes=cfg.get("EligibleProductCodes", []),
        nsf_od_fee=_safe_float(cfg.get("NSF_OD_Fee", 0)),
        ic_rate=_safe_float(cfg.get("ICRate", 0)),
    )


def _build_steps(
    file_path: Path,
    module_ids: list[str] | None = None,
) -> list[PipelineStep]:
    """Build the pipeline step list for one client."""
    if module_ids:
        analyze_step = PipelineStep(
            "run_analyses",
            lambda c, ids=module_ids: step_analyze_selected(c, ids),
        )
    else:
        analyze_step = PipelineStep("run_analyses", step_analyze)

    return [
        PipelineStep("load_data", lambda c, fp=file_path: step_load_file(c, fp)),
        PipelineStep("create_subsets", step_subsets),
        analyze_step,
        PipelineStep("generate_output", step_generate),
        PipelineStep("archive", step_archive, critical=False),
    ]


def _run_one_client(
    scanned: ScannedFile,
    settings: ARSSettings,
    module_ids: list[str] | None,
    output_base: Path | None,
    use_local_temp: bool,
) -> BatchResult:
    """Process a single client. Designed to be called from a worker process."""
    t0 = time.perf_counter()
    temp_dir = None

    try:
        client_info = _build_client_info(scanned, settings)
        final_base = output_base or scanned.file_path.parent

        # Local temp processing: copy input locally, process, copy results back
        if use_local_temp:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"ars_{scanned.client_id}_"))
            # Copy input file to temp
            local_input = temp_dir / scanned.file_path.name
            shutil.copy2(scanned.file_path, local_input)
            work_base = temp_dir
            work_file = local_input
        else:
            work_base = final_base
            work_file = scanned.file_path

        paths = OutputPaths.from_base(work_base, scanned.client_id, scanned.month)
        ctx = PipelineContext(client=client_info, paths=paths, settings=settings)

        steps = _build_steps(work_file, module_ids)
        step_results = run_pipeline(ctx, steps)

        success = all(r.success for r in step_results)
        elapsed = time.perf_counter() - t0

        # Copy results back from temp to final location
        if use_local_temp and temp_dir and success:
            _copy_results_back(paths, final_base, scanned.client_id, scanned.month)

        return BatchResult(
            client_id=scanned.client_id,
            client_name=client_info.client_name,
            success=success,
            elapsed=elapsed,
            slide_count=len(ctx.all_slides),
        )

    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return BatchResult(
            client_id=scanned.client_id,
            client_name=scanned.client_id,
            success=False,
            elapsed=elapsed,
            slide_count=0,
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        # Clean up temp directory
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _copy_results_back(
    temp_paths: OutputPaths,
    final_base: Path,
    client_id: str,
    month: str,
) -> None:
    """Copy output files from temp back to the real output location."""
    final_paths = OutputPaths.from_base(final_base, client_id, month)

    for src_dir, dst_dir in [
        (temp_paths.charts_dir, final_paths.charts_dir),
        (temp_paths.excel_dir, final_paths.excel_dir),
        (temp_paths.pptx_dir, final_paths.pptx_dir),
    ]:
        if src_dir.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)
            for src_file in src_dir.iterdir():
                if src_file.is_file():
                    shutil.copy2(src_file, dst_dir / src_file.name)


def run_batch(
    files: list[ScannedFile],
    settings: ARSSettings,
    module_ids: list[str] | None = None,
    output_base: Path | None = None,
    max_workers: int = 1,
    use_local_temp: bool = False,
) -> list[BatchResult]:
    """Process multiple clients, optionally in parallel.

    Parameters
    ----------
    files : list[ScannedFile]
        Ready files found by scan_ready_files().
    settings : ARSSettings
        Pipeline configuration.
    module_ids : list[str] or None
        Specific modules to run (None = all registered).
    output_base : Path or None
        Override output base directory.
    max_workers : int
        Number of parallel workers (1 = sequential, >1 = parallel).
    use_local_temp : bool
        Copy files to local temp before processing (faster on network drives).

    Returns
    -------
    list[BatchResult]
        One result per client processed.
    """
    username = get_username()
    logger.info("Batch start: {n} clients (workers={w})", n=len(files), w=max_workers)
    logger.log(
        "AUDIT",
        "user={user} | action=batch_start | clients={n} | workers={w}",
        user=username,
        n=len(files),
        w=max_workers,
    )

    if max_workers > 1 and len(files) > 1:
        batch_results = _run_parallel(
            files,
            settings,
            module_ids,
            output_base,
            max_workers,
            use_local_temp,
        )
    else:
        batch_results = _run_sequential(
            files,
            settings,
            module_ids,
            output_base,
            use_local_temp,
        )

    # Summary
    ok = sum(1 for r in batch_results if r.success)
    failed = len(batch_results) - ok
    total_time = sum(r.elapsed for r in batch_results)

    console.print()
    if failed:
        console.print(
            f"  [bold]Done:[/bold] {ok}/{len(batch_results)} succeeded, [red]{failed} failed[/red] ({total_time:.1f}s)"
        )
        for r in batch_results:
            if not r.success:
                console.print(f"    [red]x[/red] {r.client_id}: {r.error}")
    else:
        console.print(
            f"  [bold green]Done:[/bold green] {ok}/{len(batch_results)} succeeded ({total_time:.1f}s)"
        )
    console.print()

    logger.info(
        "Batch done: {ok}/{total} succeeded in {t:.1f}s",
        ok=ok,
        total=len(batch_results),
        t=total_time,
    )
    logger.log(
        "AUDIT",
        "user={user} | action=batch_done | ok={ok} | total={total} | elapsed={t:.1f}s",
        user=username,
        ok=ok,
        total=len(batch_results),
        t=total_time,
    )

    return batch_results


def _run_sequential(
    files: list[ScannedFile],
    settings: ARSSettings,
    module_ids: list[str] | None,
    output_base: Path | None,
    use_local_temp: bool,
) -> list[BatchResult]:
    """Process clients one at a time."""
    results = []
    console.print(f"\n  Processing {len(files)} client(s)...\n")
    for i, scanned in enumerate(files, 1):
        console.print(f"  [{i}/{len(files)}] {scanned.client_id} ({scanned.filename})...", end=" ")
        logger.info(
            "[{i}/{n}] Processing {cid} ({file})",
            i=i,
            n=len(files),
            cid=scanned.client_id,
            file=scanned.filename,
        )
        result = _run_one_client(scanned, settings, module_ids, output_base, use_local_temp)
        results.append(result)

        if result.success:
            console.print(
                f"[green]OK[/green] -- {result.slide_count} slides ({result.elapsed:.1f}s)"
            )
        else:
            console.print(f"[red]FAILED[/red] -- {result.error}")
        logger.info(
            "[{i}/{n}] {cid}: {status} -- {slides} slides in {t:.1f}s",
            i=i,
            n=len(files),
            cid=result.client_id,
            status="OK" if result.success else "FAILED",
            slides=result.slide_count,
            t=result.elapsed,
        )
    return results


def _run_parallel(
    files: list[ScannedFile],
    settings: ARSSettings,
    module_ids: list[str] | None,
    output_base: Path | None,
    max_workers: int,
    use_local_temp: bool,
) -> list[BatchResult]:
    """Process clients in parallel using ProcessPoolExecutor."""
    results: list[BatchResult] = []
    workers = min(max_workers, len(files))

    logger.info("Starting parallel processing with {w} workers", w=workers)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_client = {
            executor.submit(
                _run_one_client,
                scanned,
                settings,
                module_ids,
                output_base,
                use_local_temp,
            ): scanned.client_id
            for scanned in files
        }

        for future in as_completed(future_to_client):
            client_id = future_to_client[future]
            try:
                result = future.result()
                results.append(result)
                status = "OK" if result.success else "FAILED"
                logger.info(
                    "{cid}: {status} -- {slides} slides in {t:.1f}s",
                    cid=result.client_id,
                    status=status,
                    slides=result.slide_count,
                    t=result.elapsed,
                )
            except Exception as exc:
                results.append(
                    BatchResult(
                        client_id=client_id,
                        client_name=client_id,
                        success=False,
                        elapsed=0,
                        slide_count=0,
                        error=f"Worker error: {type(exc).__name__}: {exc}",
                    )
                )
                logger.error("{cid}: Worker error: {err}", cid=client_id, err=exc)

    return results
