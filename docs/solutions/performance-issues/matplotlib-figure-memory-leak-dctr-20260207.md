---
module: ARS DCTR
date: 2026-02-07
problem_type: performance_issue
component: service_object
symptoms:
  - "Memory grows during long ARS pipeline runs with many charts"
  - "matplotlib figures not closed when exceptions occur between fig creation and save"
root_cause: memory_leak
resolution_type: code_fix
severity: high
tags: [matplotlib, memory-leak, plt-close, figure, try-finally, dctr, chart]
---

# Troubleshooting: Matplotlib Figure Memory Leak in DCTR Charts

## Problem
The DCTR analysis module creates 12+ matplotlib figures during a pipeline run. If an exception occurs between figure creation (`plt.subplots()`) and `_save_chart()` (which calls `plt.close()`), the figure is never closed, leaking memory. Over many analysis runs or with large datasets, this can exhaust available memory.

## Environment
- Module: ARS DCTR (`ars_analysis/dctr.py`)
- Python: 3.11
- matplotlib for chart generation
- Date: 2026-02-07

## Symptoms
- Memory grows during long ARS pipeline runs processing multiple clients
- matplotlib figures not closed when exceptions occur between `fig, ax = plt.subplots()` and `_save_chart(fig, ...)`
- No explicit error -- silent resource leak

## What Didn't Work

**Direct solution:** The problem was identified during code review and fixed with a systematic pattern.

## Solution

Wrap all 12 chart-generating sites with `try/finally: plt.close(fig)` to ensure figures are always closed, even when exceptions occur.

**Code changes (pattern applied 12 times):**
```python
# Before (broken):
fig, ax = plt.subplots(figsize=(14, 7))
# ... chart building code ...
_save_chart(fig, chart_dir / "chart_name.png")

# After (fixed):
fig, ax = plt.subplots(figsize=(14, 7))
try:
    # ... chart building code ...
    _save_chart(fig, chart_dir / "chart_name.png")
finally:
    plt.close(fig)
```

**Note:** `fig = plt.subplots()` stays OUTSIDE the try block so that if `plt.subplots()` itself fails, we don't try to close a nonexistent figure. The `_save_chart()` helper already calls `plt.close()`, but the `finally` block is a safety net for exceptions that occur before `_save_chart()` is reached.

## Why This Works

1. **Root cause:** matplotlib figures consume significant memory (especially at 150 DPI with large datasets). When an exception occurs during chart configuration (e.g., bad data, missing columns), the figure object is abandoned without being closed.
2. **Solution:** Python's `try/finally` guarantees `plt.close(fig)` runs regardless of whether the chart code succeeds or throws an exception.
3. **Idempotency:** Calling `plt.close(fig)` on an already-closed figure is safe (no-op), so the double-close from `_save_chart()` + `finally` is harmless.

## Prevention

- Always wrap matplotlib figure creation with `try/finally: plt.close(fig)` in production code
- Consider a context manager pattern for chart creation: `with create_figure(...) as (fig, ax):`
- In code review, flag any `plt.subplots()` call that lacks a corresponding `plt.close()` in a finally block
- The same pattern applies to reg_e.py, attrition.py, and other ARS chart modules

## Related Issues

No related issues documented yet.
