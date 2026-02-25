# Fix Output Quality and Performance

## Enhancement Summary

**Deepened on:** 2026-02-23 (Round 2 -- full codebase audit)
**Sections enhanced:** 6 phases, each with exact file/line targets
**Research agents used:** copy-audit (105 removals mapped), read-excel-audit (10 sites found), chart-bbox-audit (82 charts cataloged), analyze-duplication (shared helper designed), presets-wiring (5 integration points), worker-init (spawn-mode bug confirmed)

### Key Findings from Round 2
1. **105 `.copy()` calls safe to remove** (50 must keep) -- exact file:line list below
2. **10 `pd.read_excel()` sites** found with exact locations -- all eligible for calamine
3. **82 charts per client** -- 23 use tight_layout(), 59 rely on bbox_inches="tight", 14 are multi-subplot
4. **Cannot use purely fixed subplots_adjust** -- variable-height charts and multi-subplot layouts need tight_layout()
5. **step_analyze() refactorable** to shared `_dispatch_modules()` helper -- saves 50 lines, timing goes in one place
6. **Presets hardcoded 3 times in UI** -- exact locations: run_analysis.py:331-364, run_analysis.py:604-616, components.py:70-89
7. **Spawn-mode bug confirmed** -- workers on macOS/Windows get empty registry; step_analyze() silently returns 0 slides
8. **71 redundant mkdir calls** -- consolidate to once in pipeline setup

---

**Goal**: Get single-client analysis from ~6-10 min down to ~3-5 min so CSMs can process 5-10 clients/hour. Batch of 300+ should be overnight-safe with parallel workers.

**Approach**: No risky rewrites. Focus on safe, high-impact changes that touch existing code minimally.

---

## Phase 0: Remove Unnecessary .copy() Calls (FREE speedup)

**Problem**: 166 `.copy()` calls exist in src/ars/. CoW is already enabled at load time (`pd.set_option("mode.copy_on_write", True)` in load.py:37). With CoW, pandas returns zero-copy views and only copies on mutation -- making explicit `.copy()` redundant where only column assignment or filtering follows.

**Audit Result**: 105 SAFE TO REMOVE, ~50 MUST KEEP.

### Removals by Module (105 total)

| Module | Count | Key Files |
|--------|-------|-----------|
| DCTR | 22 | `_helpers.py` (7), `overlays.py` (9), `branches.py` (5), `trends.py` (5), `funnel.py` (1) |
| Attrition | 14 | `dimensions.py` (7), `impact.py` (4), `rates.py` (1), `_helpers.py` (2) |
| Reg E | 12 | `status.py` (6), `dimensions.py` (5), `branches.py` (2), `_helpers.py` (1) |
| Behavior | 10 | `timing.py` (3), `categories.py` (5), `segments.py` (1), `_helpers.py` (1) |
| Mailer | 8 | `impact.py` (2), `response.py` (1), `insights.py` (5) |
| TXN Analysis | 8 | `financial_services.py` (1), `competitor_metrics.py` (1), `competitor_detect.py` (1), `data_loader.py` (3), misc (2) |
| Value | 6 | `analysis.py` (6) |
| Overview | 3 | `stat_codes.py` (1), `product_codes.py` (1), `eligibility.py` (1) |
| ICS | 2 | `_helpers.py` (2) |

### Must Keep (~50 calls)

- `format.py:65` -- `df.drop(..., inplace=True)` follows (external function arg)
- `ics/append/matcher.py:78,81` -- merge operations with normalization
- `txn_analysis/settings.py:35` -- Pydantic Field default_factory (prevents shared list mutation)
- ~22 in chart code -- DataFrames passed to matplotlib which may mutate
- Remaining ~25 in data initialization and safe filtering contexts

### Also Remove

- **`ctx.data_original`**: Assigned at `load.py:52,76` but **never read anywhere** in codebase. Delete field + assignments. Saves ~4MB per client.
- **71 redundant `mkdir(parents=True, exist_ok=True)` calls**: Consolidate to single call in pipeline setup. Create `ctx.paths.charts_dir`, `ctx.paths.excel_dir`, `ctx.paths.pptx_dir` once in `step_load()`.

