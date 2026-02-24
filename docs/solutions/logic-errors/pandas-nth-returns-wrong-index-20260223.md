---
title: "pandas groupby().nth() returns wrong index for positional selection"
category: logic-errors
tags: [pandas, groupby, nth, cumcount, vectorized, index-alignment]
module: txn_analysis.analyses.recurring
symptom: "KeyError on column name after groupby().nth().reset_index() -- column exists in original DataFrame but not in result"
root_cause: "nth() returns rows indexed by the original DataFrame integer index, not group keys; reset_index() produces integer range, losing group columns"
date_solved: 2026-02-23
---

# pandas groupby().nth() returns wrong index for positional selection

## Problem

When building onset tracking for recurring payment detection, we needed to find the N-th distinct month for each account-merchant pair. The goal: for each (account, merchant) group, select the row where `month_rank == min_months - 1` (the onset month).

### Attempted approach

```python
# WRONG -- nth() returns rows by original DF index, not group keys
onset_rows = (
    unique_months.groupby(["primary_account_num", "merchant_consolidated"])
    .nth(min_months - 1)
    .reset_index()
)
# onset_rows now has integer index columns (0, 1, 2...)
# NOT primary_account_num and merchant_consolidated
result = qualifying.merge(
    onset_rows, on=["primary_account_num", "merchant_consolidated"], how="inner"
)
# KeyError: 'primary_account_num' -- column doesn't exist!
```

### Symptom

`KeyError: 'primary_account_num'` when merging with the onset rows. The column existed in the original DataFrame but `nth().reset_index()` didn't produce it because `nth()` returns a DataFrame indexed by the **original integer position**, not by the groupby keys.

## Root Cause

`pandas.GroupBy.nth()` selects the N-th row **within each group** but returns results indexed by the original DataFrame's index (integer positions). When you call `.reset_index()`, you get an integer range index -- the group key columns are NOT restored as columns.

This is different from `.first()`, `.last()`, or `.agg()` which return results indexed by the group keys.

### The subtle trap

`nth()` appears to work in isolation -- it returns a DataFrame with the right number of rows. The bug only manifests when you try to merge/join on the group keys, because they aren't columns in the output.

## Solution

Replace `nth()` with `cumcount()` to assign a rank within each group, then filter:

```python
# CORRECT -- cumcount() preserves all original columns
unique_months["month_rank"] = unique_months.groupby(
    ["primary_account_num", "merchant_consolidated"]
).cumcount()

# Select onset rows directly -- all original columns are intact
onset_rows = unique_months[unique_months["month_rank"] == min_months - 1][
    ["primary_account_num", "merchant_consolidated", "year_month"]
].rename(columns={"year_month": "onset_month"})

# Merge works because columns exist
result = qualifying.merge(
    onset_rows, on=["primary_account_num", "merchant_consolidated"], how="inner"
)
```

### Why cumcount() works better

1. `cumcount()` adds a new column to the existing DataFrame, preserving all original columns
2. Filtering on `month_rank == N` returns rows with all original columns intact
3. No index confusion -- the DataFrame keeps its structure throughout

## Prevention

- **Prefer `cumcount()` + filter over `nth()`** when you need the full row data with group keys
- **Test merge operations** with assertions: `assert "expected_col" in df.columns` before merge
- **When using `nth()`**, always check the resulting columns with `print(df.columns.tolist())` before assuming group keys are present
- **Alternative**: Use `.iloc` within `groupby().apply()` if you need positional selection with full row data

## References

- File: `packages/txn_analysis/src/txn_analysis/analyses/recurring.py` lines 20-66
- Tests: `tests/txn/test_recurring.py` (TestOnsetTimeline class)
- pandas docs: GroupBy.nth returns "the nth row from each group" but indexed by original position
