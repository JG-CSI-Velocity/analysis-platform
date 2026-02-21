# Technical Reference

Internal developer documentation for the Analysis Platform. Not for end users.

---

## Architecture

**uv workspace monorepo** -- five packages share a single lockfile and virtual environment.

```
analysis_platform/
  packages/
    shared/           Types, context, config, helpers, format_odd, charts
    ars_analysis/     ARS pipeline: 8 analytics modules, deck builder, Excel formatter
    txn_analysis/     TXN pipeline: 35 analyses (M1-M14 + scorecard), Plotly charts
    ics_toolkit/      ICS pipeline: 37 analyses + append + referral intelligence
    platform_app/     Orchestrator, Streamlit UI (7 pages), module registry, CLI
  tests/
    shared/           93 tests
    ars/              545 tests
    txn/              597 tests
    ics/              1,049 tests (including 212 referral)
    platform/         60 tests
    integration/      26 E2E tests (12 orchestrator + 14 CLI)
    e2e_data/         Synthetic data fixtures
```

### Pipeline Pattern

All three pipelines follow the same architecture:

```
Pydantic Settings -> data_loader.load_data() -> run_all_analyses() -> export_outputs()
                                                      |
                                                ANALYSIS_REGISTRY
                                                [(name, fn), ...]
                                                      |
                                            Each fn(df, settings, ctx)
                                                      |
                                                -> AnalysisResult
```

**AnalysisResult**: One canonical frozen dataclass in `shared.types` with `from_df()` factory. Re-exported by ICS and TXN `base.py`. ARS keeps its own mutable type internally; `runner.py` converts at the boundary.

### Orchestrator

`platform_app/orchestrator.py` dispatches to pipeline runners:

```python
run_pipeline("ars", input_files={"oddd": Path(...)}, output_dir=Path(...))
run_pipeline("txn", input_files={"tran": Path(...)}, output_dir=Path(...))
run_pipeline("ics", input_files={"ics": Path(...)}, output_dir=Path(...))
```

Auto-detection: if no pipelines specified, `_detect_pipelines()` checks which input file keys are present.

### Module Registry

`platform_app/core/module_registry.py` -- 80 `ModuleInfo` entries across 3 `Product` enums (ARS, TXN, ICS). Each entry has: key, name, product, category, status (STABLE/BETA/DRAFT), description, depends_on, run_order, output_types.

Templates in `platform_app/core/templates.py` -- 6 built-in presets (Core ARS, Full ARS, TXN Essential, etc.) + user-defined YAML templates.

---

## Key Types

| Type | Location | Purpose |
|------|----------|---------|
| `AnalysisResult` | `shared.types` | Canonical result (slide_id, title, df, chart_path, success) |
| `PipelineContext` | `shared.context` | Shared context (client_id, input_files, output_dir, chart_dir) |
| `PipelineConfig` | `shared.config` | Pydantic settings for pipeline behavior |
| `FormatStatus` | `shared.format_odd` | Frozen dataclass for ODD format validation results |
| `RunRecord` | `platform_app.core.run_logger` | JSONL log entry for each pipeline run |
| `ClientWorkspace` | `platform_app.core.session_manager` | CSM/client/files workspace resolution |
| `ModuleInfo` | `platform_app.core.module_registry` | Module metadata for the library UI |

---

## ODD Format Validation

Header-only column detection (~50ms via openpyxl `read_only=True`) determines file readiness.

**ARS check** (`check_odd_formatted`): Looks for 5 signature columns added by `format_odd()`:
- `Total Spend`, `Total Swipes`, `SwipeCat12`, `Account Holder Age`, `Response Grouping`
- Threshold: 3 of 5 (handles edge cases like missing DOB)

**ICS check** (`check_ics_ready`): Looks for 2 columns added by ICS append:
- `ICS Account`, `ICS Source`
- Threshold: 2 of 2 (both required)

**Format pipeline** (`format_odd(df)` in `shared/format_odd.py`): 7 steps:
1. Drop PYTD/YTD columns
2. Calculate totals, monthly averages, swipe categories
3. Combine PIN+Sig into per-month Spend/Swipes
4. Age calculations (DOB -> holder age, Date Opened -> account age)
5. Mail & Response grouping (offers, responses, Response Grouping)
6. Control segmentation (Control/Responder/Non-Responder per month)

