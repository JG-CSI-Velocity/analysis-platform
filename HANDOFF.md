# CSI Velocity -- Repository Roadmap & Session Handoff

**Date:** 2026-02-20
**Repo:** https://github.com/JG-CSI-Velocity/analysis-platform
**Location:** `/Users/jgmbp/Desktop/ARS-pwrpt/analysis-platform/`
**Current branch:** `main`
**Working tree:** CLEAN

---

## 1. Current State (verified 2026-02-20)

### Numbers

| Metric | Value |
|--------|-------|
| Tests | **2,358 passing** |
| Coverage | **94%** (CI floor 80%) |
| Lint | Clean (ruff check + ruff format) |
| Open PRs | 0 |
| Open Issues | 2 (#23 competitor config, #24 M: drive bug) |
| Branches | `main` only (local + remote) |

### Recent Milestones

| PR | What |
|----|------|
| #21 | CLI E2E tests -- 14 integration tests exercising all 3 pipeline CLIs |
| #20 | Synthetic E2E data fixtures + pipeline validation (TXN 35/35, ICS 80/80, ARS 20/20) |
| #19 | Unified AnalysisResult (4 definitions -> 1 in shared.types) + deduplicated helpers |
| #18 | ARS CLI fix (`__main__.py`) |
| #17 | V4 consolidation -- killed entire V4 parallel pipeline, unified to 35 TXN analyses |
| #9 | ICS Referral Intelligence Engine (212 tests, 8-step pipeline) |
| #4 | ARS v2 modular pipeline migration (545 tests, 20 analytics modules) |

### Active Roadmap

See `plans/chore-unified-consolidation.md` -- Phases 1-4 complete. Phase 5 (decompose storyline monoliths) deferred. Phase 6 (features) deferred.

---

## 2. Project Structure

```
analysis_platform/
  packages/
    shared/           Shared types, context, config, helpers (81 tests)
    ars_analysis/     ARS pipeline (70+ analyses, PPTX deck, 545 tests)
    txn_analysis/     Transaction pipeline (35 analyses: M1-M14 + scorecard, 597 tests)
    ics_toolkit/      ICS pipeline (37 analyses + append + referral, 1049 tests)
    platform_app/     Orchestrator, CLI, Streamlit UI (60 tests)
  tests/
    shared/           Shared tests (81)
    ars/              ARS tests (545)
    txn/              Transaction tests (597)
    ics/              ICS tests (1049, including ics/referral/ -- 212)
    platform/         Platform tests (60)
    integration/      E2E tests (26: 12 orchestrator + 14 CLI)
    e2e_data/         Synthetic data fixtures for pipeline validation
```

### Key Architecture

**AnalysisResult**: 1 canonical frozen dataclass in `shared.types` with `from_df()` factory. Re-exported by ICS and TXN `base.py`. ARS keeps its own mutable type internally; `runner.py` converts at the boundary.

**Pipeline Pattern** (all 3 pipelines):
```
Settings (Pydantic) -> data_loader.load_data() -> run_all_analyses() -> export_outputs()
                                                        |
                                                  ANALYSIS_REGISTRY
                                                  [(name, fn), ...]
                                                        |
                                              Each fn(df, settings, ctx)
                                                        |
                                                  -> AnalysisResult
```

**Shared helpers**: `safe_percentage()` and `safe_ratio()` in `shared.helpers`, re-exported by ICS and TXN `base.py`.

---

## 3. What Needs Attention

### High Priority (when deploying)

- **Issue #24**: Network path FileNotFoundError when formatting on M: drive (xlsxwriter temp file issue)
- **Windows .bat validation**: `run.bat`, `dashboard.bat`, `run_batch.bat` need testing on Windows M: drive
- **Real-data validation**: E2E done with synthetic data; needs real client ODD/ICS/TXN files from M: drive

### Medium Priority

- **Issue #23**: Comprehensive competitor config with 3-tier matching (migrated from txn-analysis #10 + #13)
- **Reg E Enhancement**: 5-sprint plan in `plans/feat-reg-e-enhancement.md`

### Low Priority

- **Decompose storyline monoliths**: S5/S7/S8/S9 (838-1296 LOC each) behind thin adapters in `storyline_adapters.py`. Working correctly but large.
- **Chart formatting fixes**: Spine removal, positioning consistency
- **Cross-pipeline dashboard**: Unified results viewer across ARS/TXN/ICS
- **PPTX template system**: Branded deck generation

### Done (this session)

- Standalone repos archived: `txn-analysis`, `ars-pipeline`, `ics_toolkit`, `ars_analysis-jupyter`
- Standalone issues migrated: txn-analysis #10+#13 -> #23, ars-pipeline #10 -> #24
- CI caching enabled via `astral-sh/setup-uv` `enable-cache: true`

---

## 4. Commands Quick Reference

```bash
# Development
make test          # all tests (~2,358, ~2.5 min)
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package
uv run pytest tests/ars/ -q          # ARS only (545)
uv run pytest tests/txn/ -q          # TXN only (597)
uv run pytest tests/ics/ -q          # ICS only (1049)
uv run pytest tests/integration/ -q  # E2E only (26)

# Pipeline CLIs
uv run python -m ars_analysis --help
uv run python -m ics_toolkit --help
uv run python -m txn_analysis --help

# E2E pipeline smoke tests (synthetic data)
uv run python -m txn_analysis tests/e2e_data/8888_transactions.csv -o /tmp/txn_out
uv run python -m ics_toolkit analyze tests/e2e_data/9999_ICS_2026.01.xlsx -o /tmp/ics_out --client-id 9999
uv run python -m ars_analysis run "tests/e2e_data/1200_Test CU_2026.02.xlsx" --output-dir /tmp/ars_out

# Streamlit UI
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

---

## 5. Conventions

- Conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`
- Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- `kaleido==0.2.1` pinned (v1.0+ has 50x regression)
- `ruff check` + `ruff format` must pass before push
- Tests must pass before push
- CI coverage floor: 80% (`--cov-fail-under=80`), currently at 94%

---

## 6. Known Gotchas

- `callable | None` type hint fails on Python 3.12 -- use `Callable | None` from typing
- pandas `freq="M"` deprecated -- use `freq="ME"` (month-end)
- python-pptx `prs.slides` does NOT support slice indexing -- use `enumerate()` + skip
- kaleido deprecation warnings are noisy but harmless (pinned at 0.2.1)
- ARS suite runners overwrite `ctx["_save_to_excel"]` -- test results/slides, not mock call counts
- Grand Total rows via `pd.concat` can introduce object dtype -- always `pd.to_numeric(errors="coerce")`
- Excel `"0.0%"` format auto-multiplies by 100 -- use `'0.0"%"'` when values are already 0-100
- Storyline adapter pattern: thin wrapper converting pipeline args to V4 ctx dict + wrapping result back to AnalysisResult. Lazy imports inside function body.
- When removing enum values (e.g. `Product.TXN_V4`), grep ALL files including Streamlit pages -- they crash at import time, not runtime.

---

## 7. Key Files Reference

| File | What It Does |
|------|-------------|
| `packages/shared/src/shared/types.py` | Canonical `AnalysisResult` (used by all pipelines) |
| `packages/shared/src/shared/helpers.py` | `safe_percentage()`, `safe_ratio()` (used by ICS + TXN) |
| `packages/txn_analysis/src/txn_analysis/analyses/__init__.py` | ANALYSIS_REGISTRY (35 entries), `run_all_analyses()` |
| `packages/txn_analysis/src/txn_analysis/analyses/storyline_adapters.py` | Bridges S5/S7/S8/S9 into registry |
| `packages/txn_analysis/src/txn_analysis/pipeline.py` | Main TXN pipeline entry point |
| `packages/txn_analysis/src/txn_analysis/settings.py` | Pydantic Settings with all TXN config |
| `packages/ics_toolkit/src/ics_toolkit/cli.py` | ICS CLI (analyze, referral, append subcommands) |
| `packages/ars_analysis/src/ars_analysis/cli.py` | ARS CLI (run, batch, retrieve, format, validate, etc.) |
| `packages/platform_app/src/platform_app/orchestrator.py` | Pipeline dispatcher (ars, txn, ics) |
| `packages/platform_app/src/platform_app/core/module_registry.py` | Unified module registry (ARS + TXN + ICS) |
| `tests/integration/test_cli_e2e.py` | 14 CLI E2E tests for all 3 pipelines |
| `tests/e2e_data/generate_fixtures.py` | Generates synthetic data fixtures |
| `.github/workflows/ci.yml` | CI config (lint + test + coverage floor 80%) |
| `plans/chore-unified-consolidation.md` | Unified consolidation plan (Phases 1-4 done) |
