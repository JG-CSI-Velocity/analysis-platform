# Analysis Platform Review (Dead Code, Efficiency, UX, Data Accuracy)

Date: 2026-02-25
Scope: Full repo (platform UI + orchestrator + shared + ARS/TXN/ICS pipelines)
Method: Static review, targeted code scans, no tests or profiling

## Executive Summary
The codebase is generally consistent and well-structured, but there are several data-accuracy risks (formatting drift, parsing mismatches, and logging inaccuracies) plus a few dead/unused modules. The highest-impact issues are the transaction directory merge in the UI (parsing mismatch vs. pipeline), date/age calculations tied to the system clock (non-reproducible outputs), and run history metrics that report incorrect durations and executed modules.

## Findings (Prioritized)

### P1 — Data Accuracy / Reproducibility
1) **TXN directory merge in UI bypasses pipeline parsing rules.**
   - **Where:** `packages/platform_app/src/platform_app/pages/data_ingestion.py:169-185`
   - **Issue:** UI merge uses `pd.read_csv` (or tab-delimited read) without delimiter/header detection, metadata skipping, or column normalization. Pipeline uses `txn_analysis.data_loader._read_csv_autodetect` with delimiter sniffing and headerless handling. Merged output can be mis-parsed, leading to incorrect analyses if the merged file is used for TXN runs.
   - **Fix:** Reuse `txn_analysis.data_loader._read_csv_autodetect` (or a shared helper) in the UI merge path; align UI parsing with pipeline parsing rules.

2) **Age/tenure calculated against current system time (non-deterministic).**
   - **Where:**
     - `packages/shared/src/shared/format_odd.py:114-129`
     - `packages/ars_analysis/src/ars_analysis/pipeline/steps/format.py:150-162`
     - `packages/txn_analysis/src/txn_analysis/data_loader.py:494-505`
   - **Issue:** These calculations use `datetime.now()` / `pd.Timestamp.now()`. Outputs drift over time and are not reproducible; this can change age/tenure buckets and downstream metrics in ARS/TXN.
   - **Fix:** Anchor to a deterministic date (e.g., max Date Opened, max transaction date, or a report date in settings). Log the anchor used.

### P2 — Data Accuracy / UX
3) **Run history runtime and executed modules are inaccurate.**
   - **Where:** `packages/platform_app/src/platform_app/pages/run_analysis.py:250-263`
   - **Issue:** `runtime_seconds` uses the last pipeline's `t0`, not total runtime; `total_time` is unused and set to 0 when results exist. Also, `modules_run` logs *selected* modules even though the pipeline runs *all* modules for a product. Run history displays misleading performance and module execution details.
   - **Fix:** Track a single `run_start` before the loop; set `runtime_seconds = time.time() - run_start`. If module-level runs are not supported, log modules_run as `"ALL"` or the full registry list for that pipeline.

4) **ODD merge may silently fail due to account number dtype mismatch.**
   - **Where:** `packages/txn_analysis/src/txn_analysis/data_loader.py:540-555`
   - **Issue:** Merge uses `primary_account_num` vs. `Acct Number` without normalization. If one side is numeric and the other is string (or has leading zeros), match rates drop, degrading demographics-based analyses (M11–M14, spending behavior).
   - **Fix:** Normalize both keys (string, strip, zero-pad if needed). Log match rate thresholds and warn when below a minimum.

5) **Duplicate `format_odd` implementations can drift and produce inconsistent outputs.**
   - **Where:**
     - `packages/shared/src/shared/format_odd.py:29-180`
     - `packages/ars_analysis/src/ars_analysis/pipeline/steps/format.py:63-205`
   - **Issue:** UI/CLI uses shared `format_odd`; ARS pipeline uses its own implementation with different numeric coercion and account age calculation (365 vs 365.25). This risks different formatted outputs depending on entrypoint.
   - **Fix:** Consolidate to a single source of truth (shared) and remove the duplicate, or add tests that guarantee parity across both implementations.

6) **ICS string normalization defaults unknown values to “No” without warning.**
   - **Where:** `packages/ics_toolkit/src/ics_toolkit/analysis/data_loader.py:84-94`
   - **Issue:** Any unexpected value (e.g., "T", "YES ", or typos) is coerced to "No" silently. This can undercount ICS Account/Debit/Business and skew penetration metrics.
   - **Fix:** Preserve unknowns as "Unknown" and log a warning with sample values (similar to TXN `business_flag` handling).

### P3 — Dead/Unused Code + Efficiency Opportunities
7) **Unused page: `history.py` is not part of navigation.**
   - **Where:** `packages/platform_app/src/platform_app/pages/history.py:1`
   - **Impact:** Dead code; increases maintenance surface and confuses future edits.
   - **Fix:** Remove or wire into navigation (currently only `run_history.py` is used).

8) **Unused component: `client_selector.py`.**
   - **Where:** `packages/platform_app/src/platform_app/components/client_selector.py:1`
   - **Impact:** Dead code; not referenced in UI.
   - **Fix:** Remove or integrate into relevant pages.

9) **Unused shared helpers (likely legacy).**
   - **Where:**
     - `packages/shared/src/shared/charts.py:1`
     - `packages/shared/src/shared/excel.py:1`
     - `packages/shared/src/shared/data_loader.py:29-60` (load_tran/load_odd)
   - **Impact:** Not referenced outside tests; potential cleanup target or document as public API.

10) **ICS append merge uses Python loops for deduping.**
   - **Where:** `packages/ics_toolkit/src/ics_toolkit/append/merger.py:61-75`
   - **Impact:** Row-wise loop scales poorly for large files.
   - **Fix:** Use vectorized groupby + aggregation, avoid iterrows.

11) **Row-wise apply in ARS attrition impact.**
   - **Where:** `packages/ars_analysis/src/ars_analysis/analytics/attrition/impact.py:179-187`
   - **Impact:** Extra CPU for large ODD datasets.
   - **Fix:** Replace with vectorized `np.select` similar to shared `format_odd` segmentation.

## UX Improvement Opportunities
- **Run Analysis button label misleads:** it displays “Execute N Modules” even though full pipelines are run. Consider “Run ARS/TXN/ICS Pipelines” and list selected products.
  - `packages/platform_app/src/platform_app/pages/run_analysis.py:156-161`
- **Add clearer warnings when TXN ODD is missing:** some analyses are disabled; surface which ones are skipped.
  - `packages/platform_app/src/platform_app/pages/data_ingestion.py:196-200`

## Suggested Follow-ups (Optional)
- Add a shared parsing utility for transaction files used by both UI merge and pipeline loader.
- Add a single report date field (settings or inferred) to control age/tenure calculations.
- Add a small parity test that compares shared/ARS `format_odd` outputs on a fixture.
- Add warnings for low ODD merge match rates and unknown categorical values.

## Tests to Run After Fixes
- `uv run pytest tests/shared -q`
- `uv run pytest tests/ars -q`
- `uv run pytest tests/txn -q`
- `uv run pytest tests/ics -q`
- `uv run pytest tests/platform -q`
- `uv run pytest tests/integration -q`

