# Analysis Platform -- Claude Code Instructions

## Current State (2026-02-13)

**Monorepo health:** CI green, 2,318 tests, 89% coverage, 0 open PRs, 0 open issues.

### Recent milestones
- **PR #17**: V4 consolidation -- killed entire V4 parallel pipeline, unified to 35 analyses (M1-M14 + scorecard)
- **PR #18**: ARS CLI fix (`__main__.py`)
- **PR #4**: ARS v2 modular pipeline migration (545 tests, 20 analytics modules)
- **PR #9**: ICS Referral Intelligence Engine (212 tests, 8-step pipeline)
- **UAP V2.0**: Unified Streamlit UI with industrial theme, module registry
- **Issue #14**: Closed -- pipeline execution wiring already implemented in run_analysis.py

### Active roadmap
- See `plans/chore-unified-consolidation.md` for the unified path forward
- Priority: Unify AnalysisResult (4 definitions -> 1), deduplicate helpers, real-data validation

### What needs attention
- **AnalysisResult unification**: 4 competing definitions across shared/ars/txn/ics. See plan Phase 2.
- **Real-data validation**: All tests use synthetic fixtures. Run each pipeline with a real client file before deploying.
- **Windows .bat validation**: `run.bat`, `dashboard.bat`, `run_batch.bat` need testing on Windows M: drive.
- **Standalone repo archival**: `ars-pipeline`, `ars_analysis-jupyter`, `ics_toolkit`, `ics_append` are superseded by this monorepo.

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
make test          # all tests (~2,318, ~2 min)
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package
uv run pytest tests/ars/ -q          # ARS only
uv run pytest tests/txn/ -q          # TXN only
uv run pytest tests/ics/ -q          # ICS only
uv run pytest tests/integration/ -q  # E2E only

# Pipeline CLIs
uv run python -m ars_analysis --help
uv run python -m ics_toolkit --help
uv run python -m txn_analysis --help

# Platform CLI
uv run python -m platform_app run --pipeline txn --data data/file.csv
uv run python -m platform_app run --pipeline txn --data data/file.csv --odd data/odd.xlsx

# Streamlit UI
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

## Conventions
- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor: 80% (`--cov-fail-under=80`), currently at 89%
