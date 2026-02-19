"""Step: Dispatch analysis to registered modules via the registry."""

from __future__ import annotations

from loguru import logger

from ars_analysis.analytics.registry import get_module, ordered_modules
from ars_analysis.pipeline.context import PipelineContext


def step_analyze(ctx: PipelineContext) -> None:
    """Run all registered analytics modules in order.

    Each module is isolated: one failure does not block the next.
    Results are stored in ctx.results[module_id].
    """
    modules = ordered_modules()
    if not modules:
        logger.warning("No analytics modules registered -- skipping analysis step")
        return

    logger.info("Running {n} analytics modules", n=len(modules))
    success_count = 0
    skip_count = 0
    fail_count = 0

    for mod_cls in modules:
        mod = mod_cls()
        mid = mod.module_id

        # Validate prerequisites
        errors = mod.validate(ctx)
        if errors:
            logger.warning(
                "Module {id} skipped -- validation errors: {errs}",
                id=mid,
                errs="; ".join(errors),
            )
            skip_count += 1
            continue

        # Execute with isolation
        try:
            results = mod.run(ctx)
            ctx.results[mid] = results
            ctx.all_slides.extend(results)
            success_count += 1
            logger.info(
                "Module {id} produced {n} result(s)",
                id=mid,
                n=len(results),
            )
        except Exception as exc:
            fail_count += 1
            logger.error(
                "Module {id} failed: {err}",
                id=mid,
                err=f"{type(exc).__name__}: {exc}",
            )

    logger.info(
        "Analysis complete: {ok} succeeded, {skip} skipped, {fail} failed",
        ok=success_count,
        skip=skip_count,
        fail=fail_count,
    )


def step_analyze_selected(ctx: PipelineContext, module_ids: list[str]) -> None:
    """Run only the specified modules (used by CLI --modules flag)."""
    logger.info("Running {n} selected modules: {ids}", n=len(module_ids), ids=module_ids)
    success_count = 0
    skip_count = 0
    fail_count = 0

    for mid in module_ids:
        mod_cls = get_module(mid)
        mod = mod_cls()

        errors = mod.validate(ctx)
        if errors:
            logger.warning(
                "Module {id} skipped -- validation errors: {errs}",
                id=mid,
                errs="; ".join(errors),
            )
            skip_count += 1
            continue

        try:
            results = mod.run(ctx)
            ctx.results[mid] = results
            ctx.all_slides.extend(results)
            success_count += 1
            logger.info("Module {id} produced {n} result(s)", id=mid, n=len(results))
        except Exception as exc:
            fail_count += 1
            logger.error(
                "Module {id} failed: {err}",
                id=mid,
                err=f"{type(exc).__name__}: {exc}",
            )

    logger.info(
        "Selected analysis complete: {ok} succeeded, {skip} skipped, {fail} failed",
        ok=success_count,
        skip=skip_count,
        fail=fail_count,
    )
