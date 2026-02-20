# Platform Enhancement Roadmap

**Type:** enhancement
**Created:** 2026-02-21
**Status:** in-progress
**Repo:** `JG-CSI-Velocity/analysis-platform`

---

## Overview

Strategic enhancement plan for the analysis-platform monorepo. Organized into 5 tiers from "stabilize" to "polish and features." Each tier unlocks the next.

## Current State (verified 2026-02-21)

- **2301 tests pass**, 0 failures, 0 collection errors
- **88% coverage** (16018 stmts, 1963 missed)
- **CI:** floor raised to 80% (`--cov-fail-under=80`)
- **1 open issue:** #14 (Platform App wiring)
- **Local env note:** `pydantic-settings` was declared in `pyproject.toml` but missing locally until `uv sync --all-packages` was run. CI (ubuntu) installs fresh and was never affected.

---

## Tier 1: Stabilize & Lock In (30 min)

**Goal:** Raise CI floor to match reality, update docs.

### T1.1 Raise CI coverage floor

Coverage is 84%. CI floor is 60% (lowered during referral engine port). Raise it.

- [x] Update `.github/workflows/ci.yml`: `--cov-fail-under=80`
- [ ] Push, verify CI green
- [x] Commit: `ci: raise coverage floor to 80%`

**Files:** `.github/workflows/ci.yml:33`

### T1.2 Update docs with current numbers

- [x] `CLAUDE.md`: update test count to 2115, coverage to 84%, CI floor to 80%
- [x] `README.md`: update "1431 tests" to 2115
- [x] Commit: `docs: update test count and coverage stats`

---

## Tier 2: Coverage Gaps (2-4 hours)

**Goal:** Eliminate modules under 30% coverage. Push overall toward 90%.

### Lowest coverage modules (verified)

| Module | Stmts | Miss | Cov | Priority |
|--------|-------|------|-----|----------|
| ~~`txn_analysis/storylines/v4_s7_campaigns.py`~~ | 463 | 25 | **95%** | Done |
| ~~`txn_analysis/storylines/v4_s8_payroll.py`~~ | 323 | 9 | **97%** | Done |
| `txn_analysis/analyses/interchange.py` | 38 | 28 | 26% | Medium |
| `platform_app/components/results_display.py` | 35 | 27 | 23% | Low |
| `ars_analysis/cli.py` | 355 | 230 | 35% | Medium |

### T2.1 Write tests for V4 storyline modules

- [x] `tests/txn/test_v4_s7_campaigns.py` -- 94 tests, 95% coverage (was 10%)
- [x] `tests/txn/test_v4_s8_payroll.py` -- 92 tests, 97% coverage (was 17%)
- [x] Target: 50%+ coverage each -- EXCEEDED (95% and 97%)

**Pattern to follow:** existing V4 test files in `tests/txn/`.

### T2.2 Write tests for ARS CLI

- [ ] Test `scan` command with mock file system
- [ ] Test `format` command with mock input
- [ ] Test `batch` command with empty directory
- [ ] Test error handling and exit codes
- [ ] Target: 60%+ coverage (recovers ~130 missed lines)

**Files:** `tests/ars/test_cli.py`, `packages/ars_analysis/src/ars_analysis/cli.py`

### T2.3 Write tests for interchange analysis

- [ ] `tests/txn/test_interchange.py` -- test interchange rate calculation, edge cases
- [ ] Target: 70%+ coverage

### T2.4 Verify and commit

- [ ] `make cov` -- verify overall > 85%
- [ ] Commit: `test: add coverage for v4 storylines, ARS CLI, interchange`

---

## Tier 3: Architecture Consolidation (4-8 hours)

**Goal:** Reduce duplication, establish shared patterns.

### T3.1 Unify AnalysisResult

Currently 4 competing definitions:

| Package | Location | Fields |
|---------|----------|--------|
| `shared` | `shared/types.py` | Canonical base |
| `ars_analysis` | Various modules | Ad-hoc dicts |
| `txn_analysis` | `types.py` | Package-specific |
| `ics_toolkit` | `types.py` | Package-specific |

- [ ] Audit each package's `AnalysisResult` for field differences
- [ ] Extend `shared.types.AnalysisResult` to cover all use cases
- [ ] Migrate `ics_toolkit` to use `shared.types.AnalysisResult`
- [ ] Migrate `txn_analysis` to use `shared.types.AnalysisResult`
- [ ] ARS uses ad-hoc dicts -- document but don't force migration yet
- [ ] Tests pass after each migration

**Risk:** Large blast radius. Do one package at a time with full test run between.

**Dependency:** T3.1 should complete before T4.1 (Platform App wiring) so the orchestrator has a stable shared type.

### T3.2 Deduplicate helper functions

Known duplicates (verify before moving -- may have diverged):

| Function | Found in |
|----------|----------|
| `safe_percentage()` | `ics_toolkit/helpers.py`, `txn_analysis/helpers.py` |
| `ConfigError` | `ics_toolkit/exceptions.py`, `shared/exceptions.py` |

