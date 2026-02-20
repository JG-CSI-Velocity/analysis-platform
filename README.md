# Analysis Platform

Unified banking analysis platform combining ARS, Transaction, and ICS pipelines into a single monorepo with shared infrastructure.

## Architecture

```
analysis_platform/
  packages/
    shared/           Shared types, context, and config (PipelineContext, AnalysisResult)
    ars_analysis/     ARS pipeline (70+ analyses, PPTX deck, Excel reports)
    txn_analysis/     Transaction pipeline (35 analyses: M1-M14 + scorecard)
    ics_toolkit/      ICS pipeline (37 analyses + append + referral intelligence)
    platform_app/     Orchestrator, CLI, and Streamlit UI
  tests/
    ars/              ARS unit tests (545 tests)
    txn/              Transaction unit tests
    ics/              ICS unit tests
    shared/           Shared package unit tests (50 tests)
    platform/         Orchestrator and CLI tests
    integration/      End-to-end pipeline tests
```

**uv workspace monorepo** -- all five packages share a single lockfile and virtual environment.

## Quickstart (New Machine)

### 1. Clone

```
git clone https://github.com/JG-CSI-Velocity/analysis-platform.git
cd analysis-platform
```

### 2. Install uv (if not already installed)

```
pip install uv
```

### 3. Install Python and dependencies

```
uv python install 3.11
uv sync --all-packages
```

### 4. Verify everything works

```
uv run pytest tests/ -v
```

Should see ~2,305 tests pass (~2 min on macOS). Windows auto-skips ~100 kaleido-dependent tests.

---

## ARS Pipeline

The Account Revenue Solution (ARS) pipeline analyzes ODDD (Overdraft/Debit Data Dump) Excel files to produce consultant-grade PowerPoint presentations and detailed Excel reports.

### Running ARS

**Python one-liner (recommended):**
```
uv run python -c "from ars_analysis.pipeline import run_pipeline; run_pipeline(r'path\to\1776-2026-02-ClientName-ODD.xlsx')"
```

**Python API:**
```python
from ars_analysis.pipeline import run_pipeline

ctx = run_pipeline(
    file_path=r"M:\...\1776-2026-02-CoastHills CU-ODD.xlsx",
    # Optional overrides:
    config_path=None,       # defaults to M:\ARS\Config\clients_config.json
    template_path=None,     # defaults to M:\ARS\Template\Template12.25.pptx
    progress_callback=None, # for Streamlit integration
)

# Access results
print(f"Slides: {len(ctx['all_slides'])}")
print(f"PPTX built: {ctx['pptx_built']}")
print(f"Exports: {len(ctx['export_log'])}")
```

### Input File Convention

The ODD file **must** follow this naming pattern:

```
{ClientID}-{year}-{month}-{ClientName}-ODD.xlsx
```

Examples:
- `1776-2026-02-CoastHills CU-ODD.xlsx`
- `9999-2025-12-Example CU-ODD.xlsx`

The parser splits on `-` and expects exactly: ClientID, year, month, name (may contain hyphens), ODD.

### Path Configuration

All paths resolve from `ARS_BASE` (default: `M:\ARS`). Override via:

1. `ARS_BASE` environment variable
2. `ars_config.toml` file in the package root (gitignored, for dev/testing)
3. Falls back to `M:\ARS`

```
M:\ARS\
  Config\
    clients_config.json    Client-specific settings (prod codes, IC rate, fees)
  Template\
    Template12.25.pptx     PowerPoint template (14 layouts, indices 0-13)
  Output\
    Archive\{ClientName}\{year}\{month}\   Monthly archive copies
  Input\                   Watch folder (for future auto-processing)
```

### Pipeline Phases

