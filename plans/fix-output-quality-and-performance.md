# Fix: ARS Output Quality + Streamlit Performance

**Type:** fix
**Status:** Draft
**Date:** 2026-02-13
**Scope:** ARS first, then ICS/TXN

---

## Problem Statement

The ARS pipeline produces 70+ slides but real-client output has three categories of issues:

1. **Mailer slides incomplete** -- A12/A13/A14/A15 slides have sparse or missing data
2. **Funnels broken** -- DCTR funnel charts (A7.7/A7.8/A7.9) rendering incorrectly
3. **Streamlit lag** -- every click causes full page rerun; file detection + Excel reads on every interaction

**Root causes identified:**

| Issue | Root Cause | Evidence |
|-------|-----------|----------|
| Mailer incomplete | Failed results silently dropped (`_result_to_slide` returns None on success=False) | `deck_builder.py:960-961` |
| Mailer incomplete | Column discovery finds 0 pairs if naming differs from expected pattern | `mailer/_helpers.py:86-117` |
| Mailer incomplete | No visibility into which slides failed vs skipped | No validation report exists |
| Funnels broken | Data subsets may filter to 0 rows if config (stat codes) not loaded | `runner.py:78` + config path issue |
| Funnels broken | Proportional funnel sizing breaks with extreme ratios | `dctr/funnel.py:289-549` |
| Streamlit lag | `check_odd_formatted` + `check_ics_ready` read Excel on every rerun | `home.py` (partially fixed with cache) |
| Streamlit lag | No `st.fragment()` usage; entire page reruns | Streamlit 1.33+ feature not used |

---

## Architecture Context

### How slides flow from module to deck

```
Module.run(ctx)
  -> AnalysisResult(success, slide_id, chart_path, excel_data, title, notes)
  -> appended to ctx.all_slides

step_generate(ctx)
  -> _write_excel(): iterates ctx.all_slides, writes sheets from excel_data
  -> _build_deck(): calls build_deck(ctx)

build_deck(ctx)
  -> _group_by_section(): groups all_slides by section tag
  -> _convert_list(): calls _result_to_slide() per result
  -> _result_to_slide(): returns None if success=False OR chart missing
  -> Silent drop: slide simply doesn't appear in final deck
```

**Key finding:** Failed modules produce invisible gaps, not blank slides. The user sees fewer slides but no indication of what failed or why.

### Files involved

| File | Lines | Role |
|------|-------|------|
| `analytics/mailer/_helpers.py` | 213 | Column discovery, segment analysis |
| `analytics/mailer/insights.py` | 366 | A12 slides (per-month swipes/spend) |
| `analytics/mailer/response.py` | 641 | A13 + A14 slides (response summaries) |
| `analytics/mailer/impact.py` | 815 | A15 slides (market reach, revenue) |
| `analytics/dctr/funnel.py` | 549 | A7.7/A7.8/A7.9 funnels |
| `output/deck_builder.py` | 1162 | PPTX construction + consolidation |
| `output/excel_formatter.py` | 161 | Excel formatting + summary sheet |
| `pipeline/steps/generate.py` | 126 | Orchestrates Excel + PPTX generation |
| `pipeline/steps/analyze.py` | ~120 | Sequential module execution |
| `platform_app/pages/home.py` | ~500 | Streamlit UI |

---

## Phase 1: Output Validation & Diagnostics

**Goal:** See exactly what's failing before fixing anything. Add a run report that shows which slides succeeded, failed, or had no data.

### 1.1 Add `RunReport` to step_generate

After all modules run, before deck build, produce a diagnostic summary:

```python
# pipeline/steps/generate.py

@dataclass
class SlideStatus:
    slide_id: str
    module_id: str
    success: bool
    has_chart: bool
    has_excel: bool
    error: str = ""
    row_count: int = 0   # rows in source data for this analysis

def _build_run_report(ctx) -> list[SlideStatus]:
    report = []
    for result in ctx.all_slides:
        report.append(SlideStatus(
            slide_id=result.slide_id,
            module_id=result.module_id if hasattr(result, 'module_id') else '',
            success=result.success,
            has_chart=bool(result.chart_path and Path(result.chart_path).exists()),
            has_excel=bool(result.excel_data),
            error=result.error or '',
        ))
    return report
```

- [x] Add `SlideStatus` dataclass to `generate.py`
- [x] Call `_build_run_report()` after analyze, before deck build
- [x] Log summary: `"Run report: 58/70 slides OK, 8 failed, 4 no chart"`
- [x] Save report as JSON next to output files
- [x] Surface report in Streamlit UI (collapsible after run)

### 1.2 Show run report in Streamlit

After pipeline completes, show a table:

```
Slide       Status   Chart  Excel  Error
A7.7        OK       Yes    Yes
A7.8        OK       Yes    Yes
A12.Aug25   FAIL     No     No     No mail columns found
A13.Aug25   FAIL     No     No     discover_pairs returned 0 pairs
A15.1       FAIL     No     No     No eligible_with_debit subset
```

- [x] Parse run report JSON in `home.py` after run completes
- [x] Display as `st.dataframe` inside expandable "Run Report" section
- [x] Color-code: green=OK, red=FAIL, yellow=partial (chart but no excel or vice versa)

---

## Phase 2: Fix Mailer Output (A12-A15)

**Goal:** Mailer slides produce complete data for real client files.

### 2.1 Diagnose column discovery

The most likely cause of incomplete mailer output. `discover_pairs()` matches:
- `{Mon}{YY} Mail` + `{Mon}{YY} Resp` (e.g. "Aug25 Mail", "Aug25 Resp")
- If real data uses different naming, 0 pairs are found and all mailer modules produce 0 slides.

```python
# mailer/_helpers.py:86-117
MAIL_PATTERN = re.compile(r"^([A-Z][a-z]{2}\d{2})\s+Mail$")
RESP_PATTERN = re.compile(r"^([A-Z][a-z]{2}\d{2})\s+Resp$")
```

- [x] Add logging to `discover_pairs()`: log all column names, which matched, which didn't
- [x] If 0 pairs found, log an explicit warning with the columns that ALMOST matched
- [x] Add fuzzy matching fallback: case-insensitive, with/without spaces, common variants
- [ ] Test with real client ODD column headers (need user to provide sample column list)

### 2.2 Handle missing mailer data gracefully