**UI gates**: Workspace shows badges, Data Ingestion shows warnings + "Format Now" button, Run Analysis blocks execution if not ready.

---

## Streamlit UI Pages

| Page | File | Purpose |
|------|------|---------|
| Home | `pages/home.py` | Dashboard with metrics, product cards, workflow steps, recent runs |
| Workspace | `pages/workspace.py` | CSM + client folder selection, auto-detect files, format badges |
| Data Ingestion | `pages/data_ingestion.py` | Upload/server path/directory scan, format validation, data profiling |
| Module Library | `pages/module_library.py` | Browse/search/select modules by product tab, templates, bulk select |
| Run Analysis | `pages/run_analysis.py` | Pre-flight checks, format gates, execution with progress, logging |
| Batch Run | `pages/batch_workflow.py` | Multi-pipeline sequential execution |
| View Outputs | `pages/outputs.py` | Result display, chart preview, downloads |
| Run History | `pages/run_history.py` | JSONL log table with filters |

**Session state keys**:
- `uap_file_oddd`, `uap_file_tran`, `uap_file_ics`, `uap_file_odd` -- file paths
- `uap_selected_modules` -- set of module keys
- `uap_workspace` -- ClientWorkspace object
- `uap_csm`, `uap_client_id`, `uap_client_name` -- identifiers
- `_oddd_ars_status`, `_oddd_ics_status` -- FormatStatus from validation

**Theme**: Bloomberg-terminal aesthetic. Dark sidebar, JetBrains Mono for labels, DM Sans for content. CSS variables prefixed `--uap-`.

---

## ARS Pipeline Internals

### Analytics Modules

8 module packages in `ars_analysis/analytics/`:

| Module | Package | Slide IDs | Charts |
|--------|---------|-----------|--------|
| Overview | `overview/` (stat_codes, product_codes, eligibility) | A1-A5 | 5 |
| DCTR | `dctr/` (penetration, trends, branches, funnel, overlays) | DCTR-1 to DCTR-16, A7.x | 19 |
| Reg E | `reg_e/` (status, branches, dimensions) | A8.x | 10 |
| Attrition | `attrition/` (rates, dimensions, impact) | A9.1-A9.13 | 13 |
| Value | `value/` (analysis) | A11.x | 2 |
| Mailer Insights | `mailer/insights/` | A12.x | per-month |
| Mailer Response | `mailer/response/` | A13-A14 | 6+ |
| Mailer Impact | `mailer/impact/` | A15.x | 4 |

Each module uses ABC + `@register` pattern. Error isolation via `_safe()` wrapper returns `AnalysisResult(success=False)` on failure.

### Deck Builder

Template: `Template12.25.pptx` (14 layouts). Key layout indices:
- [2] Divider (section title)
- [5] Chart (title + picture + text)
- [11] Blank

Placeholder map: ph[0]=title, ph[13]=subtitle, ph[14]=picture, ph[26]=text header, ph[19]=text body.

Section grouping: Slide ID prefix maps to sections. Consolidation reorders slides into main + appendix with section dividers.

### Chart Patterns

- **Leak guard**: `fig = None` before try, `fig = None` after save, `finally: plt.close(fig)`
- **chart_figure()**: Context manager with style isolation + guaranteed cleanup
- **Copy-on-Write**: `pd.set_option("mode.copy_on_write", True)` at load time
- **Date pre-parse**: Once at load, not repeated downstream

---

## TXN Pipeline Internals

35 analyses in `ANALYSIS_REGISTRY`. M1-M10 are native. M11-M14 use storyline adapters (thin wrappers around V4 code). Scorecard is final.

Plotly charts exported via `kaleido==0.2.1` (pinned -- v1.0+ has 50x regression).

Storyline adapter pattern: lazy import inside function body, converts pipeline args to V4 ctx dict, wraps result back to AnalysisResult.

---

## ICS Pipeline Internals

Three sub-pipelines:

- **Analysis** (`ics_toolkit/analysis/`): 37 registered analyses, Plotly charts, PPTX deck with section dividers
- **Append** (`ics_toolkit/append/`): 5-step matching pipeline, adds `ICS Account` (Yes/No) and `ICS Source` (REF/DM/Both) to ODD
- **Referral** (`ics_toolkit/referral/`): 8-step pipeline with entity normalization, temporal signals, network inference, influence scoring (0-100)

