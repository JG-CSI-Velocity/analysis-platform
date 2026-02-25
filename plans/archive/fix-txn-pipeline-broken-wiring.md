# Fix: TXN Pipeline Broken Wiring

**Date:** 2026-02-23
**Severity:** Critical -- TXN pipeline silently fails in multiple places
**Related issues:** #50 (PerformanceWarning), user-reported "barely works"

---

## Problem Statement

The TXN pipeline has 6 concrete bugs that cause silent failures, missing outputs, and no user visibility when things go wrong. ARS and ICS complete fine, but TXN breaks at multiple points in the execution chain.

Beyond TXN, a cross-platform review surfaced 6 additional data-integrity and correctness issues (P1-P3) affecting all pipelines.

---

## Bug 1: Excel Export Crashes on Pre-loaded Data (CRITICAL)

**File:** `packages/txn_analysis/src/txn_analysis/exports/excel_report.py:90`

```python
("Source File:", result.settings.data_file.name),  # AttributeError when None
```

When multiple TXN files are loaded in memory (pre-loaded mode), `settings.data_file` is `None`. This line crashes with `AttributeError: 'NoneType' object has no attribute 'name'`. The crash is caught by `pipeline.py:222` which logs it but returns an empty list -- user sees "Export complete" but no Excel file is created.

### Fix

```python
# excel_report.py:90
("Source File:", result.settings.data_file.name if result.settings.data_file else "(multiple files)"),
```

- [ ] Fix `excel_report.py:90` -- handle None data_file
- [ ] Also check `transaction_dir` as fallback label

---

## Bug 2: Export Failures Shown as Success (HIGH)

**File:** `packages/txn_analysis/src/txn_analysis/runner.py:69-74`

```python
export_outputs(result)  # Can silently fail (Bug 1)
if ctx.progress_callback:
    ctx.progress_callback(f"[3/{_total}] Export complete -- {n} analyses")  # Fires anyway
```

The "Export complete" callback fires even when `export_outputs()` failed internally. User sees success message, no Excel file.

### Fix

```python
generated = export_outputs(result)
if ctx.progress_callback:
    if generated:
        ctx.progress_callback(f"[3/{_total}] Exported {len(generated)} files")
    else:
        ctx.progress_callback(f"[3/{_total}] Export produced no files")
```

- [ ] Capture `export_outputs()` return value in `runner.py`
- [ ] Report actual file count instead of hardcoded "complete"

---

## Bug 3: Chart Failures Are Invisible (HIGH)

**File:** `packages/txn_analysis/src/txn_analysis/pipeline.py:143-144`

```python
except Exception as e:
    logger.error("Chart generation failed: %s", e, exc_info=True)
    # Returns empty charts dict -- no error propagated
```

If chart generation fails (template issue, missing column, etc.), the pipeline continues with zero charts. Excel report has no charts. User never knows.

### Fix

- [ ] Add chart failure count to progress callback after chart step
- [ ] Include chart error summary in PipelineResult or log visible to UI

---

## Bug 4: TXN Results Lose Chart Paths in Conversion (HIGH)

**File:** `packages/txn_analysis/src/txn_analysis/runner.py:94-111`

```python
results[ar.name] = SharedResult(
    name=ar.name,
    data={"main": ar.df},
    summary=ar.title,
    metadata=meta,
    # NO charts= field -- chart paths are lost
)
```

Compare to ARS runner which includes `charts=charts`. TXN chart PNGs exist on disk but are not referenced in the SharedResult, so downstream code (results page, deck builder) can't find them.

### Fix

```python
# After run_pipeline returns, collect chart PNGs from output dir
chart_dir = settings.output_dir / "charts"
for ar in analyses:
    charts_for_ar = []
    chart_path = chart_dir / f"{ar.name}.png"
    if chart_path.exists():
        charts_for_ar.append(chart_path)
    results[ar.name] = SharedResult(..., charts=charts_for_ar)
```

- [ ] Collect chart PNG paths from disk after export
- [ ] Pass them in `SharedResult.charts` field
- [ ] Verify `SharedResult` dataclass accepts `charts` param

---

