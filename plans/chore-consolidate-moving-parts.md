> **SUPERSEDED** by `chore-unified-consolidation.md` (2026-02-13). Phase 1 of this plan was completed; remaining phases merged into the unified plan.

# Consolidate Moving Parts -- Platform Stabilization Roadmap

**Type:** chore/stabilization
**Created:** 2026-02-20
**Context:** 5-package monorepo with 1942 tests, CI green, but several "last mile" gaps between "code exists" and "code works end-to-end for 300 CSMs on Windows."

---

## The Problem

The platform has excellent engineering -- orchestrator, 3 pipeline runners, UAP V2.0 UI, 1942 tests, sync scripts -- but nobody has run it end-to-end with real data. Several critical gaps block production usage:

1. `run.bat` crashes immediately (missing `__main__.py`)
2. Streamlit UI has a Run button but it's never been tested with real files
3. 4 standalone repos are drifting with uncommitted/unmerged work
4. Documentation is stale (wrong test counts, wrong coverage floor)

---

## Phase 1: Unblock Production (Day 1)

Quick fixes that unblock everything else. All are < 30 minutes each.

### 1.1 Add `__main__.py` to ars_analysis

**Why:** `run.bat` (the primary CSM entry point) calls `uv run python -m ars_analysis retrieve/format/batch`. Without `__main__.py`, this crashes with `No module named ars_analysis.__main__`.

- [x] Create `packages/ars_analysis/src/ars_analysis/__main__.py`
  ```python
  from ars_analysis.cli import app
  app()
  ```
- [x] Verify: `uv run python -m ars_analysis --help` shows CLI commands
- [x] Also add to `ics_toolkit` and `txn_analysis` if missing (both already have __main__.py)

### 1.2 Update CLAUDE.md

**Why:** Every new Claude session reads this first. Current content references completed 2/21 tasks and wrong test counts.

- [x] Replace "Session Pickup: 2.21.26" block with current state
- [x] Update test count: 2168 (was 1657 on main)
- [x] Fix coverage floor: confirmed 70% in ci.yml, currently at 81%
- [x] Add "What's Next" pointing to this plan
- [x] Document the `__main__.py` fix (in CLI commands section)

### 1.3 Update README test count

- [x] Line 54: "976 tests" -> "~2168 tests"
- [x] Line 288: "1431 tests" -> "~2168 tests"
- [x] Update runtime estimate if needed

---

## Phase 2: Real-World Validation (Day 1-2)

The single highest-leverage action: run one real client file through each pipeline.

### 2.1 ARS pipeline -- real ODD file test

**Why:** 80-row synthetic fixtures cannot validate 78-slide PowerPoint generation, branch heatmaps, L12M trend charts, or consolidation logic. Real ODD files have 10k-100k rows.

- [ ] Pick one real ODD file from M: drive (e.g., `1200-2026-01-Guardians CU-ODD.xlsx`)
- [ ] Run via CLI: `uv run python -m ars_analysis run /path/to/real-ODD.xlsx`
- [ ] Check output: Excel workbook, 70+ PNG charts, PowerPoint deck
- [ ] Compare to reference PDF if available
- [ ] Fix whatever breaks (likely: column name mismatches, empty subset handling, chart scaling)

### 2.2 ICS pipeline -- real ICS file test

- [ ] Run via CLI: `uv run python -m ics_toolkit analyze /path/to/real-ics.xlsx`
- [ ] Verify all 37 analyses + PPTX output

### 2.3 TXN pipeline -- real transaction file test

- [ ] Run via CLI: `uv run python -m txn_analysis /path/to/real-txn.csv`
- [ ] Verify base (M1-M10) + V4 storyline output

### 2.4 Streamlit UI -- end-to-end through browser

- [ ] `uv run streamlit run packages/platform_app/src/platform_app/app.py`
- [ ] Upload a real ODD file, select modules, click Run
- [ ] Verify progress bar, results display, output file paths
- [ ] Test batch workflow page with scan directory

---

## Phase 3: Repo Consolidation (Day 2-3)

Stop the drift. The monorepo is the source of truth now.

### 3.1 Audit standalone repo branches

