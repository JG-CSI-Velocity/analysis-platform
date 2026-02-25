# feat: Selectable Analysis Types in ARS Pipeline

**Status:** Implemented
**Type:** Enhancement
**Detail Level:** Comprehensive
**Created:** 2026-02-08

---

## Overview

Enable the ARS pipeline to run one or more analysis types (ARS, Transaction, ICS) in a single execution. Currently, `run_pipeline()` is monolithic -- it always runs every ARS suite (A1-A15) with no way to select subsets or combine with Transaction analysis. The Transaction module (`txn.py`) is fully coded but never called. ICS has zero implementation.

This plan introduces a suite selection mechanism so users can pick which analysis types to run, share the common setup phase, execute suites in proper sequence, and produce a single combined deck.

## Problem Statement

1. **No selection mechanism** -- `run_pipeline()` has no `selected_suites` parameter; it always runs all ARS phases
2. **Dead code** -- `txn.py:run_txn_suite(ctx)` (237 lines, 28 analyses) is never called from pipeline or UI
3. **analysis_type is decorative** -- `app.py` lets users pick a type via `st.radio`, stores it in session state, passes it to `run_single_client()`, but that function never forwards it to `run_pipeline()`
4. **No multi-select** -- `st.radio` only allows one selection at a time
5. **TXN slides unhandled** -- `_reorder_analysis_slides()` categorizes DCTR, Reg E, Attrition, Overview, Value, Mailer, but TXN slides (category='TXN') fall into the `other` bucket and are dumped at the end unsorted
6. **ExecutiveReport is ARS-only** -- no `set_txn()` or `set_ics()` methods; no sections for those types
7. **Transaction needs a CSV** -- unlike ARS (ODD xlsx only), Transaction analysis requires a separate transaction CSV file that must be located or specified

## Proposed Solution

### Architecture: Suite Registry + Conditional Orchestrator

Instead of a full rewrite, extend `run_pipeline()` with a `selected_types` parameter and gate each phase group behind a type check. A lightweight `SUITE_REGISTRY` dict in pipeline.py defines metadata for each type (phases, dependencies, required files).

```
run_pipeline(file_path, selected_types=['ars', 'transaction'], ...)
    |
    +-- Phase 1: Shared Setup (always runs)
    |     step_load_data, step_parse_and_paths, step_load_config,
    |     step_clean_data, step_date_range, step_create_subsets, step_setup_deck
    |
    +-- Phase 2: ARS Suites (if 'ars' in selected_types)
    |     A1-A5, A9, A6/A7, A8, A11, A12, A13/A14, A15
    |
    +-- Phase 3: Transaction Suite (if 'transaction' in selected_types)
    |     run_txn_suite(ctx)
    |
    +-- Phase 4: ICS Suite (if 'ics' in selected_types) -- future stub
    |
    +-- Phase 5: Shared Finalization (always runs)
          flush_workbooks, step_build_deck, step_archive_excel
```

### Key Design Decisions

1. **Extend, don't replace** -- `run_pipeline()` keeps its current structure; new code wraps existing phases in `if` guards
2. **Default = ARS only** -- `selected_types` defaults to `['ars']` so existing callers (CLI, batch) are unchanged
3. **Shared setup always runs** -- ODD data loading, config, date ranges, subsets, and deck builder are needed by all types
4. **TXN after ARS** -- Transaction analysis can benefit from ctx data populated by ARS (eligible accounts, date ranges), but also works standalone via its own data loader
5. **Combined deck** -- one PPTX with section dividers separating ARS and TXN sections

## Technical Approach

### Phase 1: Suite Registry + Pipeline Gating

**Files:** `pipeline.py`

#### 1a. Add SUITE_REGISTRY constant

