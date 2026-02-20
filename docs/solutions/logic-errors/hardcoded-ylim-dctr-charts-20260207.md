---
module: ARS DCTR
date: 2026-02-07
problem_type: logic_error
component: service_object
symptoms:
  - "DCTR decade comparison chart clips data below 50%"
  - "Clients with low take rates see truncated or invisible bars"
root_cause: logic_error
resolution_type: code_fix
severity: high
tags: [matplotlib, y-axis, hardcoded-limit, data-driven, dctr, chart]
---

# Troubleshooting: Hardcoded Y-Axis Limit Hides Low DCTR Values

## Problem
The DCTR decade comparison chart (`run_dctr_decade_comparison`) used a hardcoded `ax.set_ylim(50, 100)` which silently clipped any debit card take rates below 50%. Some client segments (especially business accounts or small branches) can have rates well below 50%.

## Environment
- Module: ARS DCTR (`ars_analysis/dctr.py`)
- Python: 3.11
- matplotlib for chart generation
- Date: 2026-02-07

## Symptoms
- DCTR decade comparison chart showed bars starting at 50% minimum
- Clients with low take rates saw truncated or invisible data
- No error raised -- data silently hidden from the presentation

## What Didn't Work

**Direct solution:** The problem was identified and fixed on the first attempt during code review.

## Solution

Replace hardcoded y-axis with data-driven bounds computed from all rate arrays.

**Code changes:**
```python
# Before (broken):
ax.tick_params(axis="y", labelsize=24)
ax.set_ylim(50, 100)

# After (fixed):
ax.tick_params(axis="y", labelsize=24)
# Data-driven y-axis: 5pp padding below min, capped at 100
all_rates = [v for v in overall_rates + personal_rates + (business_rates if has_biz else [])
             if not np.isnan(v)]
y_min = max(0, (min(all_rates) - 5) // 5 * 5) if all_rates else 0
ax.set_ylim(y_min, 100)
```

## Why This Works

1. **Root cause:** A developer hardcoded `set_ylim(50, 100)` assuming DCTR rates would always be above 50%. This is not true for all client segments.
2. **Solution:** Computes `y_min` from the actual data with 5 percentage-point padding below the minimum, rounded down to the nearest 5, floored at 0. The upper bound stays at 100 since rates are percentages.
3. **Edge case handling:** If `all_rates` is empty (no valid data), defaults to `y_min=0` to avoid min() on empty sequence.

## Prevention

- Never hardcode axis limits in data visualization code -- always derive from actual data
- When setting chart bounds, add padding (e.g., 5pp) and use `max(0, ...)` / `min(100, ...)` guards
- Review all `set_ylim()` / `set_xlim()` calls for hardcoded values during code review
- Add assertions in tests that chart y-axis accommodates all plotted values

## Related Issues

No related issues documented yet.