- [ ] Compare implementations to confirm they are equivalent
- [ ] Move shared functions to `shared/helpers.py`
- [ ] Establish `shared/exceptions.py` as the single exception hierarchy
- [ ] Update imports in consuming packages
- [ ] Tests pass after each move

### T3.3 Slim oversized files

Priority targets over the 300-line guideline:

- [ ] `ics_toolkit/settings.py` (380+ lines) -- split into `settings/base.py`, `settings/referral.py`
- [ ] Large analysis modules -- evaluate if splitting helps readability

---

## Tier 4: Feature Work (multi-day, broken into sub-tasks)

**Goal:** Ship new capabilities. Each sub-task is independently shippable.

### T4.1 Platform App wiring (Issue #14)

**Depends on:** T3.1 (unified AnalysisResult)

- [ ] Wire ARS pipeline execution through `platform_app`
- [ ] Wire TXN pipeline execution through `platform_app`
- [ ] Wire ICS pipeline execution through `platform_app`
- [ ] Wire Referral pipeline execution through `platform_app`
- [ ] Unified progress callbacks
- [ ] Error handling and reporting
- [ ] Close Issue #14

**Estimate:** 1 day

### T4.2 Streamlit UI

**Depends on:** T4.1 (pipelines wired)

- [ ] Landing page with pipeline selection
- [ ] File upload for each pipeline (including Referral)
- [ ] Progress display during execution
- [ ] Results viewer (Excel download, chart gallery)
- [ ] Error display for pipeline failures (user-friendly, not raw tracebacks)
- [ ] Temp file cleanup on session end

**Estimate:** 2-3 days

**Risks:**
- `kaleido==0.2.1` pin -- chart generation in Streamlit triggers kaleido. Ensure pin is respected.
- Temp file accumulation -- `file_input.py` uses `delete=False`. Add cleanup.

### T4.3 Chart Formatting fixes

**Should precede or parallel T4.4** (Reg E creates new charts that need correct formatting)

- [ ] Spine removal consistency
- [ ] Positioning fixes
- [ ] Apply across all chart builders

**Estimate:** 0.5 day

### T4.4 Reg E Enhancement

**Depends on:** T4.3 (chart formatting)

- [ ] Execute the existing plan items (5 sprints in sub-plan)

**Estimate:** 3-5 days (this is a substantial enhancement, not a quick task)

---

## Tier 5: CI & DevEx Polish (2-4 hours)

**Goal:** Fast CI, great developer experience.

### T5.1 CI optimization

- [ ] Add `uv cache` caching step to `.github/workflows/ci.yml`
- [ ] Add coverage report as PR comment or artifact
- [ ] Measure current CI time as baseline before optimizing

### T5.2 Developer tooling

- [ ] Add `make test-ars`, `make test-txn`, `make test-ics` targets for per-package testing
- [ ] Add `make test-quick` that skips slow chart/kaleido tests
- [ ] Ensure `make check` runs both lint and test in one command

### T5.3 Documentation

- [ ] Update README and CLAUDE.md after each tier (not queued to end)
- [ ] Keep test counts and coverage numbers current

---

## Acceptance Criteria

### Tier 1 Complete
- [ ] CI floor at 80%, CI green
- [ ] Docs current

### Tier 2 Complete
- [ ] No module under 30% coverage
- [ ] Overall coverage > 85%

### Tier 3 Complete
- [ ] Single `AnalysisResult` in `shared` used by ICS + TXN
- [ ] No duplicated helpers across packages
- [ ] No file over 300 lines (except analysis modules with good reason)

### Tier 4 Complete
- [ ] All 4 pipelines executable via `platform_app`
- [ ] Streamlit UI functional for all pipelines
- [ ] Issue #14 closed

### Tier 5 Complete
- [ ] Per-package test targets in Makefile
- [ ] CI has caching

---

## Recommended Execution Order

```
Tier 1 (T1.1 -> T1.2)                    -- 30 min, do now
  |
  +-- Tier 5.1-5.2                        -- Can start in parallel (CI + Makefile)
  |
Tier 2 (T2.1 -> T2.2 -> T2.3 -> T2.4)   -- Coverage gaps
  |
Tier 3 (T3.1 -> T3.2 -> T3.3)           -- Architecture (T3.1 blocks T4.1)
  |
Tier 4.3 (Chart Formatting)              -- Before Reg E
  |
Tier 4.1 (Platform App)  -->  Tier 4.2 (Streamlit UI)
  |
Tier 4.4 (Reg E Enhancement)             -- Largest single item
```

## References

- Issue #14: Platform App wiring
- `packages/shared/src/shared/types.py` -- canonical AnalysisResult
- `.github/workflows/ci.yml:33` -- CI coverage floor
- `tests/ars/test_cli.py` -- ARS CLI tests
- Coverage run: 2026-02-21, 84% overall, 2115 tests