| Phase | Label | What it does |
|-------|-------|-------------|
| 1 | Setup | Load ODD, parse filename, load config, clean data, build subsets, init deck |
| 2 | A1-A5 | Portfolio overview: stat codes, debit penetration, eligibility funnel, opening trends, branch distribution |
| 2b | A9 | Attrition suite (13 analyses): overall rate, closure duration, open vs closed, debit/mailer impact, revenue loss, velocity, branch/product/tenure/balance breakdowns |
| 3 | A6+A7 | DCTR suite (25+ analyses): take rates, trends, funnels, branch heatmaps, seasonality, vintage curves, decade analysis |
| 3b | A8 | Reg E suite (13 analyses): opt-in status, trends, age/branch/product breakdowns, volume vs rate scatter |
| 3c | A11 | Value suite: debit card value, Reg E opt-in value (revenue per account, portfolio potential) |
| 3d | A12 | Mailer Insights: per-month swipes/spend analysis with 1-mo, 3-mo, 6-mo deltas |
| 3e | A13+A14 | Mailer Response: monthly summaries, aggregate summary, rate/count trends, account age distribution |
| 3f | A15 | Market Impact: market reach, spend composition, revenue attribution, pre/post mailer delta |
| 4 | PowerPoint | Build 78-slide deck from 13 preamble + ordered analysis slides |
| -- | Archive | Copy Excel to master + monthly archive on M: drive |

### Analysis Modules

| Module | File | Analyses | Main slides | Appendix slides |
|--------|------|----------|-------------|-----------------|
| Overview | `pipeline.py` | A1-A5 | 5 | -- |
| DCTR | `dctr.py` | 25+ | 5 | 9 |
| Reg E | `reg_e.py` | 13 | 4 | 6 |
| Attrition | `attrition.py` | 13 | 6 | 6 |
| Value | `value.py` | 2 | 2 (wired into DCTR/Reg E sections) | -- |
| Mailer Insights | `mailer_insights.py` | per-month | 3 per recent month | older months to appendix |
| Mailer Response | `mailer_response.py` | 6+ | summaries + trends | aggregate + demographics |
| Mailer Impact | `mailer_impact.py` | 4 | market reach, spend, revenue, delta | -- |

Supporting modules:
- `helpers.py` -- shared `_report`, `_fig`, `_save_chart`, `_slide`, `_save` across all suites
- `chart_style.py` -- matplotlib color palette, font sizes, `PCT_FORMATTER`
- `deck_builder.py` -- `SlideContent` dataclass, `DeckBuilder` class, `setup_slide_helpers()`
- `ars_config.py` -- path resolution (`ARS_BASE`, `CONFIG_PATH`, `TEMPLATE_PATH`)
- `mailer_common.py` -- shared mailer column detection, responder identification

### PowerPoint Template Layouts

The CSI template (`Template12.25.pptx`) has 14 slide layouts (indices 0-13):

| Index | Name | Used for |
|-------|------|----------|
| 0 | Cover - Dark | Financial Performance (blank, manual) |
| 1 | Cover - Left text | Title slides, section intros |
| 2 | Divider | Section dividers, All Program Results |
| 4 | Chart + header | Branch distribution, attrition breakdowns |
| 5 | Chart + KPI | Attrition overview, debit card impact |
| 6 | Side-by-side | DCTR comparisons, Reg E funnels |
| 8 | Blank flexible | Agenda, ARS Lift Matrix, DCO |
| 9 | Centered chart | Reg E trends, DCTR heatmaps, vintage curves |
| 12 | Blank flexible | Monthly Revenue, Summary & Takeaways |
| 13 | Full-width spaced | Mailer summaries, branch trends, value slides |

### Output Files

For a run like `1776-2026-02-CoastHills CU-ODD.xlsx`, the pipeline produces:

**Source folder** (beside the ODD file):
- `1776-2026-02-ars-analysis.xlsx` -- detailed Excel with tabs per analysis
- `1776-2026-02-CoastHills CU-presentation.pptx` -- 78-slide consultant deck
- `charts/` -- 70+ PNG chart images (matplotlib, 150 DPI)

**Master Excel** (cumulative):
- `M:\ARS\Output\Presentation Excels\1776-master-CoastHills CU-ars-analysis.xlsx`