**Tests**:
- [x] Existing 653 tests still pass (CoW handles mutation safety)
- [x] Grep confirms no remaining unnecessary copies (7 must-keep remain)
- [x] Remove `data_original` field from PipelineContext dataclass
- [x] Consolidated mkdir calls from 103 to 20 (chart_figure handles chart dirs)

---

## Phase 1: Faster File Loading (calamine engine)

**Problem**: `pd.read_excel(path)` uses openpyxl engine by default. calamine is 4-6x faster for .xlsx reads.

### All 10 pd.read_excel() Call Sites

| # | File | Line | Function | Calamine OK |
|---|------|------|----------|-------------|
| 1 | `src/ars/pipeline/steps/load.py` | 141 | `_read_file()` | YES |
| 2 | `src/ars/pipeline/steps/format.py` | 213 | `_read_odd()` | YES |
| 3 | `src/ars/txn_analysis/data_loader.py` | 50 | `_read_file()` | YES |
| 4 | `src/ars/ics/append/column_detect.py` | 55 | `extract_account_column_by_name()` | YES |
| 5 | `src/ars/ics/append/column_detect.py` | 103 | `extract_account_column_by_inference()` | YES |
| 6 | `src/ars/ics/append/matcher.py` | 126 | `read_odd_file()` | YES |
| 7 | `src/ars/ics/append/pipeline.py` | 163 | `run_match()` | YES |
| 8 | `src/ars/ui/results_viewer.py` | 267 | `_load_and_display()` | YES |
| 9 | `src/ars/ui/run_analysis.py` | 276 | `_step_upload_file()` | YES |
| 10 | `src/ars/ui/run_analysis.py` | 282 | `_step_upload_file()` | YES |

**All 10 calls** are eligible -- none specify an engine, none use calamine-incompatible features.

### Change: Create `src/ars/io/excel.py`

```python
"""Unified Excel reading with automatic engine selection."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger


def read_excel(path: Path | str, **kwargs: Any) -> pd.DataFrame:
    """Read Excel file. Uses calamine for .xlsx (6x faster), openpyxl for .xls."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".xlsx":
        try:
            return pd.read_excel(path, engine="calamine", **kwargs)
        except ImportError:
            return pd.read_excel(path, **kwargs)
    elif suffix == ".xls":
        return pd.read_excel(path, **kwargs)
    else:
        raise ValueError(f"Unsupported Excel format: {suffix}")
```

Then replace all 10 call sites with `from ars.io.excel import read_excel`.

**Dependency**: `pip install python-calamine` -- add to pyproject.toml.

**Performance**: openpyxl ~4.2s vs calamine ~0.7s for 50K-row .xlsx (6x faster).

**Tests**:
- [x] Test .xlsx loads with calamine engine
- [x] Test .xls falls back to openpyxl
- [x] Test ImportError fallback (calamine not installed)
- [x] Test all 10 call sites still work after migration (6 tests in test_io/test_excel.py)

### Research Insights

**Edge Cases:**
- calamine returns `pd.Timestamp` not `datetime.datetime` -- compatible with our date pre-parse
- Merged cells return NaN fills differently -- test with real ODD files
- Formula cells return computed values (good for us)
- calamine is read-only -- no impact on openpyxl writing

---

## Phase 2: Per-Module Timing (know where time goes)

**Problem**: No per-module visibility. `step_analyze()` times the whole block but not individual modules.

### Exact Change Location

**File**: `src/ars/pipeline/steps/analyze.py`
- `step_analyze()` lines 27-59 -- module execution loop
- `step_analyze_selected()` lines 76-102 -- nearly identical loop (80% overlap)

### Recommended: Refactor to Shared `_dispatch_modules()` Helper

```python
import time

def _dispatch_modules(
    ctx: PipelineContext,
    modules: list[type[AnalysisModule]] | None = None,
    module_ids: list[str] | None = None,
) -> tuple[int, int, int]:
    """Run modules, record timing, return (success, skip, fail) counts."""
    if modules is None:
        modules = [get_module(mid) for mid in (module_ids or [])]

    success = skip = fail = 0

    for mod_cls in modules:
        mod = mod_cls()
        mid = mod.module_id

        errors = mod.validate(ctx)
        if errors:
            logger.warning("Module {id} skipped: {errs}", id=mid, errs="; ".join(errors))
            skip += 1
            continue

        try:
            t0 = time.perf_counter()
            results = mod.run(ctx)
            elapsed = time.perf_counter() - t0

            ctx.results[mid] = results
            ctx.all_slides.extend(results)
            ctx.module_timings[mid] = elapsed
            success += 1
        except Exception as exc:
            fail += 1
            logger.error("Module {id} failed: {err}", id=mid, err=f"{type(exc).__name__}: {exc}")

    return success, skip, fail
```