---

## Commands

```bash
# Development
make test          # all tests (~2,400, ~2.5 min)
make cov           # tests + coverage
make lint          # ruff check + format check
make fmt           # auto-fix lint + format

# Per-package
uv run pytest tests/ars/ -q
uv run pytest tests/txn/ -q
uv run pytest tests/ics/ -q
uv run pytest tests/shared/ -q
uv run pytest tests/integration/ -q

# Pipeline CLIs
uv run python -m ars_analysis --help
uv run python -m txn_analysis --help
uv run python -m ics_toolkit --help

# E2E smoke tests (synthetic data)
uv run python -m txn_analysis tests/e2e_data/8888_transactions.csv -o /tmp/txn_out
uv run python -m ics_toolkit analyze tests/e2e_data/9999_ICS_2026.01.xlsx -o /tmp/ics_out --client-id 9999
uv run python -m ars_analysis run "tests/e2e_data/1200_Test CU_2026.02.xlsx" --output-dir /tmp/ars_out

# Streamlit UI
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

---

## Conventions

- **Commits**: Conventional format -- `feat(scope):`, `fix(scope):`, `refactor(scope):`
- **Config**: Pydantic v2 with `ConfigDict(extra="forbid")` on all settings models
- **Charts**: kaleido==0.2.1 pinned (v1.0+ has 50x regression)
- **Lint**: `ruff check` + `ruff format` must pass before push
- **Tests**: Must pass before push. CI coverage floor: 80% (`--cov-fail-under=80`), currently 94%.
- **Python**: Target 3.11+. Line length 100.

---

## Known Gotchas

- `callable | None` fails on Python 3.12 -- use `Callable | None` from typing
- pandas `freq="M"` deprecated -- use `freq="ME"` (month-end)
- python-pptx `prs.slides` does NOT support slice indexing -- use `enumerate()` + skip
- kaleido deprecation warnings are noisy but harmless (pinned at 0.2.1)
- Grand Total rows via `pd.concat` can introduce object dtype -- always `pd.to_numeric(errors="coerce")`
- Excel `"0.0%"` format auto-multiplies by 100 -- use `'0.0"%"'` when values are already 0-100
- When removing enum values (e.g. `Product.TXN_V4`), grep ALL files including Streamlit pages -- they crash at import time, not runtime

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `packages/shared/src/shared/types.py` | Canonical `AnalysisResult` |
| `packages/shared/src/shared/format_odd.py` | ODD formatting + validation checks |
| `packages/shared/src/shared/helpers.py` | `safe_percentage()`, `safe_ratio()` |
| `packages/shared/src/shared/context.py` | `PipelineContext` dataclass |
| `packages/txn_analysis/src/txn_analysis/analyses/__init__.py` | ANALYSIS_REGISTRY (35 entries) |
| `packages/txn_analysis/src/txn_analysis/analyses/storyline_adapters.py` | V4 bridge for M11-M14 |
| `packages/ics_toolkit/src/ics_toolkit/cli.py` | ICS CLI entry point |
| `packages/ars_analysis/src/ars_analysis/cli.py` | ARS CLI entry point |
| `packages/platform_app/src/platform_app/orchestrator.py` | Pipeline dispatcher |
| `packages/platform_app/src/platform_app/core/module_registry.py` | 80-module unified registry |
| `packages/platform_app/src/platform_app/app.py` | Streamlit entry point + theme CSS |
| `config/platform.yaml` | Global platform config |
| `.github/workflows/ci.yml` | CI: lint + test + coverage floor |
| `tests/e2e_data/generate_fixtures.py` | Synthetic data fixture generator |

---

## Open Issues

| # | Priority | Description |
|---|----------|-------------|
| #24 | High | Network path FileNotFoundError when formatting on M: drive (xlsxwriter temp file) |
| #23 | Medium | Comprehensive competitor config with 3-tier matching |

## Deployment Checklist

- [ ] Windows .bat scripts validated on M: drive
- [ ] Real client ODD/ICS/TXN files tested (not just synthetic)
- [ ] M: drive path configured in `config/platform.yaml`
- [ ] `clients_config.json` populated with client-specific settings
- [ ] PowerPoint template placed at expected path