## Bug 5: Failed Analyses Silently Dropped (MEDIUM)

**File:** `packages/txn_analysis/src/txn_analysis/runner.py:98-100`

```python
if ar.error:
    logger.warning("Skipping failed analysis: %s (%s)", ar.name, ar.error)
    continue  # Removed from results, no UI indication
```

When analyses fail, they're silently removed from the result dict. User sees "25 results" instead of "25/35 results (10 failed)" -- no indication that anything went wrong.

### Fix

- [ ] Include failed analyses in results with `success=False` flag
- [ ] Or: add summary of failed analyses to progress callback
- [ ] Add failure count to completion message: `"TXN complete -- 25/35 analyses (10 skipped)"`

---

## Bug 6: Error Traceback Truncated to 300 Chars (MEDIUM)

**File:** `packages/platform_app/src/platform_app/pages/home.py:1160`

```python
_status_text.error(_tb_str[-300:])  # Root cause often cut off
```

When TXN crashes, the user only sees the last 300 characters of the traceback, which is usually just the innermost exception. The actual root cause (e.g., "data_file is None") is lost.

### Fix

- [ ] Show last 500 chars of traceback
- [ ] Or: extract just the final exception line + root cause line
- [ ] Add `st.expander("Full error")` with complete traceback

---

## Cross-Platform Issues (User Review Findings)

### P1-A: TXN Directory Merge Bypasses Pipeline Parsing (CRITICAL)

**File:** `packages/platform_app/src/platform_app/utils/data_ingestion.py:169-185`

When the UI loads multiple TXN files from a directory, `_combine_tran_files()` does a raw `pd.concat()` without running `resolve_columns()` or any of the pipeline's column normalization. The pipeline's `load_data()` function applies merchant consolidation, year/month derivation, business flag normalization, and partial-month flagging -- none of which happen on the UI merge path.

**Result:** Column names may not match what analyses expect. Derived columns are missing. Analyses fail or produce wrong results silently.

### Fix

- [ ] Ensure UI multi-file loading path runs the same column resolution as the pipeline
- [ ] The in-memory `_load_tran_to_df()` we already built partially addresses this -- verify it calls `resolve_columns()` and all normalization steps

---

### P1-B: Age/Tenure Calculations Use System Clock (CRITICAL)

**Files:**
- `packages/ars_analysis/src/ars_analysis/data/format_odd.py:114-129`
- `packages/txn_analysis/src/txn_analysis/data_loader.py:493-505`

Both `format_odd()` and TXN's `load_odd()` compute age and tenure columns using `pd.Timestamp.now()` (system time). This means:
- Results are non-deterministic: running the same data on different days produces different outputs
- Cannot reproduce past results
- Testing is fragile (timestamps shift)

### Fix

- [ ] Accept an optional `reference_date` parameter (default: today)
- [ ] Use `reference_date` instead of `pd.Timestamp.now()` in all age/tenure calculations
- [ ] Pass through from PipelineContext or Settings

---

### P2-A: Run History Logs Incorrect Runtime and Modules (MEDIUM)

**File:** `packages/platform_app/src/platform_app/pages/run_analysis.py:250-263`

The run history records elapsed time and module counts at the wrong point in the execution flow -- capturing values before the pipeline finishes rather than after. Module count may reflect selected modules, not actually executed ones.

### Fix

- [ ] Capture elapsed time AFTER pipeline completes
- [ ] Log actual executed module count from results, not from the selection list

---

### P2-B: ODD Merge Key Normalization Missing (MEDIUM)

**File:** `packages/txn_analysis/src/txn_analysis/data_loader.py:540-555`

When TXN data is merged with ODD data via account number, there's no normalization of the merge key. Account numbers may have leading zeros, whitespace, or different types (int vs string) between the two files. This causes silent merge failures -- rows that should match don't.

### Fix

- [ ] Strip whitespace and normalize type (string) on both sides before merge
- [ ] Log merge hit rate so silent drops are visible
- [ ] Add warning when merge rate < 80%

---

### P2-C: ICS Normalization Silently Coerces Unknowns to 'No' (MEDIUM)

