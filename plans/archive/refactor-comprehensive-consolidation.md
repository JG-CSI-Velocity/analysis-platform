# Comprehensive Consolidation Plan

**Type:** refactor
**Date:** 2026-02-23
**Scope:** Full monorepo audit -- consolidate, condense, remove, improve
**Codebase:** 246 files, 54,248 LOC, 2,609 tests, 5 packages

---

## Executive Summary

The analysis-platform monorepo works and ships. But after rapid porting of 3 repos into 1 monorepo, there is significant duplication, oversized files, and orphaned code. This plan targets **~4,000 LOC reduction** across 6 phases without changing any user-facing behavior.

---

## Phase 1: Extract `_safe()` into shared (12 copies -> 1)

**Impact:** -200 LOC, eliminates highest-count duplication in the codebase

The identical `_safe(fn, label, ctx)` wrapper is copy-pasted across 12 ARS analytics modules:

| File | Lines |
|------|-------|
| `dctr/branches.py` | 30 |
| `dctr/overlays.py` | 30 |
| `dctr/penetration.py` | 37 |
| `dctr/trends.py` | 25 |
| `dctr/funnel.py` | 22 |
| `rege/branches.py` | 30 |
| `rege/dimensions.py` | 31 |
| `rege/status.py` | 23 |
| `attrition/_helpers.py` | 169 |
| `mailer/_helpers.py` | 301 |
| `value/analysis.py` | 227 |
| `insights/_data.py` | 13 |

### Plan

- [ ] Create `shared.analytics.safe_run(_safe)` in `packages/shared/src/shared/analytics.py`
- [ ] Function signature: `_safe(fn: Callable, label: str, ctx: PipelineContext) -> list[AnalysisResult]`
- [ ] Replace all 12 local `_safe()` definitions with `from shared.analytics import safe_run`
- [ ] Keep the `_safe` name as a local alias if import readability matters
- [ ] Tests: Existing 2,609 tests cover all call sites; run full suite to confirm

### Risks
- None. All 12 copies are byte-identical in behavior (try/except, log, return `AnalysisResult(success=False)`)

---

## Phase 2: Consolidate color palettes (6 definitions -> 1)

**Impact:** -80 LOC, single source of truth for brand colors

Current state -- color palettes defined in 6 locations:

| Location | Variable | Purpose |
|----------|----------|---------|
| `shared/charts.py` | `COLORS` | Shared base palette |
| `txn_analysis/settings.py` | `BRAND_COLORS` | TXN brand |
| `txn_analysis/charts/theme.py` | `COLORS`, `COMPETITOR_COLORS`, `GENERATION_COLORS` | TXN charts |
| `ics_toolkit/settings.py` | `BRAND_COLORS` | ICS brand |
| `ics_toolkit/analysis/charts/style.py` | `PERSONA_COLORS` | ICS personas |
| `ics_toolkit/analysis/charts/renderer.py` | `COLORS` | ICS chart fallback |

### Plan

- [ ] Expand `shared/charts.py` to be the canonical color module:
  - `BRAND_COLORS: list[str]` -- primary ordered palette
  - `SEMANTIC_COLORS: dict[str, str]` -- named colors (positive, negative, neutral, etc.)
  - `COMPETITOR_COLORS: dict[str, str]` -- competitor categories
  - `GENERATION_COLORS: dict[str, str]` -- demographic bands
  - `PERSONA_COLORS: dict[str, str]` -- ICS persona mapping
- [ ] Update `txn_analysis/settings.py`, `ics_toolkit/settings.py`, `txn_analysis/charts/theme.py`, `ics_toolkit/analysis/charts/renderer.py` to import from `shared.charts`
- [ ] Remove duplicate definitions
- [ ] Run full test suite

### Risks
- Some TXN/ICS tests may assert specific hex values. Update assertions to use shared constants.

---

## Phase 3: Unify `chart_figure()` context manager

**Impact:** -40 LOC, consistent chart cleanup across all 3 pipelines

