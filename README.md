# Analysis Platform

Unified banking analysis platform combining ARS, Transaction, and ICS pipelines into a single monorepo with shared infrastructure.

## Architecture

```
analysis_platform/
  packages/
    shared/           Shared types, context, and config (PipelineContext, AnalysisResult)
    ars_analysis/     ARS pipeline (A1-A15 analyses, DCTR, Reg E, Value, Attrition)
    txn_analysis/     Transaction pipeline (M1-M10 base + V4 S1-S9 storylines)
    ics_toolkit/      ICS pipeline (37 analyses + append pipeline)
    platform_app/     Orchestrator, CLI, and Streamlit UI
  tests/
    ars/              ARS unit tests
    txn/              Transaction unit tests
    ics/              ICS unit tests
    platform/         Orchestrator and CLI tests
    integration/      End-to-end pipeline tests
```

**uv workspace monorepo** -- all five packages share a single lockfile and virtual environment.

## Setup

```
uv sync --all-packages
```

## Running Analyses

### CLI

Run a single pipeline:

```
uv run python -m platform_app run --pipeline txn --tran data/transactions.csv --client-id 1234
```

Run all applicable pipelines (auto-detected from input files):

```
uv run python -m platform_app run-all --data-dir data/ --client-id 1234
```

### Streamlit UI

```
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

Per-pipeline pages are available in the sidebar: ARS, Transaction, and ICS.

### Python API

```python
from platform_app.orchestrator import run_pipeline, run_all
from pathlib import Path

# Single pipeline
results = run_pipeline(
    "txn",
    input_files={"tran": Path("data/transactions.csv")},
    output_dir=Path("output"),
    client_id="1234",
    client_name="Example CU",
)

# Auto-detect and run all
all_results = run_all(
    input_files={"tran": Path("data/tx.csv"), "ics": Path("data/ics.xlsx")},
    output_dir=Path("output"),
)
```

## Pipelines

| Pipeline | Key | Input File | Analyses |
|----------|-----|------------|----------|
| ARS | `ars` | ODDD Excel (`{ClientID}-{year}-{month}-{name}-ODD.xlsx`) | A1-A15 + DCTR, Reg E, Value, Attrition |
| Transaction (Base) | `txn` | CSV with `merchant_name`, `amount`, `primary_account_num`, `transaction_date`, `mcc_code` | M1-M10 (31 analyses, 19 charts) |
| Transaction (V4) | `txn_v4` | Tab-delimited transaction files + ODD Excel + YAML config | S1-S9 storylines (99+ analyses) |
| ICS Analysis | `ics` | ICS Excel/CSV | 37 analyses + Plotly charts + PPTX |
| ICS Append | `ics_append` | Base directory of ICS source files | Organize, merge, match pipeline |

## Tests

Run all tests:

```
uv run pytest tests/ -v
```

Run unit tests only:

```
uv run pytest tests/ --ignore=tests/integration -v
```

Run integration tests only:

```
uv run pytest tests/integration/ -v
```

**866 tests, ~57s runtime.**

## Lint

```
uv run ruff check .
uv run ruff format --check .
```

## CI

GitHub Actions workflow runs on push/PR to main:
1. **lint** -- ruff check + format
2. **test** -- unit tests + integration tests on Python 3.11

## Key Dependencies

- pandas, numpy -- data processing
- plotly + kaleido==0.2.1 -- chart generation (kaleido pinned; v1.0+ has perf regression)
- openpyxl -- Excel read/write
- python-pptx -- PowerPoint generation
- pydantic + pyyaml -- config validation
- typer + rich -- CLI
- streamlit -- web UI
