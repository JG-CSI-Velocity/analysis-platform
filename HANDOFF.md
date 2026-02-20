# CSI Velocity -- Repository Roadmap & Session Handoff

**Date:** 2026-02-07
**Repo:** https://github.com/JG-CSI-Velocity/analysis-platform
**Location:** `/Users/jgmbp/Desktop/analysis_platform/`
**Current branch:** `main`
**Working tree:** CLEAN

---

## 1. What Was Handed To Me

The user provided a comprehensive CSI Velocity Repository Roadmap covering:

- **Monorepo state:** 5-package uv workspace (`shared`, `ars_analysis`, `txn_analysis`, `ics_toolkit`, `platform_app`)
- **Problem:** Two completely independent transaction analysis systems existed in `txn_analysis` -- a main pipeline (M1-M10, ~2,000 LOC) and a V4 pipeline (S1-S9, ~12,200 LOC) with 60% overlap and zero shared code
- **V4 consolidation plan:** 5-phase plan to kill V4, keep unique analyses, merge infrastructure (Phases 1-4 already committed)
- **5-tier roadmap:** Stabilize -> Coverage -> Architecture -> Features -> Polish
- **Open PRs:** #17 (V4 consolidation, Phases 1-4), #18 (ARS CLI fix)
- **Open issues:** 1 on monorepo (#14), 6 on txn-analysis (standalone), 1 on ars-pipeline (standalone)
- **Standalone repos:** txn-analysis, ars-pipeline, ics-analysis, ics-append (all superseded by monorepo)
- **Test suite:** 2,318 tests, 89% coverage, CI floor 80%

The handoff asked me to: complete Phase 5, fix Streamlit UI, ensure consistency, merge everything, close superseded issues, and produce a handoff summary.

---

## 2. What I Did

### 2a. Completed V4 Consolidation Phase 5 (prior session, committed in `7de644e`)

Phase 5: delete overlapping storylines and purge all `txn_v4` references from the platform app.

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
| `orchestrator.py` | Removed `"txn_v4"` from `PIPELINE_NAMES`, simplified detection |
| `components.py` | Removed `txn_v4` from pipeline selector and `PIPELINE_FILE_ROLES` |
| `cli.py` | Updated help text, simplified `_build_input_files` |
| `module_registry.py` | Removed `Product.TXN_V4` enum, removed `_V4_STORYLINES`, added M11-M14 to `_TXN_MODULES` |
| `session_manager.py` | `pipelines.extend(["txn", "txn_v4"])` -> `pipelines.append("txn")` |
| `dashboard.py` | Removed `txn_v4` from counter |

### 2b. Fixed Streamlit UI Crash (committed in `1c3d8fc`)

Phase 5 removed `Product.TXN_V4` from the enum but three Streamlit pages still referenced it, causing import-time `AttributeError` crashes that made the module library and run pages invisible.

**Fixed 7 files:**

| File | Change |
|------|--------|
| `pages/home.py` | Removed V4 product card (4 cols -> 3), updated TXN desc to "M1-M14 + scorecard" |
| `pages/module_library.py` | Removed `Product.TXN_V4` from `_COLORS` dict |
| `pages/run_analysis.py` | Removed `TXN_V4` refs, added ODD file passthrough to TXN pipeline |
| `pages/data_ingestion.py` | Added ODD upload/path input under Transaction tab (enables M11-M14) |
| `pages/batch_workflow.py` | "Transaction Base" -> "Transaction Analysis", added ODD file input, passes ODD to TXN |
| `core/templates.py` | Replaced dead `"V4 Full Storyline"` template (v4_s0-s9 keys) with `"TXN Full Suite"` (all 35 real module keys) |
| `CLAUDE.md` | Updated session pickup |

### 2c. Merged, Closed, and Cleaned Up

| Action | Detail |
|--------|--------|
| Merged PR #18 | ARS CLI crash fix (`chore/consolidate-moving-parts`) |
| Merged PR #17 | V4 consolidation + UI fixes (`feat/platform-enhancement`) |
| Closed txn-analysis #5 | "improve dupe id" -- superseded by consolidated merchant_rules |
| Closed txn-analysis #6 | "merchant top 50 spend" -- covered by M1-M5 |
| Closed txn-analysis #11 | "ch - viz - comp heavy spend" -- covered by M6 competitor_* |
| Closed txn-analysis #16 | "comp spend by account" -- covered by M6 + M10 |
| Commented txn-analysis #10 | "config" -- flagged for migration to monorepo |
| Commented txn-analysis #13 | "merge competition" -- flagged for migration to monorepo |
| Commented ars-pipeline #10 | "2.17 run issue" -- flagged for investigation in monorepo context |
| Deleted 5 local branches | feat/platform-enhancement, feat/v4-consolidation, test/close-coverage-gaps, feat/referral-intelligence-engine, feat/streamlit-ui |
| Deleted remote branches | feat/platform-enhancement, Gilmore3088-slides-with-scale; pruned 3 others |
| Updated README.md | Removed all V4 references, updated test counts |
| Updated CLAUDE.md | Current session pickup with merged state |

---

## 3. Current State (verified 2026-02-07)

### Repository Map

```
analysis_platform/                    https://github.com/JG-CSI-Velocity/analysis-platform
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
| Tests passing | 2,305 (13 ARS pre-existing collection failures) |
| Coverage | 89% (16,018 stmts, 1,737 missed) |
| CI floor | 80% (`--cov-fail-under=80`) |
| Test time | ~2 min |
| Lint | Clean (ruff check + ruff format) |
| Warnings | 2,443 (all kaleido deprecation -- harmless) |

### Open PRs

None. All merged.

### Open Issues

**analysis-platform (monorepo):**

| # | Title | Notes |
|---|-------|-------|
| 14 | Platform App: Wire Pipeline Execution | Tier 4.1 -- biggest remaining feature. BLOCKS on Tier 3.1 (unified AnalysisResult). |

**txn-analysis (standalone -- superseded, commented for migration):**

| # | Title | Disposition |
|---|-------|-------------|
| 10 | config | MIGRATE to monorepo -- commented with pointer to `settings.py` |
| 13 | merge competition | MIGRATE to monorepo -- commented with pointer to M6 competitor_detection |

**ars-pipeline (standalone -- superseded):**

| # | Title | Disposition |
|---|-------|-------------|
| 10 | 2.17 run issue | INVESTIGATE -- production file path bug, commented with pointer to `ars_config.py` |

**ics-analysis, ics-append:** 0 open issues. Clean.

### Standalone Repos

| Repo | Monorepo Package | Status |
|------|-----------------|--------|
| `txn-analysis` | `txn_analysis` | Superseded. 4 issues closed, 2 open (migrate). |
| `ars-pipeline` | `ars_analysis` | Superseded. 1 open issue (production bug). |
| `ics-analysis` | `ics_toolkit` | Superseded. Clean. |
| `ics-append` | `ics_toolkit` | Superseded. Clean. |
| `ils_kickoff_day2` | NOT in monorepo | Standalone OD/NSF tool, 75 tests, 91% coverage. |

### Branches

```
Local:   main (only)
Remote:  origin/main (only)
```

All stale branches deleted.

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

M11-M14 are thin adapters in `analyses/storyline_adapters.py` that wrap the kept V4 storyline modules (S5/S7/S8/S9). They convert pipeline args to V4 context dict and wrap results back to AnalysisResult. Lazy imports inside function body. Graceful empty result when ODD file not provided.

### 4 Competing AnalysisResult Definitions (NEEDS CONSOLIDATION -- Tier 3.1)

| Location | Package | Notes |
|----------|---------|-------|
| `shared.types.AnalysisResult` | shared | Canonical target |
| `ars_analysis.analytics.base.AnalysisResult` | ars_analysis | Has extra PPTX fields |
| `ics_toolkit.analysis.analyses.base.AnalysisResult` | ics_toolkit | Similar to shared |
| `txn_analysis.analyses.base.AnalysisResult` | txn_analysis | Similar to shared |

Consolidating these into `shared.types.AnalysisResult` is Tier 3.1 and **BLOCKS** Tier 4.1 (Platform App wiring / Issue #14).

### Streamlit UI Pages

```
platform_app/pages/
  home.py              Dashboard with product cards (ARS/TXN/ICS -- 3 products, V4 removed)
  workspace.py         CSM folder + client selection, auto-detect files
  data_ingestion.py    Upload/path for ODDD, Transaction + ODD (optional), ICS
  module_library.py    Browse/search/select all analysis modules (3 products)
  config_page.py       Client settings management
  run_analysis.py      Execute selected modules with progress (passes ODD to TXN)
  batch_workflow.py    Queue multiple pipelines sequentially (passes ODD to TXN)
  results_viewer.py    View results and download
  outputs.py           Output file browser
  history.py           Run history log
  run_history.py       Detailed run history
  dashboard.py         KPI overview
```

UI is scaffolded but **NOT wired** to actual pipeline execution (Issue #14).

---

## 5. Roadmap (5 Tiers)

### Tier 1: Stabilize & Lock In -- DONE

- [x] CI floor raised to 80%
- [x] Docs updated with current numbers
- [x] PR #17 V4 consolidation -- MERGED
- [x] PR #18 ARS CLI fix -- MERGED
- [x] 4 txn-analysis issues closed (#5, #6, #11, #16)
- [x] Stale branches deleted (all of them)
- [x] Commentary left on all adjusted issues

### Tier 2: Coverage & Repo Triage -- PARTIAL

- [x] V4 storyline coverage (S7: 95%, S8: 97%)
- [x] Superseded issues closed with commentary
- [ ] Migrate txn-analysis #10 (config) to monorepo issue
- [ ] Migrate txn-analysis #13 (competitor merge) to monorepo issue
- [ ] Investigate ars-pipeline #10 (production file path bug)
- [ ] ARS CLI coverage (currently 35% -- 230 lines missed)
- [ ] Interchange analysis coverage (currently 26% -- 28 lines missed)

### Tier 3: Architecture Consolidation -- NOT STARTED

- [ ] **3.1 Unified AnalysisResult** -- Collapse 4 definitions into `shared.types.AnalysisResult`. All 3 pipelines import from shared. **BLOCKS Tier 4.1.**
- [ ] **3.2 Deduplicate helpers** -- `safe_percentage()` in both ics_toolkit and txn_analysis. `ConfigError` in ics_toolkit and shared.
- [ ] **3.3 Decompose Storyline Monoliths** -- Break S5/S7/S8/S9 (267-463 LOC each) into small focused modules. Delete `storylines/` directory.
- [ ] **3.4 Slim oversized files** -- `ics_toolkit/settings.py` (380+ lines)

### Tier 4: Platform Features -- NOT STARTED

- [ ] **4.1 Wire Pipeline Execution** (Issue #14) -- Connect Streamlit UI to actual pipeline runs. Requires Tier 3.1.
- [ ] **4.2 Cross-Pipeline Dashboard** -- Unified results viewer across ARS/TXN/ICS
- [ ] **4.3 Chart Formatting Fixes** -- Spine removal, positioning consistency
- [ ] **4.4 Reg E Enhancement** -- 5-sprint plan in `plans/feat-reg-e-enhancement.md`
- [ ] **4.5 PPTX Template System** -- Branded deck generation

### Tier 5: CI & DevEx Polish -- NOT STARTED

- [ ] CI caching (`uv cache` in GitHub Actions)
- [ ] Per-package Makefile targets (`make test-ars`, `make test-txn`, etc.)
- [ ] Coverage report as PR comment/artifact
- [ ] User documentation

### Execution Order for Next Worker

```
Tier 3.1 (Unified AnalysisResult)  <-- THIS IS THE CRITICAL PATH
  |
Tier 4.1 (Wire Pipeline Execution / Issue #14)
  |
Tier 3.3 (Decompose Storyline Monoliths)  <-- can parallel with 4.1
  |
Tier 4.2-4.5 (Features -- can parallel)
  |
Tier 2 remainder (coverage gaps, issue migration)  <-- can parallel anytime
  |
Tier 5 (Polish)
```

---

## 6. Commands Quick Reference

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

## 7. Conventions

- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x perf regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor: 80%
- Files under 300 lines (split if larger)
- uv workspace for package management

---

## 8. Known Gotchas

- `callable | None` type hint fails on Python 3.12 -- use `Callable | None` from typing
- pandas `freq="M"` deprecated -- use `freq="ME"` (month-end)
- python-pptx `prs.slides` does NOT support slice indexing -- use `enumerate()` + skip
- kaleido deprecation warnings are noisy but harmless (pinned at 0.2.1)
- ARS suite runners overwrite `ctx["_save_to_excel"]` -- test results/slides, not mock call counts
- Grand Total rows via `pd.concat` can introduce object dtype -- always `pd.to_numeric(errors="coerce")`
- Excel `"0.0%"` format auto-multiplies by 100 -- use `'0.0"%"'` when values are already 0-100
- When deleting modules eagerly imported by `__init__.py`, simplify `__init__.py` first to avoid cascade import failures
- Storyline adapter pattern: thin wrapper converting pipeline args to V4 ctx dict + wrapping result back to AnalysisResult. Lazy imports inside function body.
- 4 ARS test files fail to collect (missing `pydantic_settings` at import time) -- run `uv sync --all-packages` to fix locally. CI is unaffected.
- When removing enum values (e.g. `Product.TXN_V4`), grep ALL files including Streamlit pages -- they crash at import time, not runtime.

---

## 9. Key Files Reference

| File | What It Does |
|------|-------------|
| `packages/txn_analysis/src/txn_analysis/analyses/__init__.py` | ANALYSIS_REGISTRY (35 entries), `run_all_analyses()` |
| `packages/txn_analysis/src/txn_analysis/analyses/storyline_adapters.py` | Bridges S5/S7/S8/S9 into registry |
| `packages/txn_analysis/src/txn_analysis/pipeline.py` | Main TXN pipeline entry point |
| `packages/txn_analysis/src/txn_analysis/data_loader.py` | CSV/ODD loading, column resolution, merchant rules |
| `packages/txn_analysis/src/txn_analysis/settings.py` | Pydantic Settings with all TXN config |
| `packages/txn_analysis/src/txn_analysis/charts/builders.py` | 10 generic chart builders (ported from V4) |
| `packages/txn_analysis/src/txn_analysis/charts/theme.py` | Colors, formatting, `apply_theme()` |
| `packages/platform_app/src/platform_app/orchestrator.py` | Pipeline dispatcher (ars, txn, ics, ics_append) |
| `packages/platform_app/src/platform_app/core/module_registry.py` | Unified module registry (ARS + TXN + ICS) |
| `packages/platform_app/src/platform_app/core/templates.py` | Analysis templates (builtin + user-saved) |
| `packages/shared/src/shared/types.py` | Canonical `AnalysisResult` (consolidation target for Tier 3.1) |
| `.github/workflows/ci.yml` | CI config (lint + test + coverage floor 80%) |
| `plans/feat-platform-enhancement-roadmap.md` | Full 5-tier roadmap with acceptance criteria |
| `plans/feat-reg-e-enhancement.md` | Reg E enhancement plan (5 sprints) |
| `plans/feat-streamlit-platform-ui.md` | Streamlit UI implementation plan |

---

## 10. What the Next Worker Should Do First

1. Read this file and `CLAUDE.md`
2. Run `make test` to verify green (2,305 should pass)
3. Start on **Tier 3.1: Unified AnalysisResult** -- this is the critical path that unblocks Issue #14 (Platform App wiring)
4. After 3.1, pick up **Tier 4.1** (wire Streamlit UI to real pipeline execution)