```python
# pipeline.py (after imports, before create_context)

SUITE_REGISTRY = {
    'ars': {
        'label': 'ARS Monthly Analysis',
        'phases': ['a1_a5', 'attrition', 'dctr', 'reg_e', 'value',
                   'mailer_insights', 'mailer_response', 'market_impact'],
        'needs_odd': True,
        'needs_txn_csv': False,
    },
    'transaction': {
        'label': 'Transaction Analysis',
        'phases': ['txn'],
        'needs_odd': True,
        'needs_txn_csv': True,
    },
    'ics': {
        'label': 'ICS Analysis',
        'phases': ['ics'],
        'needs_odd': True,
        'needs_txn_csv': False,
        'coming_soon': True,
    },
}
```

#### 1b. Add `selected_types` parameter to `run_pipeline()`

```python
def run_pipeline(file_path, config_path=None, base_paths=None,
                 deck_builder_path=None, template_path=None,
                 progress_callback=None, exec_report=None,
                 selected_types=None, txn_data_folder=None):
    """
    Run the ARS pipeline with selectable analysis types.

    Parameters
    ----------
    selected_types : list[str] or None
        Which analysis types to run. Default: ['ars'].
        Valid values: 'ars', 'transaction', 'ics'.
    txn_data_folder : str or None
        Path to folder containing transaction CSV files.
        Required when 'transaction' in selected_types.
    """
    if selected_types is None:
        selected_types = ['ars']
    ctx['selected_types'] = selected_types
```

#### 1c. Gate ARS phases

Wrap existing phases A1-A15 in:

```python
if 'ars' in selected_types:
    # Phase 2: Analyses (A1-A5)
    ...existing code...
    # Phase 2b: Attrition (A9)
    ...existing code...
    # etc.
```

#### 1d. Add TXN phase after ARS

```python
if 'transaction' in selected_types:
    _report(ctx, "\n💳 Phase T: Transaction Analysis")
    try:
        if txn_data_folder:
            ctx['txn_data_folder'] = txn_data_folder
        from txn import run_txn_suite
        ctx = run_txn_suite(ctx)
        _report(ctx, "   Transaction suite complete")
        _exec_report(ctx, 'set_txn')
    except Exception as e:
        _report(ctx, f"   Transaction suite failed: {e}")
        _exec_report_fail(ctx, 'txn')
        traceback.print_exc()
    _phase_time(ctx, 'Transaction')
```

#### 1e. Add ICS stub

```python
if 'ics' in selected_types:
    _report(ctx, "\n🏦 Phase I: ICS Analysis")
    _report(ctx, "   ICS analysis not yet implemented -- skipping")
    _phase_time(ctx, 'ICS')
```

- [x] Add `SUITE_REGISTRY` constant to `pipeline.py`
- [x] Add `selected_types` and `txn_data_folder` params to `run_pipeline()`
- [x] Wrap ARS phases (A1-A5 through A15) in `if 'ars' in selected_types`
- [x] Add TXN phase block after ARS phases
- [x] Add ICS stub block after TXN phase
- [x] Fix circular import: inject `save_to_excel` into ctx before calling `run_txn_suite()`
- [x] Update `txn.py` to read `save_to_excel` from `ctx['_save_to_excel']` instead of importing from pipeline
- [x] Verify shared setup (Cells 1-16) always runs regardless of selection
- [x] Verify flush_workbooks + step_build_deck + step_archive always run

### Phase 2: Deck Consolidation for TXN Slides

**Files:** `pipeline.py` (`_reorder_analysis_slides`)

Currently, TXN slides (category='TXN') fall into the `other` list and get appended unsorted at the very end. This needs to handle them as a named section.

#### 2a. Add TXN bucket to `_reorder_analysis_slides()`

```python
# In the category sorting loop:
elif cat == 'TXN':
    txn_slides.append(s)
```

#### 2b. Insert TXN section divider + slides in deck order

After the ARS Summary section, before Appendix:

```python
if txn_slides:
    ordered.append(_section('Transaction Intelligence',
                            subtitle=section_subtitle))
    ordered.extend(txn_slides)
```

