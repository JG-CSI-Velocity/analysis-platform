> **SUPERSEDED** by `chore-unified-consolidation.md` (2026-02-13). UI is built and wired; remaining work is real-data validation.

# Streamlit Analysis Platform -- Integration Plan

**Repo:** `/Users/jgmbp/Desktop/analysis_platform/` (JG-CSI-Velocity/analysis-platform)
**Package:** `packages/platform_app/`
**Branch:** create `feat/streamlit-ui` from `main`

---

## Current State

The Streamlit app has a **working scaffold** with 5 files:

| File | Status | What it does |
|------|--------|-------------|
| `app.py` | Minimal | Static landing page, lists 4 pipelines |
| `pages/1_ARS_Analysis.py` | Scaffolded | Sidebar form, path-based input, orchestrator call, results tabs, downloads |
| `pages/2_Transaction_Base.py` | Scaffolded | Dir/file input, CSV merge, orchestrator call, results tabs |
| `pages/3_Transaction_V4.py` | Scaffolded | Likely similar (not yet read) |
| `pages/4_ICS_Analysis.py` | Scaffolded | Sidebar form, path-based input, orchestrator call, results tabs |

**What works:**
- Orchestrator dispatches to correct runner (ARS/TXN/ICS)
- Runners bridge PipelineContext -> pipeline-native Settings -> run_pipeline -> SharedResult
- Pages have progress bar + st.status + results display + download buttons
- Session state persists paths between runs

**What's missing or broken:**
1. **File upload** -- all pages use `st.text_input` for file paths (breaks when server != local machine)
2. **No interactive charts** -- results only show DataFrames, no Plotly figures
3. **No caching** -- full pipeline re-runs on every widget interaction
4. **No shared components** -- CSS, progress pattern, download pattern duplicated 4x
5. **No client registry** -- client_id/name manually entered, no auto-lookup
6. **Old page pattern** -- uses `pages/` auto-discovery instead of `st.navigation`
7. **No config.toml** -- no theme, no upload size limits
8. **No tests** -- `tests/platform_app/` directory doesn't exist
9. **Landing page is static** -- no quick-start, no recent runs, no guidance
10. **No chart catalog** -- ICS chart catalog not exposed in UI

---

## Solution Overview

Refactor the Streamlit app into a production-ready internal tool:

1. **Migrate to `st.navigation`** with sectioned sidebar
2. **Add `st.file_uploader`** alongside path input (dual mode)
3. **Display interactive Plotly charts** from pipeline results
4. **Extract shared components** (file upload, progress, download, client selector)
5. **Add `@st.cache_data`** for expensive operations
6. **Wire client registry** for auto-populated client config
7. **Add `.streamlit/config.toml`** with theme + upload limits
8. **Add tests** for orchestrator + shared components

---

## Architecture

```
packages/platform_app/src/platform_app/
  app.py                     # Entrypoint: st.navigation + pg.run()
  components/
    __init__.py
    file_input.py            # Dual file upload + path input component
    progress.py              # st.status + st.progress wrapper
    download.py              # Download button row (Excel, PPTX, charts ZIP)
    client_selector.py       # Client ID input + registry auto-lookup
    results_display.py       # Tabs: tables, charts, downloads
  pages/
    home.py                  # Landing page (replaces static app.py content)
    ics_analysis.py          # ICS pipeline page
    ars_analysis.py          # ARS pipeline page
    txn_base.py              # Transaction Base page
    txn_v4.py                # Transaction V4 page
  .streamlit/
    config.toml              # Theme, upload limits, server config
```

### Navigation Structure

```python
# app.py
import streamlit as st

home = st.Page("pages/home.py", title="Home", icon=":material/home:", default=True)
ars = st.Page("pages/ars_analysis.py", title="ARS Analysis", icon=":material/analytics:")
txn_base = st.Page("pages/txn_base.py", title="Transaction (Base)", icon=":material/credit_card:")
txn_v4 = st.Page("pages/txn_v4.py", title="Transaction (V4)", icon=":material/trending_up:")
ics = st.Page("pages/ics_analysis.py", title="ICS Analysis", icon=":material/card_membership:")

pg = st.navigation({
    "": [home],
    "Pipelines": [ars, txn_base, txn_v4, ics],
})

# Shared sidebar elements
st.logo("logo.png")  # or text-based
st.sidebar.caption("v1.0.0")

pg.run()
```

