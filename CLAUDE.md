# Analysis Platform -- Claude Code Instructions

## Current State (2026-02-20)

**Monorepo health:** CI green, 2,358 tests, 94% coverage, 0 open PRs, 0 open issues.

### Recent milestones
- **PR #21**: CLI E2E tests -- 14 integration tests exercising all 3 pipeline CLIs with synthetic data
- **PR #20**: Synthetic E2E data fixtures + pipeline validation (TXN 35/35, ICS 80/80, ARS 20/20)
- **PR #19**: Unified AnalysisResult (4 definitions -> 1 canonical in shared.types), deduplicated helpers
- **PR #17**: V4 consolidation -- killed entire V4 parallel pipeline, unified to 35 analyses (M1-M14 + scorecard)
- **PR #18**: ARS CLI fix (`__main__.py`)
- **PR #4**: ARS v2 modular pipeline migration (545 tests, 20 analytics modules)
- **PR #9**: ICS Referral Intelligence Engine (212 tests, 8-step pipeline)

### Active roadmap
- See `plans/chore-unified-consolidation.md` for the unified path forward (Phases 1-4 done)
- Remaining: Phase 5 (decompose storyline monoliths, optional), Phase 6 (deferred features)

### What needs attention
- **Windows .bat validation**: `run.bat`, `dashboard.bat`, `run_batch.bat` need testing on Windows M: drive.
- **Standalone repo archival**: `ars-pipeline`, `ars_analysis-jupyter`, `ics_toolkit`, `ics_append` are superseded by this monorepo.
- **Real-data validation on Windows**: E2E done with synthetic data; needs real client ODD/ICS/TXN files from M: drive.

---

## Project Structure

```
analysis_platform/
  packages/
    shared/           Shared types, context, config, helpers (81 tests)
    ars_analysis/     ARS pipeline (70+ analyses, PPTX deck, 545 tests)
    txn_analysis/     Transaction pipeline (35 analyses: M1-M14 + scorecard, 597 tests)
    ics_toolkit/      ICS pipeline (37 analyses + append + referral, 1049 tests)
    platform_app/     Orchestrator, CLI, Streamlit UI (60 tests)
  tests/
    ars/              ARS tests (545)
    txn/              Transaction tests (597)
    ics/              ICS tests (1049, including ics/referral/ -- 212)
    shared/           Shared tests (81)
    platform/         Platform tests (60)
    integration/      E2E tests (26: 12 orchestrator + 14 CLI)
    e2e_data/         Synthetic data fixtures for pipeline validation
```

## Commands

```bash
# Development
make test          # all tests (~2,358, ~2.5 min)
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

# E2E pipeline smoke tests (synthetic data)
uv run python -m txn_analysis tests/e2e_data/8888_transactions.csv -o /tmp/txn_out
uv run python -m ics_toolkit analyze tests/e2e_data/9999_ICS_2026.01.xlsx -o /tmp/ics_out --client-id 9999
uv run python -m ars_analysis run "tests/e2e_data/1200_Test CU_2026.02.xlsx" --output-dir /tmp/ars_out

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
- CI coverage floor: 80% (`--cov-fail-under=80`), currently at 94%