#### 2c. Optional: TXN consolidation merges

For now, no merge pairs for TXN (28 analyses produce individual slides). Can add `TXN_MERGES` later when patterns emerge.

- [x] Add `txn_slides = []` bucket in `_reorder_analysis_slides()`
- [x] Add `elif cat == 'TXN':` routing in the categorization loop
- [x] Insert TXN section divider and slides after ARS Summary, before Appendix
- [ ] Test: ARS-only deck unchanged (no TXN section appears)
- [ ] Test: ARS+TXN deck has Transaction Intelligence section
- [ ] Test: TXN-only deck has only Transaction Intelligence section

### Phase 3: UI Multi-Select

**Files:** `app.py`

#### 3a. Replace `st.radio` with `st.multiselect`

```python
# Sidebar analysis type selection
st.subheader("Analysis Type")

type_options = [k for k in ANALYSIS_TYPES if not ANALYSIS_TYPES[k].get('coming_soon')]
type_labels = {k: ANALYSIS_TYPES[k]['label'] for k in type_options}

selected_types = st.multiselect(
    "Select analyses to run",
    options=type_options,
    default=['ars'],
    format_func=lambda x: type_labels.get(x, x),
)

# Ensure at least one type is selected
if not selected_types:
    selected_types = ['ars']
    st.warning("At least one analysis type must be selected. Defaulting to ARS.")

st.session_state.selected_types = selected_types
```

#### 3b. Transaction data folder input (conditional)

Show a folder picker only when 'transaction' is selected:

```python
if 'transaction' in selected_types:
    st.divider()
    st.subheader("Transaction Data")
    txn_folder = st.text_input(
        "Transaction CSV Folder",
        value=st.session_state.get('txn_data_folder', ''),
        help="Folder containing transaction CSV files (auto-matches by client ID)",
    )
    st.session_state.txn_data_folder = txn_folder
```

#### 3c. Pass selected_types through to pipeline

Update `run_single_client()`:

```python
ctx = run_pipeline(
    file_path=fp,
    config_path=cfg_path,
    progress_callback=progress_cb,
    exec_report=exec_report,
    selected_types=st.session_state.get('selected_types', ['ars']),
    txn_data_folder=st.session_state.get('txn_data_folder'),
)
```

Update `run_batch()` similarly.

#### 3d. ICS "Coming Soon" indicator

In the sidebar, show ICS as disabled/info:

```python
# Show ICS as upcoming
for k, v in ANALYSIS_TYPES.items():
    if v.get('coming_soon'):
        st.caption(f"{v['label']} -- Coming Soon")
```

- [x] Replace `st.radio` with `st.multiselect` in sidebar
- [x] Add conditional transaction folder input
- [x] Update `run_single_client()` to pass `selected_types` and `txn_data_folder`
- [x] Update `run_batch()` to pass `selected_types` and `txn_data_folder`
- [x] Show ICS as "Coming Soon" indicator (not selectable)
- [x] Ensure empty selection defaults to `['ars']`
- [x] Remove `analysis_type` session state (replaced by `selected_types` list)

### Phase 4: Executive Report Extension

**Files:** `report_builder.py`

#### 4a. Add TXN section to report

Add a `set_txn()` method to `ExecutiveReport`:

```python
@_safe
def set_txn(self, ctx):
    """Populate transaction analysis section."""
    results = ctx.get('results', {})
    successful = sum(1 for k, v in results.items()
                     if k.startswith('txn_') and v.get('df') is not None
                     and not v['df'].empty)
    total = sum(1 for k in results if k.startswith('txn_'))
    self.sections['txn'] = {
        'title': 'Transaction Intelligence',
        'icon': 'credit_card',
        'status': 'complete',
        'metrics': {
            'Analyses': f'{successful}/{total}',
        },
    }
```

#### 4b. Add to PHASE_TO_SECTION mapping in app.py

```python
PHASE_TO_SECTION = {
    ...existing entries...
    'txn':              'txn',
}
```