**File:** `packages/ics_toolkit/src/ics_toolkit/data_loader.py:84-94`

ICS account flag normalization treats any value that isn't explicitly 'Yes' as 'No'. Unknown values, blanks, NaN, and typos like 'yes' or 'Y' are all silently mapped to 'No', undercounting ICS accounts.

### Fix

- [ ] Normalize case before comparison (`str.upper()` or `str.lower()`)
- [ ] Map NaN/blank to 'Unknown' instead of 'No'
- [ ] Log count of unknown values for transparency

---

### P3-A: Dead/Unused UI Pages and Components (LOW)

Several UI pages and components are imported but no longer wired into navigation or have been superseded by the wizard flow. These add confusion and maintenance burden.

### Fix

- [ ] Audit all pages in `platform_app/pages/` for active routing
- [ ] Remove or archive unused pages
- [ ] Clean up sidebar navigation to match actual active pages

---

### P3-B: Unused/Legacy Shared Helpers (LOW)

The `shared` package contains helper functions that were written for earlier architecture iterations and are no longer called by any module.

### Fix

- [ ] Grep for unused exports in `shared/`
- [ ] Remove dead helper functions
- [ ] Verify no downstream imports break

---

### P3-C: Vectorization Opportunities (LOW)

Several modules use row-wise `apply(lambda)` loops where vectorized pandas operations (merge, map, boolean indexing) would be faster and clearer.

### Fix

- [ ] Identify top offenders via profiling or grep for `apply(lambda`
- [ ] Replace with vectorized equivalents
- [ ] Benchmark before/after on large datasets

---

## Implementation Order

**Phase 1 -- TXN Blockers (Bugs 1-2, P1-A)**
1. **Bug 1** (5 min) -- Fix the None crash. This is the blocker.
2. **Bug 2** (5 min) -- Show real export status.
3. **P1-A** (5 min) -- Verify in-memory path runs full normalization.

**Phase 2 -- Visibility (Bugs 3-6)**
4. **Bug 5** (5 min) -- Show failure counts in completion message.
5. **Bug 6** (5 min) -- Better error display.
6. **Bug 3** (10 min) -- Surface chart failures.
7. **Bug 4** (15 min) -- Wire chart paths into SharedResult.

**Phase 3 -- Data Integrity (P1-B, P2-A/B/C)**
8. **P1-B** (20 min) -- Add `reference_date` parameter to age/tenure calculations.
9. **P2-B** (10 min) -- Normalize ODD merge keys.
10. **P2-C** (10 min) -- Fix ICS flag case-sensitivity and unknown handling.
11. **P2-A** (10 min) -- Fix run history timing and module counts.

**Phase 4 -- Cleanup (P3-A/B/C)**
12. **P3-A** (15 min) -- Remove dead UI pages.
13. **P3-B** (10 min) -- Remove unused shared helpers.
14. **P3-C** (30 min) -- Vectorize hot-path apply(lambda) calls.

---

## Verification

- [ ] `uv run pytest tests/txn/ -q` -- all pass
- [ ] `uv run pytest tests/platform/ -q` -- all pass
- [ ] `uv run pytest tests/integration/ -q` -- all pass
- [ ] `uv run pytest tests/ics/ -q` -- all pass
- [ ] `uv run pytest tests/ars/ -q` -- all pass
- [ ] `uv run ruff check . && uv run ruff format --check .` -- clean
- [ ] Manual: Run Streamlit with multi-file TXN input, verify Excel is generated
- [ ] Manual: Verify progress shows "Exported N files" (not "Export complete")
- [ ] Manual: Verify failed analyses show count in completion message
- [ ] Manual: Verify ICS 'yes'/'Y'/blank values handled correctly
- [ ] Manual: Verify ODD merge logs merge hit rate

---

## NOT in Scope (Future)

- **TXN PPTX deck builder**: TXN currently only exports Excel + PNGs, no PowerPoint. This is a feature request, not a bug. The ARS deck builder doesn't know TXN's layout.
- **ICS has the same chart-path issue**: Same fix pattern, separate PR.
- **Chart template "v4_consultant"**: Works in tests but could fail on certain data. Monitor.
