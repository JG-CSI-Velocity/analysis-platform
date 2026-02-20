# Analysis Platform -- Claude Code Instructions

## Session Pickup: 2026-02-07

### What just shipped (now merged to main)
- **PR #18** (`chore/consolidate-moving-parts`): ARS CLI crash fix -- MERGED
  - Adds `ars_analysis/__main__.py` to fix `python -m ars_analysis` crash

- **PR #17** (`feat/platform-enhancement`): V4 Consolidation + 186 new tests -- MERGING
  - https://github.com/JG-CSI-Velocity/analysis-platform/pull/17
  - 54 files changed, +4,092 / -8,595 lines (net -4,503 LOC)
  - Killed entire V4 parallel pipeline -- ONE unified txn pipeline now
  - 5-phase consolidation: merchant rules, charts, data loader, adapters, cleanup
  - Deleted 13 v4_* files (~8,600 LOC), kept 4 unique storylines (S5/S7/S8/S9) via adapters
  - Merged `txn_v4` into `txn` across orchestrator, CLI, components, module registry
  - 35 analyses in ANALYSIS_REGISTRY (was 31 base + 12 V4 separate)
  - 186 new tests (S7 campaigns: 94, S8 payroll: 92)
  - Purged all stale `Product.TXN_V4` from Streamlit UI pages
  - Added ODD file support to data ingestion, batch workflow, run analysis pages
  - Replaced dead "V4 Full Storyline" template with "TXN Full Suite" (35 real module keys)
  - Coverage: 89%, 2,305 tests passing, CI floor 80%

### Branch State
- Current branch: `feat/platform-enhancement` (merging into main)
- Working tree: CLEAN -- all committed and pushed
- PR #17: merging now
- PR #18: MERGED

### Notes
- `txn_v4` pipeline no longer exists as separate concept -- all merged into `txn`
- Storyline adapters (`analyses/storyline_adapters.py`) bridge S5/S7/S8/S9 into ANALYSIS_REGISTRY
- `kaleido==0.2.1` pinned; deprecation warnings are noisy but harmless
- Pre-existing: 4 ARS test files fail to collect (missing `pydantic_settings` dep) -- run `uv sync --all-packages` to fix
- See `HANDOFF.md` for comprehensive handoff to next worker

---

## Project Structure

```
analysis_platform/
  packages/
    shared/           Shared types, context, config (50 tests)
    ars_analysis/     ARS pipeline (70+ analyses, PPTX deck, 545 tests)
    txn_analysis/     Transaction pipeline (35 analyses: M1-M14 + scorecard, 597 tests)
    ics_toolkit/      ICS pipeline (37 analyses + append + referral, 1049 tests)
    platform_app/     Orchestrator, CLI, Streamlit UI (60 tests)
  tests/
    ars/              ARS tests (545)
    txn/              Transaction tests (597)
    ics/              ICS tests (1049, including ics/referral/ -- 212)
    shared/           Shared tests (50)
    platform/         Platform tests (60)
    integration/      E2E tests (17)
```

## Commands

```bash
# Development
make test          # all tests
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package
.venv/bin/python -m pytest tests/ics/referral/ -v   # referral only
.venv/bin/python -m pytest tests/ics/ -v             # all ICS
.venv/bin/python -m pytest tests/ -v                 # everything

# Pipeline CLIs
.venv/bin/python -m ars_analysis --help
.venv/bin/python -m ics_toolkit --help
.venv/bin/python -m txn_analysis --help

# Platform CLI
.venv/bin/python -m platform_app run --pipeline txn --data data/file.csv
.venv/bin/python -m platform_app run --pipeline txn --data data/file.csv --odd data/odd.xlsx

# Streamlit UI
.venv/bin/python -m streamlit run packages/platform_app/src/platform_app/app.py
```

## Conventions
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor is 80% (`--cov-fail-under=80`) -- currently at 89%. 2,305 tests, passing.