---

## Shared Components

### `file_input.py` -- Dual Mode File Input

```python
def render_file_input(
    page_key: str,
    accepted_types: list[str],
    label: str = "Upload client data",
) -> Path | None:
    """File uploader + fallback path input. Returns Path or None."""
    mode = st.radio("Input method", ["Upload file", "Server path"], key=f"{page_key}_mode")

    if mode == "Upload file":
        uploaded = st.file_uploader(label, type=accepted_types, key=f"{page_key}_upload")
        if uploaded is None:
            return None
        # Write to temp file so pipelines can use Path-based APIs
        tmp = tempfile.NamedTemporaryFile(suffix=f".{uploaded.name.split('.')[-1]}", delete=False)
        tmp.write(uploaded.getvalue())
        tmp.flush()
        return Path(tmp.name)
    else:
        path_str = st.text_input("File path", key=f"{page_key}_path")
        if not path_str.strip():
            return None
        p = Path(path_str.strip())
        if not p.exists():
            st.error(f"File not found: `{p}`")
            return None
        return p
```

**Why dual mode:** Enterprise users on shared network drives need path input. Remote/Docker users need file upload. Both are valid.

### `progress.py` -- Pipeline Progress Wrapper

```python
def run_with_progress(
    pipeline_name: str,
    run_fn: Callable[..., dict[str, SharedResult]],
    **kwargs,
) -> dict[str, SharedResult]:
    """Wrap any pipeline run with st.progress + st.status."""
    progress_bar = st.progress(0, text=f"Initializing {pipeline_name}...")
    messages: list[str] = []

    def on_progress(msg: str) -> None:
        messages.append(msg)
        progress_bar.progress(min(len(messages) / 20, 0.95), text=msg)

    kwargs["progress_callback"] = on_progress

    with st.status(f"Running {pipeline_name}...", expanded=True) as status:
        t0 = time.time()
        results = run_fn(**kwargs)
        elapsed = time.time() - t0
        status.update(label=f"Complete in {elapsed:.1f}s", state="complete", expanded=False)

    progress_bar.progress(1.0, text="Complete!")
    return results
```

### `download.py` -- Download Row

```python
def render_downloads(output_dir: Path, client_id: str):
    """Render download buttons for all generated output files."""
    MIME_MAP = {
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".png": "image/png",
        ".csv": "text/csv",
        ".html": "text/html",
    }
    files = sorted(
        f for f in output_dir.rglob("*")
        if f.is_file() and f.suffix in MIME_MAP
    )
    if not files:
        st.caption("No output files found.")
        return

    for f in files:
        st.download_button(
            f.name, f.read_bytes(), file_name=f.name,
            mime=MIME_MAP.get(f.suffix, "application/octet-stream"),
            on_click="ignore",
        )
```

### `client_selector.py` -- Registry Auto-Lookup

```python
@st.cache_resource(ttl=3600)
def _load_registry():
    """Load client registry once, shared across sessions."""
    try:
        from ics_toolkit.client_registry import load_master_config, resolve_master_config_path
        path = resolve_master_config_path()
        if path:
            return load_master_config(path)
    except ImportError:
        pass
    return {}

def render_client_selector(page_key: str) -> tuple[str, str]:
    """Client ID + name input with registry auto-fill."""
    registry = _load_registry()
    c1, c2 = st.columns(2)
    with c1:
        client_id = st.text_input("Client ID", key=f"{page_key}_client_id", placeholder="e.g. 1453")
    with c2:
        default_name = ""
        if client_id and client_id in registry:
            cfg = registry[client_id]
            if cfg.client_name:
                default_name = cfg.client_name
        client_name = st.text_input(
            "Client Name", key=f"{page_key}_client_name",
            value=default_name, placeholder="e.g. Connex CU",
        )
    return client_id.strip(), client_name.strip()
```

### `results_display.py` -- Unified Results Layout