#### 4c. Conditional sections

Only show report sections for selected types. The report should not show empty ARS sections when running TXN-only, and vice versa:

```python
# In set_portfolio, mark which types are active
self.selected_types = ctx.get('selected_types', ['ars'])
```

Then in `render_section()`, skip sections for unselected types.

- [x] Add `set_txn()` method to `ExecutiveReport`
- [x] Add TXN to `PHASE_TO_SECTION` mapping in `app.py`
- [x] Add `selected_types` awareness to report rendering
- [ ] Test: ARS-only run shows only ARS sections
- [ ] Test: ARS+TXN run shows all sections
- [ ] Test: TXN-only run shows portfolio + txn + build_summary

### Phase 5: Progress Detection for TXN

**Files:** `app.py`

The `detect_phase()` and `estimate_progress()` functions use keyword matching on pipeline log messages. They need to recognize TXN phases.

#### 5a. Update `detect_phase()`

Add TXN detection:

```python
# In detect_phase():
if 'transaction analysis' in m:
    return {'key': 'txn', 'label': 'Transaction', 'icon': 'credit_card'}
```

#### 5b. Update `estimate_progress()`

Adjust progress percentages based on selected types:

```python
# When ARS+TXN selected, TXN phases should be 85-94%
# When TXN-only, TXN phases should be 10-90%
('transaction analysis', 85),
('txn suite complete', 94),
```

For MVP, use fixed percentages that work reasonably for both single and combined runs.

- [x] Add TXN keywords to `detect_phase()`
- [x] Add TXN keywords to `estimate_progress()`
- [x] Test progress bar reflects TXN phases

## Edge Cases & Risks

### Circular Import: txn.py imports save_to_excel from pipeline.py
- `txn.py:124` does `from pipeline import save_to_excel`. When pipeline.py calls `run_txn_suite()`, this creates a circular import.
- **Fix**: Use the same ctx injection pattern from MEMORY.md (used for DCTR). Pipeline sets `ctx['_save_to_excel'] = save_to_excel` before calling `run_txn_suite(ctx)`, and txn.py reads it from ctx instead of importing.
- Add to Phase 1 implementation: inject `save_to_excel` into ctx, update txn.py to use `ctx['_save_to_excel']` instead of `from pipeline import save_to_excel`.

### Run Tracker Key Does Not Include Analysis Type
- `RunTracker._key()` generates `"{client_id}_{year}_{month}"`. If a user runs ARS Monday and Transaction Tuesday for the same client/month, the second run **overwrites** the first.
- **Fix for MVP**: Keep current key format but store `selected_types` list in the run entry (alongside existing `analysis_type` field). This avoids tracker format migration while preserving what was run.
- **Future**: Consider appending analysis type to key if independent tracking per type is needed.

### Transaction CSV Not Found
- `_find_txn_file(ctx)` already returns `None` gracefully and logs a skip message
- UI should pre-validate: if 'transaction' selected but no txn_data_folder configured and no CSV auto-discovered, show a warning before starting
- Pipeline should NOT fail if CSV is missing -- just skip TXN with a clear message

### ARS-Only Backward Compatibility
- `selected_types` defaults to `['ars']` -- zero behavior change for existing callers
- CLI (`python pipeline.py <file>`) unchanged
- Batch mode unchanged unless user selects multiple types in UI

### TXN-Only Run (No ARS)
- Shared setup still runs (ODD file loaded, config parsed, deck builder initialized)
- ARS phases skipped entirely
- TXN suite runs, uses ctx for chart_dir, source_folder, client_id, ic_rate
- Excel will have only TXN sheets
- Deck will have only Transaction Intelligence section
- Executive report shows portfolio + txn + build_summary

### Empty Results
- If all 28 TXN analyses return empty DataFrames, no slides are added
- Deck gracefully has no Transaction section (same pattern as DCTR/RegE guards)

