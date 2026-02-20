# Analysis Platform -- Claude Code Instructions

## Current State (2026-02-20)

**Monorepo health:** CI green, 2168 tests, 81% coverage, all PRs merged.

### Recent milestones
- **PR #4**: ARS v2 modular pipeline migration (545 tests, 20 analytics modules)
- **PR #9**: ICS Referral Intelligence Engine (212 tests, 8-step pipeline)
- **UAP V2.0**: Unified Streamlit UI with industrial theme, module registry

### What needs attention
- **Real-data validation**: All tests use synthetic fixtures. Run each pipeline with a real client file before deploying.
- **Windows .bat validation**: `run.bat`, `dashboard.bat`, `run_batch.bat` need testing on Windows M: drive.
- **Standalone repo archival**: `ars-pipeline`, `ars_analysis-jupyter`, `ics_toolkit`, `ics_append` are superseded by this monorepo.
- See `plans/chore-consolidate-moving-parts.md` for the full roadmap.

---

## Project Structure

```
analysis_platform/
  packages/
    shared/           Shared types, context, config (50 tests)
    ars_analysis/     ARS pipeline -- 20 modules, 70+ analyses, PPTX deck (545 tests)
    txn_analysis/     Transaction pipeline -- M1-M10 base + V4 S1-S9 storylines (446 tests)
    ics_toolkit/      ICS pipeline -- 37 analyses + append + referral (1049 tests)
    platform_app/     Orchestrator, Streamlit UI, CLI (60 tests)
  tests/
    ars/              ARS unit tests
    txn/              Transaction unit tests
    ics/              ICS unit tests (including referral)
    shared/           Shared unit tests
    platform/         Platform unit tests
    integration/      E2E tests (18 tests)
  scripts/
    sync_ars.sh/.bat  Sync from ars-pipeline upstream (renames ars.* -> ars_analysis.*)
    sync_ics.sh/.bat  Sync from ics_toolkit upstream
```

## Commands

```bash
# Development
uv run pytest tests/ -q              # all tests (~2168, ~2 min)
uv run pytest tests/ars/ -q          # ARS only
uv run pytest tests/ics/ -q          # ICS only
uv run pytest tests/integration/ -q  # E2E only
uv run ruff check .                  # lint
uv run ruff format --check .         # format check

# Make targets
make test    # all tests
make cov     # tests + coverage
make lint    # ruff check + format check
make fmt     # auto-fix lint + format

# Pipeline CLIs
uv run python -m ars_analysis --help
uv run python -m ics_toolkit --help
uv run python -m txn_analysis --help

# Streamlit UI
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

## Conventions
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor: 70% (`--cov-fail-under=70`), currently at ~81%

## Upstream Sync
- `ars-upstream` remote -> `JG-CSI-Velocity/ars-pipeline` (sync scripts rename `ars.*` -> `ars_analysis.*`)
- `ics-upstream` remote -> `JG-CSI-Velocity/ics_toolkit` (direct copy, same package name)
- Sync is manual: `./scripts/sync_ars.sh` or `scripts\sync_ars.bat`
- After sync: run tests, fix lint, verify no stale `from ars.` imports
