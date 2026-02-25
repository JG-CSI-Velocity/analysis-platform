# Plan: ICS Product Review Integration

## Objective

Integrate ICS (Insured Cash Sweep) product review analyses into the ARS pipeline.
The user already has a tested `ics_append` tool that annotates ODD files with two
columns (`ICS Account`, `ICS Source`). This plan covers wiring those columns into
the ARS pipeline to produce an ICS-focused PPTX + Excel product review alongside
the existing ARS output.

---

## Context: What Already Exists

### ics_append (ready, tested)
- Location: `/Users/jgmbp/Desktop/ics_append/`
- 12 modules, 738 statements, 178 tests, 91% coverage
- CLI: `python -m ics_append --base-dir ... --ars-dir ... -m 2026.01 run-all`
- Appends two columns to the ODD file:
  - `ICS Account` -- "Yes" or "No"
  - `ICS Source` -- "REF", "DM", "Both", or "" (blank)
- Output: `{clientID}_oddd_annotated.xlsx` in the ARS month folder

### ics_analysis (reference implementation)
- Location: `/Users/jgmbp/Desktop/ics_analysis/`
- 33 analyses in 6 groups using Plotly charts + DeckBuilder PPTX
- Required columns: `ICS Account`, `Source` (NOT "ICS Source"), `Stat Code`,
  `Debit?`, `Business?`, `Date Opened`, `Prod Code`, `Branch`, `Curr Bal`
- Pre-filtered DataFrames: `df`, `ics_all`, `ics_stat_o`, `ics_stat_o_debit`
- Standalone tool -- not integrated into the ARS pipeline

### ARS pipeline (target for integration)
- Location: `/Users/jgmbp/Desktop/ARS-pwrpt/ars_analysis-jupyter/`
- `pd.read_excel` loads all 436+ ODD columns -- ICS columns auto-appear
- `app.py` already has `'ics': {'coming_soon': True}` placeholder
- Plugin architecture: each analysis is a module with `run_*_suite(ctx)`
- No ICS references in any Python file today

---

## Column Name Decision

**Critical alignment issue**: `ics_append` outputs `ICS Source`, but `ics_analysis`
expects `Source`. Two options:

1. **Rename on load** (recommended): In the ARS pipeline's ICS subset creation,
   rename `ICS Source` -> `Source` when building ICS-specific DataFrames. This
   avoids touching `ics_append` and keeps the column name unambiguous in the raw
   ODD (where there may already be other "Source" columns).

2. **Change ics_append output**: Make it output `Source` instead of `ICS Source`.
   Risky because it could collide with other Source-like columns in the ODD.

**Decision**: Option 1 -- rename on load within the ARS pipeline.

---

## Architecture: Two Integration Modes

### Mode A: Embedded ICS Phase in ARS Pipeline (recommended)

Add an ICS analysis phase to `run_pipeline()` that runs conditionally when the
ODD file contains `ICS Account` and `ICS Source` columns. This produces ICS slides
in the same PPTX alongside ARS analyses.

**Advantages**: Single pipeline run, single PPTX, familiar ctx pattern.
**Disadvantages**: Larger single pipeline, more slides per deck.

### Mode B: Separate ICS Pipeline

Keep ICS analysis as a standalone `python -m ics_analysis` invocation, separate
from the ARS pipeline. The user runs `ics_append` then `ics_analysis` as separate steps.

**Advantages**: Clean separation, already exists.
**Disadvantages**: Two separate PPTX files, can't cross-reference ARS data.

**Decision**: Mode A -- embed into ARS pipeline. The user explicitly asked to
"create another product review off this file's data" within the ARS context.

---

## Implementation Plan

### Session 0: ICS Subset Creation + Column Detection

**File**: `pipeline.py`

1. **Detect ICS columns** in `step_create_subsets()` (after line 663):
   ```python
   has_ics = 'ICS Account' in data.columns and 'ICS Source' in data.columns
   ctx['has_ics'] = has_ics
   ```

