---
title: "Cross-referencing TXN transactions with ODD demographics via context"
category: integration-issues
tags: [pandas, cross-reference, ODD, TXN, context, demographics, merge, account-number]
module: txn_analysis.analyses.spending_behavior
symptom: "Need to enrich transaction data with account demographics (age, branch, mailer response) from a separate ODD file"
root_cause: "Design pattern -- not a bug. Documents the established approach for cross-pipeline data joining"
date_solved: 2026-02-23
---

# Cross-referencing TXN transactions with ODD demographics

## Context

The TXN analysis pipeline processes transaction CSVs. The ARS pipeline processes ODD (account demographics) Excel files. Some analyses need both -- e.g., "How does spending differ by age group?" or "Do mailer responders swipe earlier in the month?"

## The Pattern

### 1. ODD is passed via context dict

The pipeline orchestrator loads ODD and injects it into the shared context:

```python
# In run_all_analyses() -- analyses/__init__.py
context: dict = {"completed_results": {}}
if odd_df is not None:
    context["odd_df"] = odd_df
```

Each analysis function receives context as its 5th parameter:

```python
def analyze_spending_behavior(
    df: pd.DataFrame,          # all transactions
    business_df: pd.DataFrame,  # business-flagged
    personal_df: pd.DataFrame,  # personal-flagged
    settings: Settings,
    context: dict | None = None,  # shared context with ODD
) -> AnalysisResult:
```

### 2. Detect the account column flexibly

ODD files have inconsistent column names across clients:

```python
def _detect_acct_col(odd_df: pd.DataFrame) -> str | None:
    for col in ("Account Number", "Acct Number", "Account_Number"):
        if col in odd_df.columns:
            return col
    return None
```

### 3. Merge on account number (string-safe)

Always cast both sides to string before joining -- account numbers may be stored as int in ODD but string in TXN:

```python
acct_age = odd_df[[acct_col, age_col]].copy()
acct_age[acct_col] = acct_age[acct_col].astype(str)

merged = txn_df.merge(
    acct_age,
    left_on="primary_account_num",  # TXN column
    right_on=acct_col,              # ODD column (detected)
    how="inner",
)
```

### 4. Graceful degradation when ODD is absent

Analyses that need ODD must handle three cases:
- No ODD at all (`context is None` or `"odd_df" not in context`)
- Empty ODD (`odd_df.empty`)
- ODD missing expected columns (no account number, no age, no branch)

```python
ctx = context or {}
odd_df = ctx.get("odd_df")

if odd_df is None or (isinstance(odd_df, pd.DataFrame) and odd_df.empty):
    return AnalysisResult.from_df(
        "spending_behavior",
        "Spending Behavior Analysis",
        pd.DataFrame({"Note": ["ODD data required for demographic analysis"]}),
        metadata={"sheet_name": "M17 Behavior"},
    )
```

Return a Note row (not an error) so the pipeline test that checks for zero errors in non-adapter analyses still passes.

### 5. Mailer response column detection

ODD mailer columns follow the pattern `MmmYY Mail` / `MmmYY Resp` (e.g., `Jan25 Mail`, `Jan25 Resp`):

```python
def _detect_resp_pairs(odd_df: pd.DataFrame) -> list[tuple[str, str, str]]:
    mail_cols = sorted(
        [c for c in odd_df.columns if re.match(r"^[A-Z][a-z]{2}\d{2} Mail$", c)],
        key=lambda c: c[:5],
    )
    pairs = []
    for mc in mail_cols:
        month = mc.replace(" Mail", "")
        rc = f"{month} Resp"
        if rc in odd_df.columns:
            pairs.append((month, rc, mc))
    return pairs
```

Response values from `_RESPONSE_SEGMENTS = {"NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"}` indicate a valid response.

## Key Decisions

1. **No cross-package imports**: M17 duplicates `_RESPONSE_SEGMENTS` rather than importing from ars_analysis, keeping txn_analysis independent
2. **Inner join, not left**: Only include transactions where the account exists in ODD -- avoids NaN pollution
3. **String-safe joins**: Always `.astype(str)` both sides before merge
4. **Return Note row, not error**: Pipeline tests check `error is not None` for failures; missing ODD is expected, not an error

## References

- M17 implementation: `packages/txn_analysis/src/txn_analysis/analyses/spending_behavior.py`
- Registry wiring: `packages/txn_analysis/src/txn_analysis/analyses/__init__.py` lines 50, 131
- Tests: `tests/txn/test_spending_behavior.py` (TestAnalyzeSpendingBehavior class)
- Context injection: `packages/txn_analysis/src/txn_analysis/analyses/__init__.py` lines 154-156
