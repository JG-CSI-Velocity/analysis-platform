# Streamlit Platform UI Integration

**Status:** Complete (Phase 1-6)
**Branch:** `feat/streamlit-ui`
**Package:** `packages/platform_app/`

---

## Overview

The Streamlit app provides a browser-based UI for running ARS, TXN, and ICS analysis pipelines. Each pipeline has its own page with file input, client configuration, progress tracking, and results display.

---

## Architecture

```
packages/platform_app/src/platform_app/
  app.py                     # Entrypoint: st.navigation + pg.run()
  orchestrator.py             # Pipeline dispatcher
  cli.py                      # Typer CLI (non-Streamlit)
  components/
    __init__.py
    file_input.py             # Dual file upload + path input
    client_selector.py        # Client ID/name with registry auto-lookup
    progress.py               # st.status + st.progress wrapper
    download.py               # Download button row (MIME-mapped)
    results_display.py        # Unified tabs: tables, charts, downloads
  pages/
    home.py                   # Landing page
    ars_analysis.py           # ARS pipeline page
    txn_base.py               # Transaction Base (M1-M10) page
    txn_v4.py                 # Transaction V4 (S0-S9) page
    ics_analysis.py           # ICS pipeline page
  .streamlit/
    config.toml               # Theme, upload limits, server config
```

---

## Running

```bash
streamlit run packages/platform_app/src/platform_app/app.py
```

---

## Navigation

Uses `st.navigation` (Streamlit >= 1.36) instead of `pages/` auto-discovery.

Pages are organized into sections:
- **Home** -- landing page with quick-start guide
- **Pipelines** -- ARS, Transaction (Base), Transaction (V4), ICS

The entrypoint (`app.py`) defines all pages and calls `pg.run()`. Shared sidebar elements (version caption) render on every page.

---

## Shared Components

### `file_input.py` -- Dual Mode Input

Two input modes via radio toggle:
1. **Upload file** -- `st.file_uploader` writes to temp file, returns `Path`
2. **Server path** -- `st.text_input` validates existence, returns `Path`

Both modes return `Path | None`. Pipelines always receive a `Path` object.

### `client_selector.py` -- Registry Auto-Lookup

- Loads master client registry via `@st.cache_resource(ttl=3600)`
- Two-column layout: Client ID + Client Name
- If client ID matches a registry entry, auto-fills client name
- Graceful degradation if registry unavailable (manual input only)

### `progress.py` -- Pipeline Progress

`run_with_progress(name, run_fn, **kwargs)` wraps any pipeline call with:
- `st.progress` bar (0-100%)
- `st.status` expandable log
- `st.toast` notification on completion
- Injects `progress_callback` into kwargs

### `download.py` -- MIME-Mapped Downloads

Scans output directory for `.xlsx`, `.pptx`, `.png`, `.csv`, `.html` files and renders `st.download_button` for each.

### `results_display.py` -- Unified Results

Tabbed layout:
1. **Data Tables** -- expandable DataFrames per analysis
2. **Charts (N)** -- PNG images from output directory (if any)
3. **Downloads** -- all output files

KPI metrics row at top: Analyses count, Total Rows, Charts count.

---

## Page Pattern

Each pipeline page (except V4) follows the same pattern:

```python
# Sidebar: inputs
with st.sidebar:
    data_file = render_file_input(...)
    client_id, client_name = render_client_selector(...)
    run_btn = st.button("Run ...", type="primary")

# Main: guard + run + display
if not run_btn and "results" not in st.session_state:
    st.info("...")
    st.stop()

if run_btn:
    # validate -> run_with_progress -> store in session_state

if "results" in st.session_state:
    render_results(...)
```

Results persist in `st.session_state` so they survive widget interactions without re-running the pipeline.

### V4 Exception

Transaction V4 bypasses the orchestrator and calls `txn_analysis.v4_run.run_pipeline` directly. It has custom storyline selection checkboxes and its own progress callback signature.

---

## Config

`.streamlit/config.toml`:
- `maxUploadSize = 100` MB
- Theme: `#2E4057` primary, `#F5F7FA` secondary background
- `gatherUsageStats = false`

---

## Data Flow

```
User Input (file + client)
  -> render_file_input() returns Path
  -> render_client_selector() returns (id, name)
  -> run_with_progress() calls orchestrator.run_pipeline()
    -> orchestrator creates PipelineContext
    -> dispatches to runner (ics/ars/txn)
    -> runner bridges to pipeline-native API
    -> returns dict[str, SharedResult]
  -> results stored in st.session_state
  -> render_results() displays tables/charts/downloads
```

---

## Testing

- 15 component tests in `tests/platform/test_components.py`
- 12 orchestrator tests in `tests/platform/test_orchestrator.py`
- Components tested: MIME map, chart image discovery, registry loading, AnalysisResult
- Full suite: 1195 tests passing