| Repo | Branch | Action Needed |
|------|--------|---------------|
| `ars-pipeline` | main (4 uncommitted UI files) | UI was superseded by UAP V2.0. Discard changes. |
| `ars_analysis-jupyter` | fix/centralize-paths | Check if path fixes are needed in monorepo's config.py |
| `ars_analysis-jupyter` | fix/config-path | Check if config fix is needed |
| `ars_analysis-jupyter` | fix/executive-report | Check if report changes are needed |
| `ics_toolkit` | feat/referral-intelligence-engine | Already merged to monorepo via PR #9. Done. |
| `ics_append` | feat/modular-pipeline | Already in monorepo as ics_toolkit/append/. Done. |

- [ ] Review each jupyter branch for any unported fixes
- [ ] Port any needed fixes to monorepo
- [ ] Discard the rest

### 3.2 Archive standalone repos

- [ ] Add README banners to each standalone repo:
  ```
  ## ARCHIVED -- This repo has been merged into analysis-platform
  See: https://github.com/JG-CSI-Velocity/analysis-platform
  ```
- [ ] Set repos to read-only on GitHub (Settings > Archive)
- [ ] Keep sync scripts in monorepo for reference but mark as deprecated

### 3.3 Clean up stale branches

- [x] Delete merged remote branches: `feat/ars-v2-migration`, `feat/referral-intelligence-engine`, `test/close-coverage-gaps`
- [x] Evaluate `Gilmore3088-slides-with-scale` -- NOT merged, kept for now

---

## Phase 4: Windows Deployment (Day 3-4)

The target platform. Must work on Windows + M: drive.

### 4.1 Test batch scripts on Windows

- [ ] `run.bat` -- full pipeline (retrieve -> format -> batch -> streamlit)
- [ ] `run_batch.bat` -- headless batch processing
- [ ] `dashboard.bat` -- streamlit-only launch
- [ ] Verify `uv sync --all-packages` doesn't hang on shared M: drive

### 4.2 Address kaleido Windows issues

- [ ] kaleido==0.2.1 hangs on some Windows configs (tests auto-skip via conftest.py)
- [ ] Verify Plotly charts render on Windows or confirm fallback behavior
- [ ] If charts fail, consider matplotlib-only mode for Windows

### 4.3 M: drive path resolution

- [ ] Verify `ARSSettings.paths.ars_base` correctly resolves M: drive paths
- [ ] Test `retrieve` command (copies ODD from CSM M: folders)
- [ ] Test `format` command (reads/writes to M: drive)
- [ ] Test `batch` command (scans for ready files on M: drive)

---

## Phase 5: Harden CI (Week 2)

### 5.1 Fix coverage floor mismatch

- [ ] CLAUDE.md says 70%, ci.yml says 60%. Pick one and document.
- [ ] If 70% target: add tests to close the gap (currently ~64%)
- [ ] If 60% target: update CLAUDE.md to match reality

### 5.2 Add Windows CI runner (stretch)

- [ ] Add `windows-latest` runner to ci.yml
- [ ] Run core tests (skip kaleido-dependent ones)
- [ ] Catch Windows-specific import/path issues early

---

## Current Inventory

| Package | Tests | Status | Gap |
|---------|-------|--------|-----|
| shared | 50 | Stable | None |
| ars_analysis | 545 | Production-ready | Missing `__main__.py`, untested with real data |
| txn_analysis | 220 | Stable | Untested with real data |
| ics_toolkit | 1049 | Feature-complete | `skip_chart_pngs` kwarg bug in cli.py (fixed locally, on main?) |
| platform_app | 60 | UI complete | Execution wiring untested (Issue #14) |
| integration | 18 | Synthetic only | No real-data E2E tests |
| **Total** | **1942** | CI green | |

## Open Issues

- **#14** -- Platform App: Wire Pipeline Execution (OPEN, medium priority)
  - Execution wiring actually exists but is untested
  - Becomes validated after Phase 2.4

## Standalone Repos

| Repo | State | Recommendation |
|------|-------|----------------|
| ars-pipeline | Uncommitted UI changes | Discard + archive |
| ars_analysis-jupyter | 3 feature branches | Audit + archive |
| ics_toolkit | Clean, feature branch | Archive |
| ics_append | Clean, feature branch | Archive |

---

## Success Criteria

- [ ] `run.bat` executes without errors on Windows
- [ ] One real ODD file produces a complete 78-slide PowerPoint
- [ ] Streamlit UI can run ARS/TXN/ICS pipelines end-to-end
- [ ] All standalone repos archived with redirect banners
- [ ] CLAUDE.md and README reflect reality
- [ ] CI stays green on main