When mailer modules produce `success=False`, the deck builder silently drops them. This is correct behavior (don't render broken charts), but the user needs visibility.

- [x] In each mailer sub-module's `_safe()` wrapper, log the specific failure reason
- [x] Store failure reasons in `ctx.results["_mailer_errors"]` for the run report
- [x] If `discover_pairs()` returns 0 pairs, produce ONE result with `success=False` + descriptive error (not just silently return empty list)

### 2.3 Fix mailer insights (A12) data completeness

Check that `_calc_nu_metrics()` and `_calc_th_metrics()` produce valid DataFrames:

- [ ] Verify NU 5+ responder mask works with real data response values
- [ ] Verify TH segment matching uses exact config values, not hardcoded
- [ ] Check that Spend/Swipes columns are found by `discover_metric_cols()`
- [ ] Add `row_count` to each `AnalysisResult` for diagnostics

### 2.4 Fix mailer response (A13) summaries

A13 monthly summaries create composite charts (donut + bar). If segment data is empty, chart renders with no visible content.

- [ ] Add minimum data threshold: if total_mailed < 5, skip month with warning
- [ ] Verify `_monthly_summaries()` handles months with 0 responders
- [ ] Check `_count_trend()` and `_rate_trend()` with single-month data (needs 2+ for trend)

### 2.5 Fix mailer impact (A15)

A15.1-A15.4 depend on upstream data:
- `ctx.results.get("eligible_with_debit")` (from subsets step)
- `ctx.client.ic_rate` (from config)

- [ ] A15.1 market reach: verify `eligible_with_debit` subset exists and has rows
- [ ] A15.3 revenue attribution: already skips when `ic_rate == 0` -- verify config loads correctly
- [ ] A15.4 pre/post delta: verify spend columns exist for pre-mail baseline months

---

## Phase 3: Fix DCTR Funnels (A7.7-A7.9)

**Goal:** Funnels render correctly with proper proportions and data.

### 3.1 Diagnose funnel data

The funnel uses 4 stages: Total -> Open -> Eligible -> With Debit.
"Ruined" likely means proportions are wrong or chart layout is broken.

- [x] Log funnel stage counts: `Total={n}, Open={n}, Eligible={n}, Debit={n}`
- [ ] Check if `EligibleStatusCodes` from config correctly filters to "open" accounts
- [ ] Verify `EligibleProductCodes` doesn't filter out too many accounts
- [ ] Compare funnel counts between old jupyter pipeline and new modular pipeline (same input file)

### 3.2 Fix funnel drawing

`_draw_funnel()` (549 lines) draws proportional boxes. Issues arise when:
- Stage counts have extreme ratios (e.g., 10000 total, 3 eligible)
- Personal/Business split has 0 in one category
- Label positioning overlaps with small boxes

- [x] Add minimum box height (don't collapse to invisible)
- [ ] Handle 0 accounts in P or B split without crashing
- [ ] Test funnel with real client data ratios
- [ ] Compare visual output to the old jupyter-generated funnel charts

### 3.3 Fix L12M funnel (A7.8)

A7.8 uses `filter_l12m()` which depends on `ctx.start_date` and `ctx.end_date`. If dates aren't set, the filter may return all data or empty data.

- [x] Verify `start_date`/`end_date` are set correctly in subsets step
- [x] Log L12M date range and row count after filtering
- [x] Handle case where L12M filter returns 0 rows (skip A7.8 with message, not crash)

---

## Phase 4: Streamlit Performance

**Goal:** Eliminate lag. Clicks should respond instantly.

### 4.1 Use `st.fragment()` for Step 1

Step 1 (client selection) triggers reruns on every dropdown change. Wrap it in a fragment so only the selection area reruns.

```python
@st.fragment
def step_1_client_selection():
    # CSM / Month / Client dropdowns
    # File detection (cached)
    # Badges
    ...
```

- [ ] Wrap Step 1 in `@st.fragment`
- [ ] Keep cached file detection inside fragment
- [ ] Store selected values in `st.session_state` for downstream access

### 4.2 Use `st.fragment()` for Step 2

Template buttons and TOC tabs currently trigger full page reruns.

```python
@st.fragment
def step_2_select_analysis():
    # Template buttons
    # Module TOC tabs
    ...
```

- [ ] Wrap Step 2 in `@st.fragment`
- [ ] Template selection stays in session_state
- [ ] Module list updates based on available data (from Step 1 state)

### 4.3 Optimize remaining expensive operations

- [x] `load_templates()` -- wrap in `@st.cache_data` (reads YAML once)
- [x] `get_registry()` -- already cached in-process via `_CACHED_REGISTRY`
- [ ] `load_raw_client_entry()` -- already fast but wrap in `@st.cache_data(ttl=300)` for network drive
- [x] `discover_csm_folders()` / `discover_months()` / `discover_clients()` -- wrap in `@st.cache_data(ttl=60)`

### 4.4 Reduce UI widget count

Each `st.markdown(unsafe_allow_html=True)` adds rendering overhead. Batch multiple badge/label renders into single HTML blocks.

- [x] Combine Step 3 pre-flight metrics into single `st.markdown` call (already done)
- [ ] Batch module TOC items into single HTML per tab instead of per-module `st.markdown`

---

## Phase 5: Shared Output Framework (Scale to ICS/TXN)

**Goal:** The same validation, reporting, and deck-building patterns work for all 3 pipelines.

### 5.1 Shared `RunReport`

- [ ] Move `SlideStatus` / `RunReport` to `shared.types`
- [ ] All three runners (ARS, ICS, TXN) populate `ctx.run_report`
- [ ] Streamlit displays unified report regardless of pipeline

### 5.2 ICS output review

ICS pipeline has its own deck builder and 37 analyses. Apply same patterns:

- [ ] Add run report generation to ICS runner
- [ ] Verify ICS deck builder handles `success=False` results (skip vs blank)
- [ ] Add column validation for ICS-specific columns ("ICS Account", "ICS Source")

### 5.3 TXN output review

TXN pipeline has 35 analyses (M1-M14 + scorecard). Apply same patterns:

- [ ] Add run report generation to TXN runner
- [ ] Verify TXN chart generation handles edge cases
- [ ] Add transaction file column validation

---

## Verification

```bash
# After each phase:
uv run pytest tests/ars/ -q
uv run pytest tests/platform/ -q
uv run pytest tests/integration/ -q
uv run ruff check packages/
```

### Phase 1 verification
- [ ] Run report JSON generated alongside output files
- [ ] Run report displayed in Streamlit after run
- [ ] Failed slides show specific error messages

### Phase 2 verification
- [ ] Mailer slides appear in deck when mail columns exist in ODD
- [ ] `discover_pairs()` logs which columns matched
- [ ] 0-pair discovery produces explicit error in run report
- [ ] A15.3 works when IC rate is configured

### Phase 3 verification
- [ ] Funnel charts render with correct proportions
- [ ] L12M funnel uses correct date range
- [ ] Funnel handles extreme ratios gracefully

### Phase 4 verification
- [ ] Dropdown clicks respond in < 200ms
- [ ] Template selection doesn't trigger full page rerun
- [ ] Run button executes pipeline (not just reload)
- [ ] File detection cached across interactions

### Phase 5 verification
- [ ] ICS pipeline produces run report
- [ ] TXN pipeline produces run report
- [ ] Streamlit shows unified report for any pipeline

---

## Execution Order

| Order | Phase | Effort | Impact |
|-------|-------|--------|--------|
| 1 | Phase 1 (diagnostics) | Small | Unblocks all other phases |
| 2 | Phase 2 (mailer) | Medium | Fixes most-reported issue |
| 3 | Phase 3 (funnels) | Small | Fixes second-reported issue |
| 4 | Phase 4 (performance) | Medium | Fixes lag |
| 5 | Phase 5 (scale) | Medium | Future-proofs |

**Recommendation:** Start Phase 1 immediately -- the run report will tell us exactly which slides are failing and why, which focuses Phase 2+3 work.
