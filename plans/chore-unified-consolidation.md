# Unified Consolidation Plan

**Type:** chore/architecture
**Created:** 2026-02-13
**Context:** Merging 3 overlapping plans into one actionable path. Previous session shipped V4 consolidation (PR #17), ARS CLI fix (PR #18), stale branch cleanup, and issue triage. This plan picks up the critical path.

---

## Situation Assessment

### What's Real (verified 2026-02-13)

| Metric | Value |
|--------|-------|
| Branch | `main` (clean, up to date with `6a77e89`) |
| Tests | **2,318 passing** (13 ARS collection failures from HANDOFF are RESOLVED) |
| Coverage | 89% (CI floor 80%) |
| Lint | Clean |
| Open PRs | 0 |
| Open Issues | 1 (#14 -- but see below) |

### What's Stale

1. **Issue #14 ("Wire Pipeline Execution") is DONE** -- `run_analysis.py` already calls `run_pipeline()` via orchestrator with progress tracking, error handling, and results display. The issue should be closed.

2. **HANDOFF.md says "13 ARS collection failures"** -- these are resolved. All 545 ARS tests collect and pass.

3. **3 overlapping plans** exist:
   - `chore-consolidate-moving-parts.md` -- Phase 1 done, Phases 2-5 are environment-dependent (Windows/real data)
   - `feat-platform-enhancement-roadmap.md` -- Tier 1 done, Tier 2 partially done, Tiers 3-5 open
   - `feat-streamlit-platform-ui.md` -- UI is built; execution is wired; largely complete

4. **CLAUDE.md** references "Session Pickup: 2026-02-07" and stale PR state

### What Actually Needs Doing (in order)

```
Phase 1: Housekeeping (30 min)                    <-- unblock everything
    Close #14, update docs, deprecate stale plans
         |
Phase 2: Unify AnalysisResult (2-4 hours)         <-- CRITICAL PATH
    4 definitions -> 1 in shared.types
         |
Phase 3: Deduplicate helpers (1 hour)             <-- quick win after Phase 2
    safe_percentage, safe_ratio -> shared
         |
Phase 4: End-to-end validation (1-2 hours)        <-- FIRST REAL TEST
    Run each pipeline with actual data
         |
Phase 5: Decompose storyline monoliths (2 hours)  <-- nice to have
    S5/S7/S8/S9 -> small focused modules
         |
Phase 6: Future features (deferred)
    Reg E enhancement, chart formatting, cross-pipeline dashboard
```

---

## Phase 1: Housekeeping (30 min)

Quick cleanup to reflect reality.

### 1.1 Close Issue #14

`run_analysis.py` lines 174-188 already call `run_pipeline()` with:
- Product detection from selected modules
- Input file resolution per pipeline
- Progress bar with status updates
- Per-pipeline error capture and display
- Results logging via `RunRecord`

**Action:** Close #14 with comment explaining it was implemented during V4 consolidation.

- [x] `gh issue close 14 --comment "..."`

### 1.2 Update CLAUDE.md

Current CLAUDE.md references "Session Pickup: 2026-02-07" and stale PR state.

- [x] Update to current state: 2,318 tests, 89% coverage, 0 open PRs, 0 open issues
- [x] Point to this plan as the active roadmap
- [x] Remove references to stale plans

### 1.3 Update HANDOFF.md

- [x] Fix "13 ARS pre-existing collection failures" -> "all resolved"
- [x] Update test count: 2,318 (was 2,305)
- [x] Mark Issue #14 as closed in the issues table

### 1.4 Deprecate overlapping plans

- [x] Add "SUPERSEDED by chore-unified-consolidation.md" banner to:
  - `chore-consolidate-moving-parts.md` (Phase 1 done; rest is environment-dependent)
  - `feat-platform-enhancement-roadmap.md` (merged into this plan)
  - `feat-streamlit-platform-ui.md` (UI is built and wired)

---

## Phase 2: Unify AnalysisResult (2-4 hours)

**This is the single most impactful architectural change.** 4 competing definitions create confusion and block true cross-pipeline interop.

### Current State (4 definitions)

| Package | Location | Key Fields |
|---------|----------|------------|
| `shared` | `shared/types.py:13` | `name`, `data: dict[str, DataFrame]`, `charts: list[Path]`, `summary`, `metadata` (frozen) |
| `ars_analysis` | `analytics/base.py:26` | `slide_id`, `title`, `chart_path: Path|None`, `excel_data: dict[str, DataFrame]|None`, `notes`, `success: bool`, `error` (mutable) |
| `ics_toolkit` | `analysis/analyses/base.py:10` | `name`, `title`, `df: DataFrame`, `error: str|None`, `sheet_name`, `metadata` (mutable) |
| `txn_analysis` | `analyses/base.py:11` | `name`, `title`, `df: DataFrame`, `error: str|None`, `sheet_name: str|None`, `metadata` (mutable) |

### Target: Unified `shared.types.AnalysisResult`

Design a superset that covers all use cases:

```python
# packages/shared/src/shared/types.py
@dataclass
class AnalysisResult:
    """Standard output container for a single analysis."""
    name: str
    title: str = ""
    data: dict[str, pd.DataFrame] = field(default_factory=dict)
    charts: list[Path] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

Field mapping:

| Old Field | Package | Maps To |
|-----------|---------|---------|
| `slide_id` | ARS | `name` |
| `df` | ICS, TXN | `data["main"]` (single-DF convenience) |
| `chart_path` | ARS | `charts[0]` (single-chart convenience) |
| `excel_data` | ARS | `data` (already a dict) |
| `sheet_name` | ICS, TXN | `metadata["sheet_name"]` |
| `notes` | ARS | `metadata["notes"]` |
| `success` | ARS | `error is None` (derived) |
| `summary` | shared (old) | `metadata["summary"]` |

### Migration Steps

#### 2.1 Extend shared.types.AnalysisResult

- [x] Add `title: str = ""` field
- [x] Add `error: str | None = None` field
- [x] Keep `frozen=True` (runners create SharedResult at boundary; ARS keeps its own mutable type internally)
- [x] Keep `summary: str = ""` for backwards compat
- [x] Add convenience properties: `@property def df`, `@property def sheet_name`, `@property def success`
- [x] Add `from_df()` classmethod for ICS/TXN convenience
- [x] Update shared tests (18 tests, all passing)

#### 2.2 Migrate TXN to shared.types.AnalysisResult

TXN is closest to shared -- lowest risk first.

- [x] Update `txn_analysis/analyses/base.py`: re-export `AnalysisResult` from `shared.types`
- [x] Update all 46 TXN constructor calls to use `AnalysisResult.from_df()` (19 source files, 3 test files)
- [x] 597 TXN tests passing + 6 integration tests passing

#### 2.3 Migrate ICS to shared.types.AnalysisResult

ICS is nearly identical to TXN.

- [x] Update `ics_toolkit/analysis/analyses/base.py`: re-export `AnalysisResult` from `shared.types`
- [x] Update all 186 ICS constructor calls to use `AnalysisResult.from_df()` (23 source files, 7 test files)
- [x] sheet_name auto-population handled by `from_df()` classmethod
- [x] 1049 ICS tests passing + 3 integration tests passing

#### 2.4 Migrate ARS to shared.types.AnalysisResult

ARS has the most divergence. Use adapter pattern.

- [x] **Decision: Keep ARS internal type as-is.** ARS has a completely different field structure (slide_id, chart_path, excel_data, success, error vs name, data dict, charts list). The runner.py bridge already converts at the boundary cleanly. Forcing migration would touch 23 source files + 10 test files with zero functional benefit.
- [x] Result: **1 canonical shared type** (TXN, ICS, platform, orchestrator) + **1 ARS-internal type** (scoped to ars_analysis.analytics.base). Clean boundary via runner.py.

#### 2.5 Update orchestrator

- [x] Verified `orchestrator.py` imports from `shared.types`
- [x] Verified all pipeline runners return `dict[str, shared.types.AnalysisResult]`
- [x] All 545 ARS + 597 TXN + 1049 ICS + integration tests passing

---

## Phase 3: Deduplicate Helpers (1 hour)

Quick win after Phase 2 since we're already editing base.py files.

### 3.1 Move safe_percentage to shared

Two implementations exist:
- **ICS** (`analysis/analyses/base.py:25`): Checks `pd.isna(denominator)` -- more robust
- **TXN** (`analyses/base.py:22`): No NaN check

- [x] Created `packages/shared/src/shared/helpers.py` with `safe_percentage` + `safe_ratio`
- [x] Added 13 tests in `tests/shared/test_helpers.py`
- [x] Updated ICS base.py: re-exports from `shared.helpers` (zero import changes needed downstream)
- [x] Updated TXN base.py: re-exports from `shared.helpers` (zero import changes needed downstream)
- [x] Removed local definitions from ICS and TXN base.py
- [x] All 597 TXN + 1049 ICS tests passing

### 3.2 Leave ConfigError as-is

Each package has its own exception hierarchy (`ICSToolkitError`, `TxnError`, `ARSError`). This is correct design -- package-specific exceptions allow proper error isolation.

**No action needed.**

---

## Phase 4: End-to-End Validation (1-2 hours)

First real-data test of each pipeline. This can run on macOS if you have sample data files, or defer to Windows M: drive.

### 4.1 Test TXN pipeline

- [ ] Find or create a sample transaction CSV (needs: `merchant_name`, `amount`, `primary_account_num`, `transaction_date`, `mcc_code`)
- [ ] Run: `uv run python -m txn_analysis /path/to/sample.csv`
- [ ] Verify: Excel output + chart PNGs

### 4.2 Test ICS pipeline

- [ ] Find or create a sample ICS Excel
- [ ] Run: `uv run python -m ics_toolkit analyze /path/to/sample.xlsx`
- [ ] Verify: 37 analyses + PPTX

### 4.3 Test ARS pipeline

- [ ] Find a real ODD file (or synthetic with realistic column names and data volume)
- [ ] Run: `uv run python -m ars_analysis run /path/to/ODD.xlsx`
- [ ] Verify: Excel + charts + PPTX deck

### 4.4 Test Streamlit UI

- [ ] `uv run streamlit run packages/platform_app/src/platform_app/app.py`
- [ ] Upload a file, select modules, click Run
- [ ] Verify progress bar, results display, output files

---

## Phase 5: Decompose Storyline Monoliths (2 hours, optional)

S5/S7/S8/S9 are 267-463 LOC each. They work via thin adapters in `storyline_adapters.py` but are still monolithic.

- [ ] Break each into smaller focused modules
- [ ] Delete `storylines/` directory once all code is in `analyses/`
- [ ] Update adapter imports
- [ ] Ensure M11-M14 registry entries still work

**Priority:** Low. The adapters work. Only do this if time permits.

---

## Phase 6: Deferred Features

These are documented in existing plans but are NOT on the critical path:

| Feature | Plan File | Priority |
|---------|-----------|----------|
| Reg E Enhancement (5 sprints) | `feat-reg-e-enhancement.md` | Medium -- product feature |
| Chart Formatting Fixes | `fix-chart-formatting-spines-positioning.md` | Low -- cosmetic |
| Cross-Pipeline Dashboard | `feat-platform-enhancement-roadmap.md` T4.2 | Low -- UI polish |
| PPTX Template System | T4.5 | Low |
| Windows Deployment | `chore-consolidate-moving-parts.md` Phase 4 | High when deploying |
| Standalone Repo Archival | `chore-consolidate-moving-parts.md` Phase 3 | Medium -- housekeeping |
| CI Caching + DevEx | T5 | Low |

---

## Files That Will Change

### Phase 1 (docs only)
- `CLAUDE.md` -- update current state
- `HANDOFF.md` -- fix stale test counts
- `plans/chore-consolidate-moving-parts.md` -- add superseded banner
- `plans/feat-platform-enhancement-roadmap.md` -- add superseded banner
- `plans/feat-streamlit-platform-ui.md` -- add superseded banner

### Phase 2 (AnalysisResult unification)
- `packages/shared/src/shared/types.py` -- extend AnalysisResult
- `tests/shared/test_types.py` -- new/updated tests
- `packages/txn_analysis/src/txn_analysis/analyses/base.py` -- remove local definition
- `packages/txn_analysis/src/txn_analysis/analyses/*.py` -- update constructors (~15 files)
- `packages/ics_toolkit/src/ics_toolkit/analysis/analyses/base.py` -- remove local definition
- `packages/ics_toolkit/src/ics_toolkit/analysis/analyses/*.py` -- update constructors (~18 files)
- `packages/ars_analysis/src/ars_analysis/analytics/base.py` -- remove local definition
- `packages/ars_analysis/src/ars_analysis/analytics/**/*.py` -- update constructors (~20 files)
- `packages/platform_app/src/platform_app/orchestrator.py` -- verify imports

### Phase 3 (helper dedup)
- `packages/shared/src/shared/helpers.py` -- new file
- `tests/shared/test_helpers.py` -- new tests
- `packages/ics_toolkit/src/ics_toolkit/analysis/analyses/base.py` -- remove safe_percentage/safe_ratio
- `packages/txn_analysis/src/txn_analysis/analyses/base.py` -- remove safe_percentage
- ~23 files updating imports

---

## Success Criteria

- [ ] 0 open issues on analysis-platform
- [ ] Single `AnalysisResult` definition in `shared.types`, used by all 3 pipelines
- [ ] No duplicated helper functions across packages
- [ ] All tests pass (2,318+)
- [ ] Coverage stays >= 89%
- [ ] CLAUDE.md and HANDOFF.md reflect reality
- [ ] At least one pipeline tested with real (non-synthetic) data
