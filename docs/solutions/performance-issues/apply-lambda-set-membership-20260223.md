---
title: "Replace apply(lambda) set membership with merge-based join"
category: performance-issues
tags: [pandas, apply, lambda, merge, vectorized, performance, set-membership]
module: txn_analysis.analyses.recurring
symptom: "Slow onset spend calculation using df.apply(lambda row: tuple in set, axis=1)"
root_cause: "apply(lambda) with axis=1 iterates row-by-row in Python; O(n) per row with large set membership check"
date_solved: 2026-02-23
---

# Replace apply(lambda) set membership with merge-based join

## Problem

When calculating spend at onset for recurring payment detection, we needed to sum transaction amounts for specific (account, merchant, month) triples. The initial implementation used `apply(lambda)` to check set membership row-by-row.

### Slow approach

```python
# SLOW -- iterates every row in Python, checking tuple membership
pairs = set(zip(onsets["primary_account_num"], onsets["merchant_consolidated"]))
onset_mask = df.apply(
    lambda r: (r["primary_account_num"], r["merchant_consolidated"]) in pairs,
    axis=1,
)
onset_txns = df[onset_mask]
# Then filter to onset months and sum...
```

### Why it's slow

- `apply(lambda, axis=1)` converts each row to a Series and calls the Python function -- pure Python loop over every transaction
- For 500K+ transaction rows, this takes seconds even with a small set
- The tuple construction `(r["col1"], r["col2"])` adds overhead per row
- The `in` check on a set is O(1), but the per-row overhead dominates

## Solution

Replace with a merge-based join -- let pandas/numpy do the heavy lifting:

```python
# FAST -- vectorized merge on 3 columns
onset_txns = onsets.rename(columns={"onset_month": "year_month"}).merge(
    df[["primary_account_num", "merchant_consolidated", "year_month", "amount"]],
    on=["primary_account_num", "merchant_consolidated", "year_month"],
    how="inner",
)
onset_spend = (
    onset_txns.groupby("year_month")["amount"]
    .sum()
    .round(2)
    .reset_index()
    .rename(columns={"year_month": "onset_month", "amount": "onset_spend"})
)
```

### Why this is better

1. **Vectorized**: The merge happens in C/Cython inside pandas, not Python
2. **Selective columns**: Only select the 4 columns needed before merge (reduces memory)
3. **Inner join**: Naturally filters to only matching rows -- no boolean mask needed
4. **Composable**: The result feeds directly into groupby aggregation

## General Pattern

Whenever you see this anti-pattern:

```python
# BAD: apply(lambda) for filtering by multi-column match
target_set = set(zip(ref_df["col_a"], ref_df["col_b"]))
mask = df.apply(lambda r: (r["col_a"], r["col_b"]) in target_set, axis=1)
filtered = df[mask]
```

Replace with:

```python
# GOOD: merge-based filter
filtered = ref_df[["col_a", "col_b"]].drop_duplicates().merge(
    df, on=["col_a", "col_b"], how="inner"
)
```

Or if you need the exact same DataFrame structure:

```python
# GOOD: isin with MultiIndex
idx = pd.MultiIndex.from_frame(ref_df[["col_a", "col_b"]])
mask = pd.MultiIndex.from_frame(df[["col_a", "col_b"]]).isin(idx)
filtered = df[mask]
```

## Performance Impact

| Approach | 100K rows | 500K rows | 1M rows |
|----------|-----------|-----------|---------|
| `apply(lambda)` | ~2s | ~10s | ~20s |
| `merge` inner join | ~0.05s | ~0.2s | ~0.4s |
| `MultiIndex.isin` | ~0.1s | ~0.3s | ~0.6s |

Approximate; actual times depend on cardinality of the join keys.

## Prevention

- **Never use `apply(lambda, axis=1)` for filtering** -- always use merge or vectorized operations
- **Lint rule**: Search codebase for `\.apply\(lambda.*axis=1\)` and evaluate if a merge would work
- **When you see a `set()` of tuples being checked row-by-row**, it's always a merge candidate
- **Profile first**: If apply is on < 1000 rows, the overhead is negligible; optimize only when it matters

## References

- File: `packages/txn_analysis/src/txn_analysis/analyses/recurring.py` lines 97-110
- Tests: `tests/txn/test_recurring.py` (TestOnsetSummaryByMonth::test_spend_at_onset)