```python
def render_results(
    results: dict[str, SharedResult],
    charts: dict[str, go.Figure] | None = None,
    output_dir: Path | None = None,
    client_id: str = "",
):
    """Unified results display: metrics, tabs (Tables, Charts, Downloads)."""
    st.subheader(f"Results: {len(results)} analyses")

    tab_names = ["Data Tables"]
    if charts:
        tab_names.append("Charts")
    if output_dir:
        tab_names.append("Downloads")

    tabs = st.tabs(tab_names)
    tab_idx = 0

    # Tables tab
    with tabs[tab_idx]:
        for name, ar in results.items():
            with st.expander(ar.summary or name, expanded=False):
                for sheet_name, df in ar.data.items():
                    st.dataframe(df, use_container_width=True, hide_index=True)
    tab_idx += 1

    # Charts tab
    if charts:
        with tabs[tab_idx]:
            for chart_name, fig in charts.items():
                st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_name}")
        tab_idx += 1

    # Downloads tab
    if output_dir:
        with tabs[tab_idx]:
            render_downloads(output_dir, client_id)
```

---

## Page Template (ICS Example)

Each pipeline page follows the same pattern:

```python
# pages/ics_analysis.py
import streamlit as st
from platform_app.components.file_input import render_file_input
from platform_app.components.client_selector import render_client_selector
from platform_app.components.progress import run_with_progress
from platform_app.components.results_display import render_results

st.header("ICS Analysis")
st.caption("Instant Card Services: portfolio health, activation, usage trends")

# Sidebar: inputs
with st.sidebar:
    st.subheader("Data Sources")
    data_file = render_file_input("ics", ["xlsx", "xls", "csv"], "Upload ICS data")

    st.subheader("Client")
    client_id, client_name = render_client_selector("ics")

    st.divider()
    run_btn = st.button("Run ICS Analysis", type="primary", key="ics_run")

# Main: guard + run + display
if not run_btn and "ics_results" not in st.session_state:
    st.info("Configure inputs in the sidebar and click **Run ICS Analysis**.")
    st.stop()

if run_btn:
    if not data_file:
        st.error("Data file is required.")
        st.stop()
    if not client_id:
        st.error("Client ID is required.")
        st.stop()

    from platform_app.orchestrator import run_pipeline
    output_dir = data_file.parent / "output_ics"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = run_with_progress(
        "ICS",
        run_pipeline,
        pipeline="ics",
        input_files={"ics": data_file},
        output_dir=output_dir,
        client_id=client_id,
        client_name=client_name,
    )
    st.session_state["ics_results"] = results
    st.session_state["ics_output_dir"] = output_dir
    st.session_state["ics_client_id"] = client_id

if "ics_results" in st.session_state:
    render_results(
        st.session_state["ics_results"],
        output_dir=st.session_state.get("ics_output_dir"),
        client_id=st.session_state.get("ics_client_id", ""),
    )
```

---

## Config: `.streamlit/config.toml`

```toml
[server]
maxUploadSize = 100
maxMessageSize = 200

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#2E4057"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F7FA"
textColor = "#1B1B1B"
font = "sans-serif"
```

---

## Implementation Phases

### Phase 1: Foundation (no behavior change)

1. Create `components/` package with `__init__.py`
2. Create `.streamlit/config.toml`
3. Migrate `app.py` to use `st.navigation` + `st.Page`
4. Rename pages to remove numeric prefixes (navigation handles order)
5. Extract shared CSS into `components/__init__.py` or remove (use config.toml theme)
6. Verify: `streamlit run app.py` shows same pages with new navigation

### Phase 2: Shared Components

1. Create `components/file_input.py` -- dual mode (upload + path)
2. Create `components/client_selector.py` -- with registry auto-lookup
3. Create `components/progress.py` -- st.status + st.progress wrapper
4. Create `components/download.py` -- download button row
5. Create `components/results_display.py` -- tables + charts + downloads tabs
6. Verify: components import and render correctly in isolation

### Phase 3: Refactor Pages

1. Rewrite `ics_analysis.py` using shared components
2. Rewrite `ars_analysis.py` using shared components
3. Rewrite `txn_base.py` using shared components
4. Rewrite `txn_v4.py` (likely mirror txn_base with `run_pipeline("txn_v4", ...)`)
5. Rewrite `home.py` -- quick-start guide, links to pipeline pages
6. Verify: all 4 pipeline pages functional end-to-end

### Phase 4: Interactive Charts

1. Modify ICS runner to pass Plotly figures through SharedResult
   - Option A: Store chart PNGs in `SharedResult.charts` (list of Paths), display via `st.image`
   - Option B: Modify runner to also return `go.Figure` objects in metadata
   - Option A is simpler and consistent with existing architecture
2. Add chart display in `results_display.py` -- iterate `output_dir/charts/*.html` and render
3. For ICS: pipeline already produces Plotly figures in `result.charts` dict -- bridge those through runner
4. Verify: charts render interactively in browser