### ICS Selection Attempt
- ICS is not in the multiselect options (filtered out by `coming_soon`)
- Shown as a "Coming Soon" caption below the multiselect
- If someone passes `ics` directly via CLI, the stub logs "not yet implemented"

### Concurrent Suites with Same ctx
- ARS and TXN both write to `ctx['results']` and `ctx['all_slides']`
- No conflict: ARS uses keys like `results['A1']`, TXN uses `results['txn_1']`
- Slides use different categories: 'Overview', 'DCTR', etc. vs 'TXN'
- Both use the same Excel workbook (ctx caching) -- sheets are namespaced (TXN- prefix)

### Deck Template
- Template has fixed preamble slides (title, agenda, etc.)
- Analysis slides are appended after preamble regardless of type
- Section dividers adapt automatically based on which sections have slides

## Acceptance Criteria

### Functional Requirements
- [ ] User can select one or more analysis types via multiselect in sidebar
- [ ] Pipeline runs only the selected types (ARS phases skipped when not selected)
- [ ] Transaction suite is callable and produces results when selected
- [ ] Combined ARS+TXN run produces a single deck with both sections
- [ ] TXN-only run produces a valid deck with Transaction Intelligence section
- [ ] ICS appears as "Coming Soon" and is not selectable
- [ ] Transaction data folder is configurable in UI when TXN is selected
- [ ] `run_pipeline()` defaults to ARS-only when called without `selected_types`

### Non-Functional Requirements
- [ ] No performance regression for ARS-only runs
- [ ] Executive report adapts sections to selected types
- [ ] Progress bar reflects all phases of selected types
- [ ] Batch mode supports multi-type selection

## Dependencies & Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| TXN analyses depend on data not in ctx | Low | Medium | `run_txn_suite` already has its own data loader |
| TXN charts don't match ARS chart style | Medium | Low | TXN uses its own chart settings; can align later |
| Progress percentages awkward for multi-type | Medium | Low | Use conservative fixed values for MVP |
| ICS implementation scope creep | Low | High | Hard-gated behind `coming_soon` flag |

## Implementation Sequence

1. **Phase 1** (Pipeline gating) -- highest value, enables everything else
2. **Phase 2** (Deck consolidation) -- needed for combined output
3. **Phase 3** (UI multi-select) -- user-facing entry point
4. **Phase 4** (Executive report) -- polish
5. **Phase 5** (Progress detection) -- polish

Phases 1-3 are the MVP. Phases 4-5 are refinements.

## Future Considerations

- **ICS implementation**: When ICS is ready, add `run_ics_suite(ctx)` following the same pattern as TXN, remove `coming_soon` flag, add to multiselect
- **TXN slide consolidation**: Once TXN slide patterns stabilize, add `TXN_MERGES` and `TXN_APPENDIX_IDS` for main/appendix splitting
- **Per-client type defaults**: Store preferred analysis types in `clients_config.json` so batch runs auto-select the right types per client
- **Parallel execution**: ARS and TXN could theoretically run in parallel (separate data), but adds complexity for minimal gain given current dataset sizes

## References

### Internal References
- `pipeline.py:1808` -- `run_pipeline()` signature and full phase sequence
- `pipeline.py:897` -- `_reorder_analysis_slides()` category routing
- `pipeline.py:1189` -- `step_build_deck()` with consolidation logic
- `txn.py:118` -- `run_txn_suite(ctx)` fully implemented but never called
- `txn.py:46` -- `_find_txn_file(ctx)` transaction CSV discovery logic
- `app.py:41` -- `ANALYSIS_TYPES` dict with ars/ics/transaction definitions
- `app.py:611` -- `run_single_client()` receives but ignores analysis_type
- `app.py:878` -- `st.radio` single selection (to become `st.multiselect`)
- `app.py:402` -- `PHASE_TO_SECTION` mapping
- `report_builder.py:228-586` -- `set_*()` methods (ARS only, no TXN)