2. **Create ICS-specific subsets** (new block after existing subsets):
   ```
   ics_all         = data[data['ICS Account'] == 'Yes']
   ics_stat_o      = ics_all[ics_all['Stat Code'].str.upper() == 'O']
   ics_stat_o_debit = ics_stat_o[ics_stat_o['Debit?'] == 'Yes']
   ```
   Rename `ICS Source` -> `Source` on each subset for analysis compatibility.
   Store as `ctx['ics_all']`, `ctx['ics_stat_o']`, `ctx['ics_stat_o_debit']`.

3. **Log ICS summary** in pipeline output:
   ```
   ICS accounts: 2,341 (of 58,605 total)
   ICS Stat O: 1,892 | ICS Stat O + Debit: 1,543
   Sources: REF=1,200, DM=890, Both=251
   ```

**Tests**: Verify subset creation with and without ICS columns present.

---

### Session 1: Core ICS Analysis Module

**New file**: `ics_product.py` (~400-500 lines)

Port the 33 analyses from `ics_analysis` into the ARS ctx-based pattern. Group
into the same 6 sections:

#### Section 1: Summary (A16.1 - A16.7)
| ID | Name | Source DataFrame | Key Output |
|----|------|-----------------|------------|
| A16.1 | Total ICS Accounts | df, ics_all | ICS vs Non-ICS counts + % |
| A16.2 | Open ICS Accounts | df(stat O), ics_stat_o | ICS share among open |
| A16.3 | ICS by Stat Code | ics_all | Stat code breakdown |
| A16.4 | Product Code Distribution | ics_stat_o | Prod code breakdown |
| A16.5 | Debit Distribution | ics_stat_o | Debit Yes/No split |
| A16.6 | Debit x Prod Code | ics_stat_o | Crosstab |
| A16.7 | Debit x Branch | ics_stat_o | Crosstab |

#### Section 2: Source Analysis (A16.8 - A16.13)
| ID | Name | Key Column |
|----|------|-----------|
| A16.8 | Source Distribution | Source (renamed from ICS Source) |
| A16.9 | Source x Stat Code | Source x Stat Code |
| A16.10 | Source x Prod Code | Source x Prod Code |
| A16.11 | Source x Branch | Source x Branch |
| A16.12 | Account Type | Business? |
| A16.13 | Source by Year | Source x Year Opened |

#### Section 3: Demographics (A16.14 - A16.21)
| ID | Name | Computes |
|----|------|---------|
| A16.14 | Age Comparison | Account age distribution |
| A16.15 | Closures | Closed ICS by month |
| A16.16 | Open vs Close | O vs C counts |
| A16.17 | Balance Tiers | Curr Bal bins |
| A16.18 | Stat Open Close | Stat groups + avg balance |
| A16.19 | Age vs Balance | Age bins x avg balance |
| A16.20 | Balance Tier Detail | Balance x L12M activity |
| A16.21 | Age Distribution | Age range distribution |

#### Section 4: Activity (A16.22 - A16.26)
| ID | Name | Computes |
|----|------|---------|
| A16.22 | Activity Summary (KPIs) | 12 KPIs: total/active, swipes, spend |
| A16.23 | Activity by Source | L12M activity grouped by Source |
| A16.24 | Activity by Balance | Activity by Balance Tier |
| A16.25 | Activity by Branch | Activity by Branch |
| A16.26 | Monthly Trends | Per-month swipes/spend/active |

#### Section 5: Cohort (A16.27 - A16.36)
| ID | Name | Computes |
|----|------|---------|
| A16.27 | Cohort Activation | M1/M3/M6/M12 activation rates |
| A16.28 | Cohort Heatmap | Swipes per month per cohort |
| A16.29 | Cohort Milestones | M1/M3/M6/M12 aggregate |
| A16.31 | Activation Summary | Cross-cohort rates |
| A16.32 | Growth Patterns | MoM growth between milestones |
| A16.34 | Activation Personas | Fast/Slow/OneAndDone/Never |
| A16.36 | Branch Activation | Branch-level cohort activation |