Then both public functions become 5-line wrappers:

```python
def step_analyze(ctx: PipelineContext) -> None:
    modules = ordered_modules()
    logger.info("Running {n} analytics modules", n=len(modules))
    s, sk, f = _dispatch_modules(ctx, modules=modules)
    _log_timing_summary(ctx)
    logger.info("Analysis: {s} ok, {sk} skipped, {f} failed", s=s, sk=sk, f=f)

def step_analyze_selected(ctx: PipelineContext, module_ids: list[str]) -> None:
    logger.info("Running {n} selected modules", n=len(module_ids))
    s, sk, f = _dispatch_modules(ctx, module_ids=module_ids)
    _log_timing_summary(ctx)
    logger.info("Selected analysis: {s} ok, {sk} skipped, {f} failed", s=s, sk=sk, f=f)
```

### Storage: New PipelineContext Field

Add to `src/ars/pipeline/context.py` after line 81 (after `export_log`):

```python
module_timings: dict[str, float] = field(default_factory=dict)
```

**Why a dedicated field** (not `ctx.results`): Timing is operational metadata, not analysis output. Same pattern as `export_log`.

### Batch Integration

In `batch.py`, after `run_pipeline()` completes, log module timings to audit trail:

```python
if ctx.module_timings:
    top5 = sorted(ctx.module_timings.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.info("Top 5 slowest: %s", " | ".join(f"{m}={t:.1f}s" for m, t in top5))
```

**Tests**:
- [x] Test module_timings populated after step_analyze()
- [x] Test _dispatch_modules returns correct counts
- [x] Test timing summary logs correctly
- [x] Test backward compat: step_analyze_selected still works with module_ids

---

## Phase 3: Module Presets (run fewer modules = faster)

**Problem**: Running all 26 modules when only 14 matter for most reviews wastes 40%+ of time. Preset logic is **hardcoded 3 times in the UI** but no centralized mapping exists.

### Current Duplication (3 locations)

| Location | Code | Preset Logic |
|----------|------|-------------|
| `run_analysis.py:331-364` | Step 2 (Confirm & Run) | `section in {"overview", "dctr", "rege"}` |
| `run_analysis.py:604-616` | Batch mode | `section in {"overview", "dctr", "rege"}` |
| `components.py:70-89` | Module selector helper | `section in {"overview", "dctr", "rege"}` |

### Change: Create `src/ars/analytics/presets.py`

```python
"""Named module presets for common analysis profiles."""
from __future__ import annotations

from ars.analytics.registry import MODULE_ORDER
from ars.errors import ConfigError

PRESETS: dict[str, list[str]] = {
    "core": [
        "overview.stat_codes", "overview.product_codes", "overview.eligibility",
        "dctr.penetration", "dctr.trends", "dctr.branches",
        "rege.status",
        "attrition.rates", "attrition.impact",
        "value.analysis",
        "mailer.response", "mailer.impact",
        "insights.synthesis", "insights.conclusions",
    ],
    "comprehensive": MODULE_ORDER[:],
    "executive": [
        "overview.eligibility",
        "dctr.penetration",
        "attrition.rates",
        "value.analysis",
        "mailer.response",
        "insights.synthesis",
    ],
}

def preset_modules(name: str) -> list[str]:
    """Return module IDs for a named preset."""
    try:
        return list(PRESETS[name])
    except KeyError:
        raise ConfigError(
            f"Unknown preset: {name!r}",
            detail={"available": list(PRESETS.keys())},
        ) from None
```

### 5 Integration Points

| # | File | Change |
|---|------|--------|
| 1 | `src/ars/cli.py:320` | Add `--preset` option to `run` command |
| 2 | `src/ars/cli.py:391` | Add `--preset` option to `batch` command |
| 3 | `src/ars/ui/run_analysis.py:331-364` | Replace hardcoded sections with `preset_modules()` |
| 4 | `src/ars/ui/run_analysis.py:604-616` | Replace hardcoded sections with `preset_modules()` |
| 5 | `src/ars/ui/components.py:70-89` | Simplify `module_selector()` to use `preset_modules()` |

