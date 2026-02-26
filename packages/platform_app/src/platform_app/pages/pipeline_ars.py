"""ARS Pipeline -- dedicated page for OD/NSF account analysis."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import streamlit as st

from platform_app.core.module_registry import Product
from platform_app.core.run_logger import RunRecord, generate_run_id, hash_file, log_run
from platform_app.orchestrator import run_pipeline
from platform_app.pages._pipeline_shared import (
    make_progress_callback,
    render_file_input,
    render_module_picker,
    render_preset_picker,
    render_progress,
    render_results,
    render_run_button,
)

logger = logging.getLogger("platform_app.pipeline_ars")

PREFIX = "ars_pipe"

st.markdown(
    '<h2 style="margin-bottom:0.2rem;">ARS Analysis</h2>'
    '<p style="color:#64748B;margin-bottom:1.5rem;">'
    "OD/NSF account analysis -- attrition, DCTR, mailers, Reg E, value segmentation</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# File Input
# ---------------------------------------------------------------------------
st.markdown("**Data File**")
odd_path = render_file_input(
    "ODD File (.xlsx)",
    f"{PREFIX}_odd",
    filetypes=".xlsx",
    help_text="Formatted ODD Excel file with account data",
)

# Client ID
client_id = st.text_input(
    "Client ID",
    value=st.session_state.get(f"{PREFIX}_client_id", ""),
    key=f"_input_{PREFIX}_client_id",
    placeholder="e.g. 1234",
)
st.session_state[f"{PREFIX}_client_id"] = client_id

# Output directory
out_default = ""
if odd_path and Path(odd_path).exists():
    out_default = str(Path(odd_path).parent / "output")
out_dir = st.text_input(
    "Output Directory",
    value=st.session_state.get(f"{PREFIX}_out_dir", out_default),
    key=f"_input_{PREFIX}_out_dir",
    placeholder="Where to write results...",
)
st.session_state[f"{PREFIX}_out_dir"] = out_dir

st.divider()

# ---------------------------------------------------------------------------
# Analysis Selection
# ---------------------------------------------------------------------------
st.markdown("**Select Analyses**")
render_preset_picker(Product.ARS, f"{PREFIX}_modules")
selected = render_module_picker(Product.ARS, f"{PREFIX}_modules")

st.divider()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors: list[str] = []
if not odd_path or not Path(odd_path).exists():
    errors.append("ODD file is required.")
if not client_id:
    errors.append("Client ID is required.")
if not out_dir:
    errors.append("Output directory is required.")

if errors:
    for e in errors:
        st.warning(e)

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
should_run = render_run_button("Run ARS Analysis", PREFIX, len(selected))

# Show previous results if not running
prev_results = st.session_state.get(f"{PREFIX}_last_results")
prev_errors = st.session_state.get(f"{PREFIX}_last_error")
prev_elapsed = st.session_state.get(f"{PREFIX}_last_elapsed", 0)
prev_out = st.session_state.get(f"{PREFIX}_last_out_dir", "")

if not should_run and (prev_results is not None or prev_errors):
    render_results(
        prev_results or {},
        Path(prev_out) if prev_out else Path("."),
        prev_elapsed,
        "ars",
        errors=prev_errors,
    )
    st.stop()

if not should_run:
    st.stop()

if errors:
    st.session_state[f"{PREFIX}_running"] = False
    st.stop()

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
run_id = generate_run_id()
output_path = Path(out_dir)
output_path.mkdir(parents=True, exist_ok=True)

bar, status_text = render_progress(PREFIX, "ars")

input_files: dict[str, Path] = {"oddd": Path(odd_path)}
client_config: dict = {"client_id": client_id}
if selected:
    client_config["module_ids"] = sorted(selected)

t0 = time.time()
pipeline_error: str | None = None
results: dict = {}

try:
    results = run_pipeline(
        "ars",
        input_files=input_files,
        output_dir=output_path,
        client_id=client_id,
        client_config=client_config,
        progress_callback=make_progress_callback(bar, status_text, "ars", PREFIX),
    )
    elapsed = round(time.time() - t0, 1)
    bar.progress(1.0, text=f"ARS complete -- {len(results)} results in {elapsed}s")
    status_text.empty()
    logger.info("ARS complete: %d results in %.1fs", len(results), elapsed)
except Exception:
    import traceback

    elapsed = round(time.time() - t0, 1)
    pipeline_error = traceback.format_exc()
    bar.progress(1.0, text=f"ARS FAILED ({elapsed}s)")
    logger.error("ARS failed:\n%s", pipeline_error)

# Store results
st.session_state[f"{PREFIX}_running"] = False
st.session_state[f"{PREFIX}_last_results"] = results
st.session_state[f"{PREFIX}_last_error"] = pipeline_error
st.session_state[f"{PREFIX}_last_elapsed"] = elapsed
st.session_state[f"{PREFIX}_last_out_dir"] = str(output_path)

# Log run
try:
    record = RunRecord(
        run_id=run_id,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        csm="",
        client_id=client_id,
        client_name="",
        pipeline="ars",
        modules_run=sorted(selected),
        runtime_seconds=elapsed,
        status="success" if not pipeline_error else "error",
        output_dir=str(output_path),
        input_file_hash=hash_file(Path(odd_path)),
        result_count=len(results),
    )
    log_run(record)
except Exception:
    pass

# Render results
render_results(results, output_path, elapsed, "ars", errors=pipeline_error)
