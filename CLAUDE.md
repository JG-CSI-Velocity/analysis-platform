# Analysis Platform -- Claude Code Instructions

## Session Pickup: 2.7.26

### What just shipped
- **PR #17** (`feat/platform-enhancement`): V4 Consolidation + 186 new tests
  - https://github.com/JG-CSI-Velocity/analysis-platform/pull/17
  - 54 files changed, +4,092 / -8,595 lines (net -4,503 LOC)
  - Killed entire V4 parallel pipeline -- ONE unified txn pipeline now
  - 5-phase consolidation: merchant rules, charts, data loader, adapters, cleanup
  - Deleted 13 v4_* files (~8,600 LOC), kept 4 unique storylines (S5/S7/S8/S9) via adapters
  - Merged `txn_v4` into `txn` across orchestrator, CLI, components, module registry
  - 35 analyses in ANALYSIS_REGISTRY (was 31 base + 12 V4 separate)
  - 186 new tests (S7 campaigns: 94, S8 payroll: 92)
  - Coverage: 89%, 2,318 tests, CI floor 80%

- **PR #18** (`chore/consolidate-moving-parts`): ARS CLI crash fix + docs
  - Adds `ars_analysis/__main__.py` to fix `python -m ars_analysis` crash
  - Updates README + CLAUDE.md with current state

### Branch State
- Current branch: `feat/platform-enhancement` (PR #17)
- Working tree: CLEAN -- all committed and pushed
- PR #17 status: OPEN, ready to merge
- PR #18 status: OPEN, ready to merge (separate branch)

### Notes
- `txn_v4` pipeline no longer exists as separate concept -- all merged into `txn`
- Storyline adapters (`analyses/storyline_adapters.py`) bridge S5/S7/S8/S9 into ANALYSIS_REGISTRY
- `kaleido==0.2.1` pinned; deprecation warnings are noisy but harmless
- Pre-existing: 4 ARS test files fail to collect (missing `pydantic_settings` dep) -- unrelated to our work

---

## Project Structure

```
analysis_platform/
  packages/
    shared/           Shared types, context, config
    ars_analysis/     ARS pipeline (70+ analyses, PPTX deck)
    txn_analysis/     Transaction pipeline (35 analyses: M1-M14 + scorecard)
    ics_toolkit/      ICS pipeline (37 analyses + append + referral)
    platform_app/     Orchestrator, CLI, Streamlit UI
  tests/
    ars/              ARS tests (141)
    txn/              Transaction tests
    ics/              ICS tests (including ics/referral/ -- 212 tests)
    shared/           Shared tests (50)
    platform/         Platform tests
    integration/      E2E tests
```

## Commands

```bash
make test          # all tests
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package
.venv/bin/python -m pytest tests/ics/referral/ -v   # referral only
.venv/bin/python -m pytest tests/ics/ -v             # all ICS
.venv/bin/python -m pytest tests/ -v                 # everything
```

## Conventions
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor is 80% (`--cov-fail-under=80`) -- currently at 89%. 2,318 tests, passing.