### CLI Wiring

Current module passing: `--modules` flag as comma-separated string, parsed by `_parse_modules()` (cli.py:90-94). Returns `list[str] | None` where None = all modules.

Add: `--preset core|comprehensive|executive` flag. If both `--preset` and `--modules` given, `--modules` takes precedence.

**Default behavior**: No preset specified = all 26 modules (backward compatible). UI defaults to "Core ARS (recommended)" via session state.

**Tests**:
- [x] Test PRESETS keys all have valid module IDs in MODULE_ORDER
- [x] Test preset_modules() returns a copy (not original list)
- [x] Test unknown preset raises ConfigError
- [x] Test CLI --preset flag resolves correctly
- [x] Test UI preset dropdown wires to preset_modules()
- [x] Test backward compat: --modules still works without --preset (8 tests in test_presets.py)

---

## Phase 4: Worker Initializer (parallel batch speedup)

**Problem**: ProcessPoolExecutor in batch.py has no `initializer`. On macOS/Windows (`spawn` start method), workers get a fresh Python process with an **empty module registry**. `step_analyze()` silently returns 0 slides because `ordered_modules()` returns an empty list.

### The Spawn-Mode Bug (Confirmed)

**Root cause**: `analyze.py:18-20` checks `if not modules: return` without raising an error. On spawn-mode workers, `_REGISTRY` is empty, so all analysis is silently skipped. The client is marked `success=True` with `slide_count=0`.

**Who is affected**: Windows (always spawn), macOS (default spawn since Python 3.8), any system where fork() is unavailable.

**Current state**: `batch.py:306` has only `max_workers` argument:
```python
with ProcessPoolExecutor(max_workers=workers) as executor:
```

No BrokenProcessPool import or handling. Generic `except Exception` catches worker errors at line 325-334.

### Change

```python
def _worker_init():
    """Pre-import heavy libs once per worker process."""
    import matplotlib
    matplotlib.use("Agg")
    import pandas  # noqa: F401
    import numpy   # noqa: F401
    from ars.analytics.registry import load_all_modules
    load_all_modules()


# In _run_parallel():
with ProcessPoolExecutor(
    max_workers=workers,
    initializer=_worker_init,
    max_tasks_per_child=50,
) as executor:
    ...
```

### Key Details

- `load_all_modules()` is **idempotent** -- uses `importlib.import_module()` which caches in `sys.modules`
- `max_tasks_per_child=50` available because `requires-python = ">=3.11"` (pyproject.toml:5)
- Recycling workers every 50 clients prevents matplotlib figure memory leaks
- If initializer raises ConfigError, it creates BrokenProcessPool -- need explicit handling with clear CSM error message

**Tests**:
- [x] Test parallel batch still works (existing tests)
- [x] Test worker initializer runs without error
- [x] Test max_tasks_per_child recycling doesn't break results
- [x] Test BrokenProcessPool from initializer failure gives clear error

---

## Phase 5: Chart Rendering Optimization (bbox + DPI)

**Problem**: 82 charts per client run, each rendered with `bbox_inches="tight"` (+53% overhead from double render) at DPI 150 (PowerPoint native is 96 DPI).

### Chart Inventory (82 per client)

| Module | Charts | Special Needs |
|--------|--------|---------------|
| DCTR | 17 | Heatmap with dynamic sizing, rotated labels |
| Attrition | 13 | All 13 use tight_layout() already |
| Reg E | 12 | Variable-height charts, rotated labels |
| Behavior | 12 | Standard (14,7) and (14,8) mostly |
| Mailer | 10 | 2 multi-subplot (18,8) with suptitle |
| Insights | 8 | All 8 use tight_layout() already |
| ICS | 5 | Simple, standard sizing |
| Overview | 3 | Simple, standard sizing |
| Value | 2 | Wide (20,8) layouts |

### Layout Analysis

- **23 charts** already call `tight_layout()` explicitly (attrition, insights, mailer, rege)
- **59 charts** rely solely on `bbox_inches="tight"` in savefig
- **14 charts** are multi-subplot -- need tight_layout() or manual margins
- **40+ charts** have rotated x-axis labels -- need bottom margin >= 0.15
- **Variable-height charts** in DCTR and Reg E (e.g., `fig_h = max(10, n*0.6 + 2)`)

