---
module: ARS DCTR
date: 2026-02-07
problem_type: logic_error
component: service_object
symptoms:
  - "DCTR decade analysis silently drops data from years not in hardcoded list"
  - "Historical DCTR analysis filters to fixed year range, misses future data"
root_cause: logic_error
resolution_type: code_fix
severity: medium
tags: [hardcoded-years, time-bomb, dctr, date-range, future-proof]
---

# Troubleshooting: Hardcoded Year Lists Create Silent Time Bombs

## Problem
Two functions in `dctr.py` used hardcoded year lists that would silently exclude valid data in future years. `map_to_decade()` used `[2020, 2021, ..., 2026]` (would miss 2027+ data) and `analyze_historical_dctr()` used `.isin([2023, 2024, 2025, 2026])` (would miss 2027+ data and always included years that might not exist yet).

## Environment
- Module: ARS DCTR (`ars_analysis/dctr.py`)
- Python: 3.11
- Date: 2026-02-07

## Symptoms
- `map_to_decade()` would silently assign years >= 2027 to no decade bucket
- `analyze_historical_dctr()` would filter out data from years >= 2027
- No error raised -- data silently dropped from analysis
- Requires annual code updates to keep working (maintenance burden)

## What Didn't Work

**Direct solution:** The problem was identified during code review and fixed on the first attempt.

## Solution

Replace hardcoded year lists with dynamic range computations.

**Code changes:**
```python
# map_to_decade() -- Before:
if yr in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
    return "2020s"

# map_to_decade() -- After:
if yr >= 2020:
    return "2020s"

# analyze_historical_dctr() -- Before:
valid = merged[merged["Year"].isin([2023, 2024, 2025, 2026])]

# analyze_historical_dctr() -- After:
_current_year = pd.Timestamp.now().year
valid = merged[merged["Year"] >= _current_year - 3]
```

## Why This Works

1. **Root cause:** Developer listed years explicitly instead of using range-based logic. This creates a "time bomb" that silently breaks when the calendar advances past the last listed year.
2. **map_to_decade fix:** `yr >= 2020` correctly captures all 2020s years without an upper bound. When 2030 arrives, a new decade bucket should be added, but at least data won't be silently dropped.
3. **analyze_historical_dctr fix:** `_current_year - 3` creates a rolling 4-year window that automatically advances. No manual updates needed.

## Prevention

- Never hardcode year lists -- use `datetime.now().year` or `pd.Timestamp.now().year` with relative offsets
- Search for `isin([20` patterns during code review to catch hardcoded year lists
- Add tests with future-dated data to verify no silent data loss
- For decade mapping, use `yr // 10 * 10` arithmetic instead of explicit year lists

## Related Issues

- See also: [hardcoded-ylim-dctr-charts-20260207.md](hardcoded-ylim-dctr-charts-20260207.md) -- another hardcoded value issue in the same module
