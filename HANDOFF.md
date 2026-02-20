# CSI Velocity -- Repository Roadmap & Session Handoff

**Date:** 2026-02-07
**Repo:** `JG-CSI-Velocity/analysis-platform`
**Location:** `/Users/jgmbp/Desktop/analysis_platform/`
**Current branch:** `feat/platform-enhancement` (PR #17)
**Working tree:** 7 modified files + 1 untracked (this file) -- NOT YET COMMITTED

---

## 1. What Was Handed To Me

The user provided a comprehensive CSI Velocity Repository Roadmap covering:

- **Monorepo state:** 5-package uv workspace (`shared`, `ars_analysis`, `txn_analysis`, `ics_toolkit`, `platform_app`)
- **Problem:** Two completely independent transaction analysis systems existed in `txn_analysis` -- a main pipeline (M1-M10, ~2,000 LOC) and a V4 pipeline (S1-S9, ~12,200 LOC) with 60% overlap and zero shared code
- **V4 consolidation plan:** 5-phase plan to kill V4, keep unique analyses, merge infrastructure (already approved, Phases 1-4 committed in `7de644e`)
- **5-tier roadmap:** Stabilize -> Coverage -> Architecture -> Features -> Polish
- **Open PRs:** #17 (V4 consolidation), #18 (ARS CLI fix)
- **Open issues:** 1 on monorepo (#14), 6 on txn-analysis (standalone), 1 on ars-pipeline (standalone)
- **Standalone repos:** txn-analysis, ars-pipeline, ics-analysis, ics-append (all superseded by monorepo)
- **Test suite:** 2,318 tests, 89% coverage, CI floor 80%

The handoff asked me to: complete Phase 5, ensure consistency, update docs, and produce a handoff summary.

---

## 2. What I Did This Session

### 2a. Completed V4 Consolidation Phase 5 (prior session, committed in `7de644e`)

Phase 5 was the final cleanup -- delete overlapping storylines and purge all `txn_v4` references from the platform app layer.

**Deleted 8 files (5,743 LOC removed):**

| File | LOC | Replacement |
|------|-----|-------------|
| `storylines/v4_s1_portfolio_health.py` | 949 | M1-M5, scorecard |
| `storylines/v4_s2_merchant_intel.py` | 1,269 | M1-M5 |
| `storylines/v4_s3_competition.py` | 690 | M6 competitor_* |
| `storylines/v4_s3_threat_analysis.py` | 507 | M6 competitor_threat |
| `storylines/v4_s3_segmentation.py` | 570 | M6 competitor_segment |
| `storylines/v4_s4_finserv.py` | 797 | M7 financial_services |
| `storylines/v4_s6_risk.py` | 468 | M8-M10 |
| `v4_data_loader.py` | 493 | Merged into `data_loader.py` |

**Purged `txn_v4` from platform_app (6 files):**

| File | Change |
|------|--------|
| `orchestrator.py` | Removed `"txn_v4"` from `PIPELINE_NAMES`, simplified detection logic |
| `components.py` | Removed `txn_v4` from pipeline selector and `PIPELINE_FILE_ROLES` |
| `cli.py` | Updated help text, simplified `_build_input_files` |
| `module_registry.py` | Removed `Product.TXN_V4` enum, removed `_V4_STORYLINES` list, added M11-M14 to `_TXN_MODULES` |
| `session_manager.py` | `pipelines.extend(["txn", "txn_v4"])` -> `pipelines.append("txn")` |
| `dashboard.py` | Removed `txn_v4` from counter |

**Updated tests (4 files):**

| File | Change |
|------|--------|
| `test_v4_storyline_runners.py` | Removed S1-S4/S6 test classes, kept S5/S7/S8/S9 |
| `test_v4_data_loader.py` | Rewired imports from `v4_data_loader` -> `data_loader`, removed `TestLoadConfig` |
| `test_orchestrator.py` | Updated `PIPELINE_NAMES` assertions, renamed tests |
| `test_cli.py`, `test_components.py` | Removed `txn_v4` references |

### 2b. Fixed Streamlit UI Crash (this session -- UNCOMMITTED)

Discovered 3 Streamlit pages were crashing because they still referenced `Product.TXN_V4` which was removed from the enum in Phase 5.

**Fixed 7 files:**

| File | Change |
|------|--------|
| `pages/home.py` | Removed V4 product card (4 cols -> 3), updated TXN desc to "M1-M14 + scorecard" |
| `pages/module_library.py` | Removed `Product.TXN_V4` from `_COLORS` dict |
| `pages/run_analysis.py` | Removed `Product.TXN_V4` refs, added ODD file passthrough to TXN pipeline |
| `pages/data_ingestion.py` | Added ODD file upload/path input under Transaction tab (enables M11-M14) |
| `pages/batch_workflow.py` | "Transaction Base" -> "Transaction Analysis", added ODD file input, passes ODD to TXN |
| `core/templates.py` | Replaced dead `"V4 Full Storyline"` template (v4_s0-s9 keys) with `"TXN Full Suite"` (all 35 real module keys) |
| `CLAUDE.md` | Updated session pickup section |

**Verification:** 2,305 tests pass (excludes 13 pre-existing ARS collection failures), lint clean, 89% coverage.

---

## 3. Current State (verified 2026-02-07)

### Repository Map

```
analysis_platform/                    GitHub: JG-CSI-Velocity/analysis-platform
  packages/
    shared/           640 LOC    Shared types, context, config, chart utils
    ars_analysis/     14,933 LOC ARS pipeline (70+ analyses, PPTX deck)
    txn_analysis/     10,158 LOC Transaction pipeline (35 analyses: M1-M14 + scorecard)
    ics_toolkit/      14,706 LOC ICS pipeline (37 analyses + append + referral)
    platform_app/     4,271 LOC  Orchestrator, Typer CLI, Streamlit UI
  tests/
    shared/           50 tests
    ars/              545 collected (13 fail to collect -- pydantic_settings dep)
    txn/              597 tests
    ics/              1,049 tests (incl. referral: 212)
    platform/         60 tests
    integration/      17 tests
```

### Numbers

| Metric | Value |
|--------|-------|
| Source LOC | 44,708 |
| Test LOC | 21,854 |
| Total tests collected | 2,318 |
| Tests passing | 2,305 (13 ARS pre-existing failures) |
| Coverage | 89% (16,018 stmts, 1,737 missed) |
| CI floor | 80% (`--cov-fail-under=80`) |
| Test time | ~2 min |
| Lint | Clean (ruff check + ruff format) |
| Warnings | 2,443 (all kaleido deprecation -- harmless) |

### Open PRs

| # | Branch | Title | Status |
|---|--------|-------|--------|
| 17 | `feat/platform-enhancement` | V4 Consolidation + 186 new tests | OPEN, ready to merge (CURRENT) |
| 18 | `chore/consolidate-moving-parts` | ARS CLI crash fix + docs | OPEN, ready to merge |

### Open Issues

**analysis-platform (monorepo):**

| # | Title | Notes |
|---|-------|-------|
| 14 | Platform App: Wire Pipeline Execution | Tier 4.1 -- biggest remaining feature |

**txn-analysis (standalone -- superseded by monorepo):**

| # | Title | Disposition |
|---|-------|-------------|
| 5 | improve dupe id | CLOSE after PR #17 merge -- covered by consolidated merchant_rules |
| 6 | merchant top 50 spend | CLOSE after PR #17 merge -- covered by M1-M5 |
| 10 | config | MIGRATE to monorepo -- config enhancement request |
| 11 | ch - viz - comp heavy spend | CLOSE after PR #17 merge -- covered by M6 competitor_* |
| 13 | merge competition | MIGRATE to monorepo -- competitor merge logic |
| 16 | comp spend by account | CLOSE after PR #17 merge -- covered by M6 competitor_* |

**ars-pipeline (standalone):**

| # | Title | Disposition |
|---|-------|-------------|
| 10 | 2.17 run issue | INVESTIGATE -- production file path bug, may affect monorepo ARS too |

**ics-analysis, ics-append:** 0 open issues each.

### Standalone Repos

| Repo | Monorepo Package | Status |
|------|-----------------|--------|
| `txn-analysis` | `txn_analysis` | Superseded, 6 open issues (4 close, 2 migrate) |
| `ars-pipeline` | `ars_analysis` | Superseded, 1 open issue (production bug) |
| `ics-analysis` | `ics_toolkit` | Superseded, clean |
| `ics-append` | `ics_toolkit` | Superseded, clean |
| `ils_kickoff_day2` | NOT in monorepo | Standalone OD/NSF tool, 75 tests, 91% coverage |

### Branches

| Branch | Status | Action |
|--------|--------|--------|
| `main` | Behind | Merge PRs #18 then #17 into this |
| `feat/platform-enhancement` | CURRENT, PR #17 | Has uncommitted UI fixes (7 files) |
| `chore/consolidate-moving-parts` | PR #18 | Ready to merge as-is |
| `feat/v4-consolidation` | Stale | DELETE after PR #17 merges |
| `test/close-coverage-gaps` | Stale | DELETE |
| `feat/referral-intelligence-engine` | Already merged | DELETE |
| `feat/streamlit-ui` | Already merged | DELETE |

---

## 4. Architecture

### Pipeline Pattern (all 3 pipelines)

```
Settings (Pydantic) -> data_loader.load_data() -> run_all_analyses() -> export_outputs()
                                                        |
                                                  ANALYSIS_REGISTRY
                                                  [(name, fn), ...]
                                                        |
                                              Each fn(df, biz_df, per_df, settings, ctx)
                                                        |
                                                  -> AnalysisResult
```

### TXN ANALYSIS_REGISTRY (35 analyses)

```
M1:  top_merchants_by_spend, by_transactions, by_accounts    (Overall)
M2:  mcc_by_accounts, by_transactions, by_spend              (MCC)
M3:  business_top_by_spend, by_transactions, by_accounts     (Business)
M4:  personal_top_by_spend, by_transactions, by_accounts     (Personal)
M5:  monthly_rank_tracking, growth_leaders, consistency,      (Trends)
     new_vs_declining, business_movers, personal_movers
M6:  competitor_detection -> high_level, top_20, categories,  (Competitor)
     biz_personal, monthly_trends, threat, segmentation
M7:  financial_services_detection -> summary                  (Financial)
M8:  interchange_summary                                      (Revenue)
M10: member_segments                                          (Segmentation)
M11: demographics        <- storyline adapter (requires ODD)  (Demographics)
M12: campaigns           <- storyline adapter (requires ODD)  (Campaigns)
M13: payroll             <- storyline adapter                 (Payroll)
M14: lifecycle           <- storyline adapter (requires ODD)  (Lifecycle)
M9:  portfolio_scorecard <- MUST BE LAST                      (Scorecard)
```

M11-M14 are thin adapters in `analyses/storyline_adapters.py` that wrap the kept V4 storyline modules (S5/S7/S8/S9). They convert pipeline args to V4 context dict and wrap results back to AnalysisResult. Lazy imports inside function body.

### 4 Competing AnalysisResult Definitions (NEEDS CONSOLIDATION)

| Location | Package | Notes |
|----------|---------|-------|
| `shared.types.AnalysisResult` | shared | Canonical target |
| `ars_analysis.analytics.base.AnalysisResult` | ars_analysis | Has extra PPTX fields |
| `ics_toolkit.analysis.analyses.base.AnalysisResult` | ics_toolkit | Similar to shared |
| `txn_analysis.analyses.base.AnalysisResult` | txn_analysis | Similar to shared |

Consolidating these into `shared.types.AnalysisResult` is Tier 3.1 and BLOCKS Tier 4.1 (Platform App wiring).

### Streamlit UI Pages

```
platform_app/pages/
  home.py              Dashboard with product cards (ARS/TXN/ICS)
  workspace.py         CSM folder + client selection, auto-detect files
  data_ingestion.py    Upload/path for ODDD, Transaction+ODD, ICS
  module_library.py    Browse/search/select all analysis modules
  config_page.py       Client settings management
  run_analysis.py      Execute selected modules with progress
  batch_workflow.py    Queue multiple pipelines sequentially
  results_viewer.py    View results and download
  outputs.py           Output file browser
  history.py           Run history log
  run_history.py       Detailed run history
  dashboard.py         KPI overview
```

UI is scaffolded but NOT wired to actual pipeline execution (Issue #14).

---

## 5. Roadmap (5 Tiers)

### Tier 1: Stabilize & Lock In -- DONE

- [x] CI floor raised to 80%
- [x] Docs updated with current numbers
- [x] PR #17 V4 consolidation committed and pushed
- [x] PR #18 ARS CLI fix committed and pushed

### Tier 2: Coverage & Repo Triage -- PARTIAL

- [x] V4 storyline coverage (S7: 95%, S8: 97%)
- [ ] Close 4 txn-analysis issues superseded by PR #17 (#5, #6, #11, #16)
- [ ] Migrate 2 txn-analysis issues to monorepo (#10 config, #13 competitor merge)
- [ ] Investigate ars-pipeline #10 (production file path bug)
- [ ] ARS CLI coverage (currently 35% -- 230 lines missed)
- [ ] Interchange analysis coverage (currently 26% -- 28 lines missed)

### Tier 3: Architecture Consolidation -- NOT STARTED

- [ ] **3.1 Unified AnalysisResult** -- Collapse 4 definitions into `shared.types.AnalysisResult`. All 3 pipelines import from shared. **BLOCKS Tier 4.1.**
- [ ] **3.2 Deduplicate helpers** -- `safe_percentage()` exists in both ics_toolkit and txn_analysis. `ConfigError` in ics_toolkit and shared.
- [ ] **3.3 Decompose Storyline Monoliths** -- Break S5/S7/S8/S9 (267-463 LOC each) into small focused modules. Delete `storylines/` directory entirely.
- [ ] **3.4 Slim oversized files** -- `ics_toolkit/settings.py` (380+ lines)

### Tier 4: Platform Features -- NOT STARTED

- [ ] **4.1 Wire Pipeline Execution** (Issue #14) -- Connect Streamlit UI to actual pipeline runs. Requires Tier 3.1.
- [ ] **4.2 Cross-Pipeline Dashboard** -- Unified results viewer across ARS/TXN/ICS
- [ ] **4.3 Chart Formatting Fixes** -- Spine removal, positioning consistency
- [ ] **4.4 Reg E Enhancement** -- 5-sprint plan exists in `plans/feat-reg-e-enhancement.md`
- [ ] **4.5 PPTX Template System** -- Branded deck generation

### Tier 5: CI & DevEx Polish -- NOT STARTED

- [ ] CI caching (`uv cache` in GitHub Actions)
- [ ] Per-package Makefile targets (`make test-ars`, `make test-txn`, etc.)
- [ ] Coverage report as PR comment/artifact
- [ ] User documentation

### Execution Order

```
IMMEDIATE (before next feature work):
  1. Commit UI fixes (7 files, this session)
  2. Push to origin
  3. Merge PR #18 (ARS CLI fix -- no conflicts)
  4. Merge PR #17 (V4 consolidation -- the big one)
  5. Close txn-analysis #5, #6, #11, #16
  6. Delete stale branches

NEXT WORKER:
  Tier 3.1 (Unified AnalysisResult)  <-- unblocks everything downstream
    |
  Tier 4.1 (Wire Pipeline Execution / Issue #14)
    |
  Tier 4.2-4.5 (Features -- can parallel)
    |
  Tier 5 (Polish)
```

---

## 6. Uncommitted Changes (ACTION REQUIRED)

There are **7 modified files + 1 untracked** on `feat/platform-enhancement` that need to be committed and pushed before merging PR #17.

```
modified:   CLAUDE.md
modified:   packages/platform_app/src/platform_app/core/templates.py
modified:   packages/platform_app/src/platform_app/pages/batch_workflow.py
modified:   packages/platform_app/src/platform_app/pages/data_ingestion.py
modified:   packages/platform_app/src/platform_app/pages/home.py
modified:   packages/platform_app/src/platform_app/pages/module_library.py
modified:   packages/platform_app/src/platform_app/pages/run_analysis.py
untracked:  HANDOFF.md
```

**What these fix:** Streamlit UI crash (3 pages referenced deleted `Product.TXN_V4` enum), stale V4 template, missing ODD file support in TXN data ingestion/batch/run pages.

**Suggested commit:**
```bash
git add CLAUDE.md HANDOFF.md packages/platform_app/
git commit -m "fix(platform): remove stale TXN_V4 refs from Streamlit UI, add ODD support"
git push
```

---

## 7. Commands Quick Reference

```bash
# Setup
cd /Users/jgmbp/Desktop/analysis_platform
source .venv/bin/activate   # or: uv sync --all-packages

# Test & Lint
make test          # all tests
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package testing
.venv/bin/python -m pytest tests/txn/ -v
.venv/bin/python -m pytest tests/ics/ -v
.venv/bin/python -m pytest tests/ars/ -v
.venv/bin/python -m pytest tests/platform/ -v
.venv/bin/python -m pytest tests/integration/ -v

# Run pipelines
.venv/bin/python -m txn_analysis data/file.csv
.venv/bin/python -m ics_toolkit analyze data/file.xlsx
.venv/bin/python -m ars_analysis data/file.xlsx

# Platform CLI
.venv/bin/python -m platform_app run --pipeline txn --data data/file.csv
.venv/bin/python -m platform_app run --pipeline txn --data data/file.csv --odd data/odd.xlsx

# Streamlit UI
.venv/bin/python -m streamlit run packages/platform_app/src/platform_app/app.py
```

---

## 8. Conventions

- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x perf regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor: 80%
- Files under 300 lines (split if larger)
- uv workspace for package management

---

## 9. Known Gotchas

- `callable | None` type hint fails on Python 3.12 -- use `Callable | None` from typing
- pandas `freq="M"` deprecated -- use `freq="ME"` (month-end)
- python-pptx `prs.slides` does NOT support slice indexing -- use `enumerate()` + skip
- kaleido deprecation warnings are noisy but harmless (pinned at 0.2.1)
- ARS suite runners overwrite `ctx["_save_to_excel"]` -- test results/slides, not mock call counts
- Grand Total rows via `pd.concat` can introduce object dtype -- always `pd.to_numeric(errors="coerce")`
- Excel `"0.0%"` format auto-multiplies by 100 -- use `'0.0"%"'` when values are already 0-100
- When deleting modules that are eagerly imported by `__init__.py`, simplify `__init__.py` first to avoid cascade import failures
- Storyline adapter pattern: thin wrapper converting pipeline args to V4 ctx dict + wrapping result back to AnalysisResult. Lazy imports inside function body avoid cascade.
- 4 ARS test files fail to collect due to missing `pydantic_settings` at import time -- run `uv sync --all-packages` to fix locally. CI is unaffected.
- When removing enum values (e.g. `Product.TXN_V4`), grep ALL files including Streamlit pages -- they crash at import time, not at runtime.

---

## 10. Key Files Reference

| File | What It Does |
|------|-------------|
| `packages/txn_analysis/src/txn_analysis/analyses/__init__.py` | ANALYSIS_REGISTRY (35 entries), `run_all_analyses()` |
| `packages/txn_analysis/src/txn_analysis/analyses/storyline_adapters.py` | Bridges S5/S7/S8/S9 into registry |
| `packages/txn_analysis/src/txn_analysis/pipeline.py` | Main TXN pipeline entry point |
| `packages/txn_analysis/src/txn_analysis/data_loader.py` | CSV/ODD loading, column resolution, merchant rules |
| `packages/txn_analysis/src/txn_analysis/settings.py` | Pydantic Settings with all TXN config |
| `packages/txn_analysis/src/txn_analysis/charts/builders.py` | 10 generic chart builders (ported from V4) |
| `packages/txn_analysis/src/txn_analysis/charts/theme.py` | Colors, formatting, `apply_theme()` |
| `packages/platform_app/src/platform_app/orchestrator.py` | Pipeline dispatcher |
| `packages/platform_app/src/platform_app/core/module_registry.py` | Unified module registry (ARS+TXN+ICS) |
| `packages/platform_app/src/platform_app/core/templates.py` | Analysis templates (builtin + user) |
| `packages/shared/src/shared/types.py` | Canonical `AnalysisResult` (consolidation target) |
| `.github/workflows/ci.yml` | CI config (lint + test + coverage floor) |
| `plans/feat-platform-enhancement-roadmap.md` | Full 5-tier roadmap |
| `plans/feat-reg-e-enhancement.md` | Reg E enhancement plan |
| `plans/feat-streamlit-platform-ui.md` | Streamlit UI plan |