### Phase 5: Caching + Polish

1. Add `@st.cache_data` on file parsing (hash by file bytes + name)
2. Add `@st.cache_resource` on client registry loading
3. Store results in `st.session_state` to persist across widget interactions
4. Add `st.toast` notifications on completion
5. Add KPI metrics row (`st.metric`) at top of results
6. Verify: re-clicking widgets doesn't re-run pipeline

### Phase 6: Tests

1. Create `tests/platform_app/` directory
2. Test `orchestrator.py` -- dispatch, unknown pipeline, missing files
3. Test `components/file_input.py` -- path validation
4. Test `components/client_selector.py` -- registry lookup
5. Test `components/download.py` -- MIME mapping
6. Target: 20+ tests, integrated into `make test`

---

## Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `components/__init__.py` | ~5 | Package marker |
| `components/file_input.py` | ~50 | Dual file upload + path input |
| `components/client_selector.py` | ~40 | Client ID/name with registry |
| `components/progress.py` | ~30 | Progress wrapper |
| `components/download.py` | ~30 | Download buttons |
| `components/results_display.py` | ~60 | Unified results layout |
| `pages/home.py` | ~40 | Landing page |
| `.streamlit/config.toml` | ~20 | Theme + server config |

## Files to Modify

| File | Change |
|------|--------|
| `app.py` | Replace static content with `st.navigation` entrypoint |
| `pages/ics_analysis.py` | Rewrite using shared components |
| `pages/ars_analysis.py` | Rewrite using shared components |
| `pages/txn_base.py` | Rewrite using shared components |
| `pages/txn_v4.py` | Rewrite using shared components |

## Files to Delete

| File | Reason |
|------|--------|
| `pages/1_ARS_Analysis.py` | Renamed to `pages/ars_analysis.py` (no numeric prefix) |
| `pages/2_Transaction_Base.py` | Renamed to `pages/txn_base.py` |
| `pages/3_Transaction_V4.py` | Renamed to `pages/txn_v4.py` |
| `pages/4_ICS_Analysis.py` | Renamed to `pages/ics_analysis.py` |

---

## Key Design Decisions

1. **Dual file input (upload + path)** -- Enterprise users on shared drives need path mode. Remote users need upload mode. Both are first-class.

2. **Results stored in `st.session_state`** -- Prevents re-running 30-60 second pipelines on every widget interaction. Pipeline runs only on explicit button click.

3. **Plotly charts via file-based approach initially** -- Pipelines already write chart HTML/PNGs to output dirs. Display those via `st.image` or `st.plotly_chart` (loading saved HTML). Avoid modifying runner return types until needed.

4. **`st.navigation` over `pages/` directory** -- Gives control over page order, sections, icons, and dynamic visibility. Modern Streamlit pattern (v1.36+).

5. **Temp file for uploads** -- Pipeline APIs expect `Path` objects. Writing uploaded bytes to a temp file is the simplest bridge. No need to refactor every pipeline to accept `BytesIO`.

6. **Client registry cached with `@st.cache_resource(ttl=3600)`** -- Loaded once per server, shared across sessions, refreshed hourly.

---

## Verification

1. `streamlit run packages/platform_app/src/platform_app/app.py` -- all pages render
2. Upload a real .xlsx file on ICS page -> pipeline runs -> results display -> download works
3. Use path input mode -> same result
4. Re-interact with widgets after run -> results persist (no re-run)
5. `make test` passes (existing + new tests)
6. `make lint` passes

---

## Dependencies

No new dependencies needed. Already in `pyproject.toml`:
- `streamlit>=1.36` (bump to `>=1.50` for modern features)
- `typer[all]>=0.12`
- All pipeline packages (shared, ars-analysis, txn-analysis, ics-toolkit)

Consider adding to dev dependencies:
- `orjson>=3.9` -- faster Plotly chart serialization in Streamlit

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Pipeline expects Path, upload gives BytesIO | Write to temp file, pass Path |
| Large file upload timeout | Set `maxUploadSize=100` in config.toml |
| Charts not rendering | Fall back to PNG display via `st.image` |
| Client registry file not found | Graceful degradation (manual input only) |
| Pages break on import | Lazy imports inside button-click handlers |
| Session state lost on page switch | All state in `st.session_state` persists across pages |