`chart_figure()` lives in `ars_analysis/charts/guards.py`. ICS has its own chart setup in `ics_toolkit/analysis/charts/renderer.py`. TXN uses raw `plt.figure()`.

### Plan

- [ ] Move `chart_figure()` from `ars_analysis/charts/guards.py` to `shared/charts.py`
- [ ] Keep the ARS import path working via re-export: `from shared.charts import chart_figure` in guards.py
- [ ] Adopt `chart_figure()` in ICS renderer (replace manual plt.figure + try/finally)
- [ ] Document in CLAUDE.md: "All chart creation must use `shared.charts.chart_figure()`"

### Risks
- ICS charts currently use a slightly different style setup. Test each ICS chart module after migration.

---

## Phase 4: Decompose `home.py` (1,325 lines -> ~5 files)

**Impact:** -0 LOC net (restructure), massive maintainability improvement

`home.py` is the highest-churn file (11 touches in 20 commits) and violates the 300-line rule by 4x. It contains: wizard UI, pipeline execution, progress display, result rendering, and session management.

### Plan

Split into focused modules under `pages/home/`:

| New file | Lines | Responsibility |
|----------|-------|----------------|
| `pages/home/__init__.py` | ~20 | Route entry, calls render() |
| `pages/home/wizard.py` | ~300 | 4-step wizard (data, modules, config, run) |
| `pages/home/executor.py` | ~250 | Pipeline execution + progress callbacks |
| `pages/home/results.py` | ~200 | Result display, charts, tables |
| `pages/home/session.py` | ~150 | Session state management |
| `pages/home/helpers.py` | ~100 | Shared helpers (_extract_progress, etc.) |

- [ ] Create `pages/home/` package directory
- [ ] Extract wizard steps (lines ~200-600) into `wizard.py`
- [ ] Extract execution loop (lines ~1000-1200) into `executor.py`
- [ ] Extract result rendering (lines ~700-950) into `results.py`
- [ ] Extract session state helpers into `session.py`
- [ ] Wire `__init__.py` to call the pieces
- [ ] Update imports in `app.py`
- [ ] Run platform tests

### Risks
- Streamlit session state is global; need to pass `st.session_state` explicitly to extracted functions
- Test coverage for platform_app is only ~21%; add integration tests for each extracted module

---

## Phase 5: Decompose `deck_builder.py` (1,413 lines -> ~4 files)

**Impact:** Maintainability improvement for the largest file in the codebase

### Plan

Split into focused modules under `output/deck/`:

| New file | Lines | Responsibility |
|----------|-------|----------------|
| `output/deck/__init__.py` | ~20 | Public API (build_deck) |
| `output/deck/builder.py` | ~300 | Main orchestrator |
| `output/deck/section_router.py` | ~200 | Section -> slide mapping |
| `output/deck/slide_builders.py` | ~400 | Individual slide construction |
| `output/deck/helpers.py` | ~150 | Image fitting, text formatting, placeholder map |

- [ ] Create `output/deck/` package
- [ ] Extract slide builders (divider, chart, table, kpi) into `slide_builders.py`
- [ ] Extract section routing logic into `section_router.py`
- [ ] Extract image fitting + text helpers into `helpers.py`
- [ ] Keep public `build_deck()` in `__init__.py`
- [ ] Update imports in CLI and runner
- [ ] Run ARS tests

---

## Phase 6: Remove dead code and stale plans

**Impact:** -500+ LOC, cleaner repo

### Dead code (already identified)

- [x] `pages/history.py` -- deleted in Issue #55
- [x] `components/client_selector.py` -- deleted in Issue #55
- [ ] Audit all `# TODO` / `# FIXME` comments -- resolve or delete
- [ ] Remove any unused imports flagged by ruff

### Stale plans

The `plans/` directory has 13 files, many from early phases that are now complete:

| Plan | Status | Action |
|------|--------|--------|
| `feat-ars-pipeline-roadmap.md` | Superseded by v2 | Archive |
| `feat-ars-pipeline-v2-revamp.md` | Complete (PR #4) | Archive |
| `feat-dctr-section-overhaul.md` | Complete | Archive |
| `feat-efficacy-stories-and-threads.md` | Complete | Archive |
| `feat-ics-product-review.md` | Complete (PR #9) | Archive |
| `feat-market-impact-visuals.md` | Complete | Archive |
| `feat-selectable-analysis-types.md` | Superseded | Archive |
| `feat-team-reporting-platform.md` | Active | Keep |
| `fix-mailer-summary-slide-refinements.md` | Complete | Archive |
| `fix-output-quality-and-performance.md` | In progress | Keep |
| `fix-txn-pipeline-broken-wiring.md` | In progress | Keep |
| `review-impact-analysis.md` | Reference | Archive |
| `strategic-insights-analysis.md` | Reference | Archive |

- [ ] Move completed/superseded plans to `plans/archive/`
- [ ] Keep 3-4 active plans in `plans/`

### Stale plans in repo

| Plan | Action |
|------|--------|
| `plans/feat-rebrand-rpe-and-platform-improvements.md` | Review status |
| `plans/refactor-unified-deck-consolidation.md` | Active -- keep |
| `plans/feat-improve-analysis-output-quality.md` | Review status |
| `plans/DEPLOYMENT-CHECKLIST-RPE-REBRAND.md` | Active -- keep |

- [ ] Review each in-repo plan, archive completed ones

---

## Phase 7: Decompose TXN storyline monoliths (4 files, 3,938 LOC)

**Impact:** -0 LOC net (restructure), aligns with 300-line coding standard

These 4 TXN storyline files all exceed 835 lines:

| File | Lines |
|------|-------|
| `v4_s7_campaigns.py` | 1,296 |
| `v4_s5_demographics.py` | 907 |
| `v4_s8_payroll.py` | 900 |
| `v4_s9_lifecycle.py` | 835 |

### Plan

For each file, split into `{storyline}/` package:

```
storylines/campaigns/
    __init__.py          # public API
    channel_analysis.py  # M7.1-M7.4
    response_metrics.py  # M7.5-M7.8
    helpers.py           # shared within storyline
```

- [ ] `v4_s7_campaigns.py` -> `storylines/campaigns/` (3 files)
- [ ] `v4_s5_demographics.py` -> `storylines/demographics/` (3 files)
- [ ] `v4_s8_payroll.py` -> `storylines/payroll/` (3 files)
- [ ] `v4_s9_lifecycle.py` -> `storylines/lifecycle/` (3 files)
- [ ] Update imports in TXN runner and tests
- [ ] Run TXN tests

### Risks
- These modules are stable and working. Only decompose if we need to modify them.
- CLAUDE.md marks Phase 5 (storyline decomposition) as "optional" -- user may defer.

---

## Phase 8: Improve test coverage and CI

**Impact:** Prevent regressions, catch bugs earlier

### Coverage gaps

| Package | Current | Target |
|---------|---------|--------|
| platform_app | ~21% | 60% |
| ars_analysis | ~90% | 90% (maintain) |
| txn_analysis | ~85% | 85% (maintain) |
| ics_toolkit | ~95% | 95% (maintain) |
| shared | ~80% | 85% |

### Plan

- [ ] Add tests for `home.py` execution paths (after Phase 4 decomposition)
- [ ] Add tests for `app.py` navigation routing
- [ ] Add tests for `module_library.py` filter/search logic
- [ ] Add tests for deck builder section routing (after Phase 5 decomposition)
- [ ] Verify CI coverage floor is enforced per-package, not just global

---

## Phase 9: Version pinning and dependency hygiene

**Impact:** Reproducible builds, prevent surprise breakage

### Current state

- `ars_analysis` and `shared`: Strict version bounds (good)
- `txn_analysis` and `ics_toolkit`: Loose bounds like `pandas>=2.0` (risky)
- `kaleido==0.2.1` pinned everywhere (correct -- v1.0+ has 50x regression)

### Plan

- [ ] Align all 4 packages to same version bound style: `>=2.x,<3`
- [ ] Pin `matplotlib`, `openpyxl`, `python-pptx` to tested ranges
- [ ] Add `uv lock --check` to CI to catch drift
- [ ] Document pinning policy in CLAUDE.md

---

## Phase 10: Column alias resolution (recurring bug pattern)

**Impact:** Prevent the #1 recurring bug category (6 fix commits in history)

Column naming varies across ODD files: `"Product Code"` vs `"Prod Code"`, `"ICS Source"` vs `"Source"`, `"Acct Hash"` vs `"Account Hash"`. This has caused 6+ bugs.

### Plan

- [ ] Create `shared/columns.py` with a `resolve_column(df, canonical, aliases)` function
- [ ] Define alias maps for known columns:
  ```python
  COLUMN_ALIASES = {
      "Product Code": ["Prod Code", "Product"],
      "ICS Account": ["ICS Acct", "ICS_Account"],
      "ICS Source": ["Source", "ICS_Source"],
      "Account Hash": ["Acct Hash", "AcctHash"],
  }
  ```
- [ ] Replace scattered `if "Prod Code" in df.columns` / `product_col()` checks with `resolve_column()`
- [ ] Add validation: warn if an expected column is missing AND no alias found
- [ ] Run full test suite

---

## Implementation Priority

| Phase | Effort | Impact | Priority |
|-------|--------|--------|----------|
| 1. Extract `_safe()` | Small (1h) | High -- 12 copies eliminated | P0 |
| 2. Color palettes | Small (1h) | Medium -- single source of truth | P0 |
| 3. `chart_figure()` | Small (30m) | Medium -- consistent cleanup | P0 |
| 6. Dead code + stale plans | Small (30m) | Medium -- repo hygiene | P0 |
| 10. Column aliases | Medium (2h) | High -- prevents recurring bugs | P1 |
| 4. Decompose `home.py` | Medium (3h) | High -- highest-churn file | P1 |
| 5. Decompose `deck_builder.py` | Medium (3h) | Medium -- largest file | P2 |
| 8. Test coverage | Medium (3h) | High -- platform_app at 21% | P2 |
| 9. Version pinning | Small (1h) | Medium -- reproducible builds | P2 |
| 7. TXN storylines | Large (4h) | Low -- stable, optional | P3 |

**Recommended execution order:** Phases 1-3 + 6 (quick wins, 3h total), then 10 + 4 (highest impact, 5h), then 5 + 8 + 9 (medium priority, 7h), then 7 (deferred).

---

## Verification

After each phase:
```bash
uv run pytest -q                     # 2,609 tests pass
uv run ruff check packages/          # lint clean
uv run ruff format --check packages/ # format clean
```

After all phases:
```bash
make cov                             # coverage >= 80% per package
```

---

## Files Summary

| Phase | Files modified | Files created | Files deleted |
|-------|---------------|---------------|---------------|
| 1 | 12 ARS modules | 1 (`shared/analytics.py`) | 0 |
| 2 | 6 color files | 0 | 0 |
| 3 | 3 chart files | 0 | 0 |
| 4 | 2 (`home.py`, `app.py`) | 6 (`pages/home/*.py`) | 0 |
| 5 | 2 (`deck_builder.py`, `cli.py`) | 5 (`output/deck/*.py`) | 0 |
| 6 | ~5 (TODO cleanup) | 1 (`plans/archive/`) | ~10 stale plans moved |
| 7 | 4 TXN storylines | 12 (`storylines/{name}/*.py`) | 0 |
| 8 | ~8 test files | ~4 new test files | 0 |
| 9 | 4 `pyproject.toml` | 0 | 0 |
| 10 | ~8 analytics modules | 1 (`shared/columns.py`) | 0 |