**Archive** (monthly copy):
- `M:\ARS\Output\Archive\CoastHills CU\2026\02\`

### Deck Structure

The PowerPoint follows a fixed section order:

1. **Preamble** (13 slides) -- title, agenda, program performance, financial placeholders, mailer revisit, DCO, mailer summaries header
2. **Recent Mailer Summaries** -- most recent 2-3 months' composite slides + swipes/spend charts
3. **DCTR** -- 5 main comparison/funnel/trend slides + value slide
4. **Reg E** -- 4 main trend/funnel/age/branch slides + value slide
5. **Attrition** -- 6 main slides (overview, profile, debit/mailer impact, revenue, velocity)
6. **Summary & Key Takeaways** -- blank placeholder for manual content
7. **Appendix** -- older mailer months, then DCTR/Reg E/Attrition detail slides, aggregate mailer, impact metrics

Slides are automatically consolidated (e.g., 17 DCTR analyses -> 5 main + 9 appendix) and reordered by the pipeline.

---

## Transaction Pipeline

### CLI

```
uv run python -m txn_analysis data/transactions.csv
```

### Python API

```python
from txn_analysis import run_client
run_client("data/transactions.csv")
```

35 analyses (M1-M14 + scorecard), 19+ charts. M11-M14 (Demographics, Campaigns, Payroll, Lifecycle) require optional ODD file.

---

## ICS Pipeline

### CLI

```
uv run python -m ics_toolkit analyze data/ics_data.xlsx
uv run python -m ics_toolkit append run-all
uv run python -m ics_toolkit referral data/referral_file.xlsx
```

37 analyses + Plotly charts + PPTX output. Append pipeline for organizing/merging/matching ICS accounts.

### Referral Intelligence

```
uv run python -m ics_toolkit referral data/referral_file.xlsx
```

```python
from ics_toolkit import run_referral
run_referral("data/referral_file.xlsx")
```

8-step pipeline: data loading, entity normalization, code decoding, temporal signals, network inference, influence scoring (0-100), 8 analysis artifacts, 5 Plotly chart builders. Configurable scoring weights, burst/dormancy thresholds, and code prefix mapping via `config.yaml`.

---

## Pipelines Summary

| Pipeline | Input File | Output |
|----------|------------|--------|
| ARS | `{ClientID}-{year}-{month}-{name}-ODD.xlsx` | Excel + PPTX + charts |
| Transaction | CSV: `merchant_name`, `amount`, `primary_account_num`, `transaction_date`, `mcc_code` + optional ODD Excel | Excel + PNG charts |
| ICS Analysis | ICS Excel/CSV | Excel + Plotly charts + PPTX |
| ICS Append | Directory of ICS source files | Merged/organized output |
| ICS Referral | Referral Excel/CSV | Excel + Plotly charts + PPTX |

## Tests

Run all tests:

```
uv run pytest tests/ -v
```

Run by package:

```
uv run pytest tests/ars/ -v              # 545 ARS tests
uv run pytest tests/txn/ -v              # Transaction tests
uv run pytest tests/ics/ -v              # ICS tests (incl. 212 referral)
uv run pytest tests/ics/referral/ -v     # Referral tests only
uv run pytest tests/shared/ -v           # 50 shared tests
```

Using make (macOS/Linux):

```
make test    # all tests
make cov     # tests + coverage report
make lint    # ruff check + format check
make fmt     # auto-fix lint + format
```

**~2,305 tests, ~2 min runtime.** Windows auto-skips ~100 kaleido-dependent tests (chart PNG export hangs on Windows).

## Lint

```
uv run ruff check .
uv run ruff format --check .
```

## CI

GitHub Actions workflow runs on push/PR to main:
1. **lint** -- ruff check + format
2. **test** -- unit tests with `--cov-fail-under=80` on Python 3.12

## Key Dependencies

- pandas, numpy -- data processing
- matplotlib -- ARS chart generation
- plotly + kaleido==0.2.1 -- ICS/TXN chart generation (kaleido pinned; v1.0+ has 50x perf regression)
- openpyxl -- Excel read/write
- python-pptx -- PowerPoint generation
- pydantic + pyyaml -- config validation
- streamlit -- web UI (UAP V2.0 unified dashboard with module registry)

## Windows Notes

- `make` is not available -- use `uv run pytest tests/ -v` directly
- kaleido v0.2.1 hangs indefinitely on Windows during Plotly PNG export; tests auto-skip via `tests/conftest.py`
- Validate chart output via real PowerPoint decks instead of unit tests on Windows