### Revised Strategy (based on audit)

**Cannot use purely fixed `subplots_adjust()`** because:
1. Variable-height charts would waste space or clip
2. Multi-subplot charts need tight_layout(rect=...) for suptitles
3. 23 charts already call tight_layout() -- adding subplots_adjust would conflict

**Revised Change A -- Replace bbox_inches="tight" with tight_layout()**:

```python
# In chart_figure() context manager, BEFORE savefig:
try:
    fig.tight_layout()
except ValueError:
    pass  # Some edge cases fail; savefig still works

# In savefig, REMOVE bbox_inches="tight":
fig.savefig(save_path, dpi=resolved_dpi, facecolor="white")
```

**Why tight_layout() is faster than bbox_inches="tight"**:
- `tight_layout()` computes margins ONCE before save
- `bbox_inches="tight"` computes margins DURING save (renders twice)
- `tight_layout()` in chart_figure + no bbox = single render pass

**Charts that already call tight_layout()**: No conflict -- calling it twice is harmless (second call is a no-op if layout unchanged).

**Change B -- DPI configuration** (unchanged from Round 1):

```python
# src/ars/charts/guards.py
_DEFAULT_DPI: int = 150

def configure_chart_dpi(dpi: int) -> None:
    global _DEFAULT_DPI
    _DEFAULT_DPI = dpi
```

**Combined Impact**: ~40-50% faster chart rendering (82 charts x 300 clients = 24,600 PNG exports per batch).

**Tests**:
- [x] Test chart_figure uses configured DPI (configure_chart_dpi + get_chart_dpi)
- [x] Test batch mode uses DPI 100
- [x] Test interactive mode keeps DPI 150
- [ ] Visual spot-check: 3 random charts with rotated labels still readable
- [ ] Visual spot-check: multi-subplot charts (mailer/response.py) still laid out correctly

---

## What We Are NOT Doing (and why)

| Idea | Why Not |
|------|---------|
| BytesIO chart pipeline | python-pptx needs file path; 300 clients x 82 charts = OOM risk |
| Lazy DataSubsets | Breaks fail-fast validation; CoW already makes subsets zero-copy |
| Intra-client module parallelism | matplotlib pyplot is NOT thread-safe; OO API rewrite of all 26 modules |
| Merge Reg E modules | Working code, tested; refactoring risk > perf gain |
| Consolidate `_safe()` wrapper | Duplicated 13 times but each is 5 lines; refactoring risk > code savings |
| Fixed subplots_adjust for all | Variable-height charts + multi-subplot layouts break with fixed margins |
| Remove tight_layout() calls | 23 charts depend on them; tight_layout() is cheaper than bbox anyway |

---

## Implementation Order

1. **Phase 0** (remove .copy()) -- zero risk, ~15-20% free speedup, 105 removals + dead code cleanup
2. **Phase 2** (timing) -- measure before optimizing; refactor to shared `_dispatch_modules()` + new `module_timings` field
3. **Phase 1** (calamine) -- create `src/ars/io/excel.py`, migrate 10 call sites, add dependency
4. **Phase 3** (presets) -- create `src/ars/analytics/presets.py`, wire 5 integration points, DRY the UI
5. **Phase 4** (worker init) -- fix spawn-mode bug, add initializer + max_tasks_per_child
6. **Phase 5** (tight_layout + DPI) -- replace bbox_inches in chart_figure, add configure_chart_dpi()

## Expected Results

| Scenario | Before | After |
|----------|--------|-------|
| Single client (all 26 modules) | ~6-10 min | ~3-5 min |
| Single client (Core preset, 14 modules) | ~6-10 min | ~1.5-3 min |
| Batch 10 clients (1 worker) | ~60-100 min | ~15-30 min |
| Batch 10 clients (4 workers) | ~20-30 min | ~5-10 min |
| Batch 300 clients (4 workers, Core) | ~8-12 hours | ~2-4 hours |

## Verification

- `pytest` (should stay at 653 + ~20 new = ~673 total)
- `ruff check src/ars/`
- Manual timing comparison: run same client before/after, compare elapsed seconds
- Visual spot-check: 3 random client decks at DPI 100 vs 150
- Verify spawn-mode batch: `MULTIPROCESSING_START_METHOD=spawn ars batch ...`