#### Section 6: Executive Summary (A16.99)
Aggregates KPIs from above into a single summary slide.

**Pattern**: Each analysis follows:
```python
def _a16_1_total_accounts(ctx):
    data = ctx['data']
    ics_all = ctx['ics_all']
    # ... compute table ...
    _save(ctx, df_result, 'A16.1-Total ICS', 'Total ICS Accounts')
    _slide(ctx, 'A16.1', {...}, 'ICS')
    return ctx
```

**Charts**: Use matplotlib (matching ARS pipeline style), not Plotly. The ARS
DeckBuilder and chart export infrastructure already handle matplotlib PNGs.

---

### Session 2: Pipeline Wiring + Slide Reordering

**File**: `pipeline.py`

1. **Add `run_ics(ctx)` wrapper** (after `run_a15`):
   ```python
   def run_ics(ctx):
       if not ctx.get('has_ics'):
           _report(ctx, "   ICS columns not found -- skipping ICS analysis")
           return ctx
       from ics_product import run_ics_suite
       return run_ics_suite(ctx)
   ```

2. **Wire into `run_pipeline()`** (after Phase 3f):
   ```
   Phase 3g: run_ics(ctx)  -- ICS Product Review
   ```

3. **Slide reordering** in `_reorder_analysis_slides()`:
   - Add `'ICS'` category handling
   - Place ICS section after Value, before Mailer (or as its own appendix section)
   - Add ICS section divider slide

4. **app.py**: Remove `'coming_soon': True` from the ICS config entry.

---

### Session 3: Excel Export + Config

1. **Excel sheets**: Each A16.x analysis writes to the source + master workbooks
   using existing `save_to_excel()` infrastructure.

2. **clients_config.json**: Add optional ICS fields per client:
   ```json
   {
     "ICSEnabled": true,
     "ICSBalanceTiers": [0, 1000, 5000, 10000, 25000, 50000, 100000],
     "ICSAgeRanges": [0, 6, 12, 24, 36, 60],
     "ICSCohortStart": "2025-01"
   }
   ```
   These are optional -- sensible defaults when missing.

3. **Config loading**: Extract ICS config values into `ctx` during
   `step_load_config()`.

---

### Session 4: Testing + Validation

1. **Unit tests for `ics_product.py`**: Test each analysis function with
   synthetic data containing ICS columns. Follow existing test patterns.

2. **Integration test**: Run full pipeline with an ICS-annotated ODD file,
   verify PPTX has ICS section + slides, verify Excel has ICS sheets.

3. **Graceful degradation**: Verify pipeline still works when ODD has no
   ICS columns (existing behavior preserved).

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `pipeline.py` | Modify | ICS detection, subset creation, `run_ics()` wrapper, slide reordering |
| `ics_product.py` | Create | New module with 33 analyses ported from ics_analysis |
| `app.py` | Modify | Remove `coming_soon: True` for ICS |
| `clients_config.json` | Modify | Add optional ICS config fields |
| `tests/test_ics_product.py` | Create | Unit tests for ICS analyses |

---

## Dependencies

- `ics_append` must run first to produce the annotated ODD file
- The annotated ODD file replaces the standard ODD as pipeline input
- No new Python package dependencies (matplotlib, pandas, openpyxl already present)

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| ICS columns missing from ODD | `has_ics` gate skips all ICS analyses gracefully |
| Column name collision (`Source`) | Rename only on ICS subsets, not on raw data |
| Large PPTX (33 extra slides) | ICS section can be toggled via config flag |
| Inconsistent chart style | Use matplotlib (same as ARS), not Plotly |
| Performance | ICS subsets are small (~2-5K of ~50K rows), negligible overhead |

---

## Estimated Scope

- Session 0: ~50 lines (subset creation + detection)
- Session 1: ~400-500 lines (33 analyses, the bulk of the work)
- Session 2: ~80 lines (pipeline wiring + reordering)
- Session 3: ~40 lines (config + Excel)
- Session 4: ~200 lines (tests)

Total: ~800-900 lines of new code across 2 new files + modifications to 3 existing files.
