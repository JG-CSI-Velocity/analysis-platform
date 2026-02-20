"""Module registry -- @register decorator, execution ordering, discovery."""

from __future__ import annotations

import importlib

from loguru import logger

from ars_analysis.analytics.base import AnalysisModule
from ars_analysis.exceptions import ConfigError

_REGISTRY: dict[str, type[AnalysisModule]] = {}

# Explicit execution order -- deterministic, no import side effects.
# Each entry maps to a subpackage under ars.analytics.
MODULE_ORDER: list[str] = [
    "overview.stat_codes",
    "overview.product_codes",
    "overview.eligibility",
    "dctr.penetration",
    "dctr.trends",
    "dctr.branches",
    "dctr.funnel",
    "dctr.overlays",
    "rege.status",
    "rege.branches",
    "rege.dimensions",
    "attrition.rates",
    "attrition.dimensions",
    "attrition.impact",
    "value.analysis",
    "mailer.insights",
    "mailer.response",
    "mailer.impact",
    "insights.synthesis",
    "insights.conclusions",
]


def register(cls: type[AnalysisModule]) -> type[AnalysisModule]:
    """Class decorator to register an analytics module."""
    _REGISTRY[cls.module_id] = cls
    logger.debug("Registered analytics module: {id}", id=cls.module_id)
    return cls


def get_module(module_id: str) -> type[AnalysisModule]:
    """Look up a module by ID. Raises ConfigError (not KeyError) if missing."""
    try:
        return _REGISTRY[module_id]
    except KeyError:
        raise ConfigError(
            f"Unknown analytics module: {module_id!r}",
            detail={"available": list(_REGISTRY.keys())},
        ) from None


def ordered_modules() -> list[type[AnalysisModule]]:
    """Return registered modules in execution order. Warns on missing."""
    modules: list[type[AnalysisModule]] = []
    for mid in MODULE_ORDER:
        if mid not in _REGISTRY:
            logger.warning("Module {id} in MODULE_ORDER but not registered", id=mid)
            continue
        modules.append(_REGISTRY[mid])
    return modules


def load_all_modules() -> None:
    """Import all analytics subpackages to trigger @register decorators."""
    # Pre-import heavy shared libs so individual modules load fast
    import concurrent.futures
    for lib in ("pandas", "matplotlib", "matplotlib.pyplot", "numpy", "openpyxl"):
        try:
            importlib.import_module(lib)
        except ImportError:
            pass

    errors: list[str] = []
    lock = __import__("threading").Lock()

    def _load(module_id: str) -> None:
        try:
            importlib.import_module(f"ars_analysis.analytics.{module_id}")
        except Exception as exc:
            logger.error("Failed to load module {id}: {err}", id=module_id, err=exc)
            with lock:
                errors.append(module_id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        pool.map(_load, MODULE_ORDER)

    if errors:
        raise ConfigError(
            f"Failed to load {len(errors)} analytics module(s)",
            detail={"failed_modules": errors},
        )


def clear_registry() -> None:
    """Clear all registered modules. Used in tests."""
    _REGISTRY.clear()
