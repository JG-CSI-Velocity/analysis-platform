"""TXN Pipeline -- dedicated page for transaction intelligence."""

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

logger = logging.getLogger("platform_app.pipeline_txn")

PREFIX = "txn_pipe"

st.markdown(
    '<h2 style="margin-bottom:0.2rem;">Transaction Analysis</h2>'
    '<p style="color:#64748B;margin-bottom:1.5rem;">'
    "Transaction intelligence -- merchants, MCC, competitors, trends, "
    "interchange, demographics, lifecycle</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# File Inputs
# ---------------------------------------------------------------------------
st.markdown("**Data Files**")
txn_path = render_file_input(
    "Transaction CSV (.csv)",
    f"{PREFIX}_txn",
    filetypes=".csv",
    help_text="Combined transaction CSV or single-month file",
)

odd_path = render_file_input(
    "ODD File (.xlsx) -- optional",
    f"{PREFIX}_odd",
    filetypes=".xlsx",
    help_text="Required for Demographics (M11), Campaigns (M12), Lifecycle (M14)",
)

if not odd_path:
    st.caption(
        "Without ODD: Demographics, Campaigns, and Lifecycle modules will be skipped."
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
if txn_path and Path(txn_path).exists():
    out_default = str(Path(txn_path).parent / "output_txn")
out_dir = st.text_input(
    "Output Directory",
    value=st.session_state.get(f"{PREFIX}_out_dir", out_default),
    key=f"_input_{PREFIX}_out_dir",
    placeholder="Where to write results...",
)
st.session_state[f"{PREFIX}_out_dir"] = out_dir

st.divider()

# ---------------------------------------------------------------------------
# Module Selection
# ---------------------------------------------------------------------------
st.markdown("**Select Modules**")
render_preset_picker(Product.TXN, f"{PREFIX}_modules")
selected = render_module_picker(Product.TXN, f"{PREFIX}_modules")

# Dependency enforcement: if any M6B-G selected, auto-include M6A
_COMPETITOR_DEPS = {
    "txn_competitor_high_level",
    "txn_top_20_competitors",
    "txn_competitor_categories",
    "txn_competitor_biz_personal",
    "txn_competitor_monthly_trends",
    "txn_competitor_threat_assessment",
    "txn_competitor_segmentation",
}
_FINANCIAL_DEPS = {"txn_financial_services_summary"}
_SCORECARD_DEPS = {"txn_portfolio_scorecard"}

auto_added: list[str] = []
if selected & _COMPETITOR_DEPS and "txn_competitor_detection" not in selected:
    selected.add("txn_competitor_detection")
    auto_added.append("Competitor Detection (required by selected competitor modules)")
if selected & _FINANCIAL_DEPS and "txn_financial_services_detection" not in selected:
    selected.add("txn_financial_services_detection")
    auto_added.append("Financial Services Detection (required by Financial Summary)")
if selected & _SCORECARD_DEPS:
    for dep in ("txn_interchange_summary", "txn_member_segments"):
        if dep not in selected:
            selected.add(dep)
            auto_added.append(f"{dep.replace('txn_', '').replace('_', ' ').title()} (required by Scorecard)")

if auto_added:
    st.info("Auto-added dependencies: " + "; ".join(auto_added))
    st.session_state[f"{PREFIX}_modules"] = selected

# ODD-dependent module warnings
_ODD_MODULES = {"txn_demographics", "txn_campaigns", "txn_lifecycle"}
if selected & _ODD_MODULES and not odd_path:
    st.warning(
        "Selected modules require ODD file: "
        + ", ".join(m.replace("txn_", "").replace("_", " ").title() for m in sorted(selected & _ODD_MODULES))
    )

st.divider()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors: list[str] = []
if not txn_path or not Path(txn_path).exists():
    errors.append("Transaction CSV file is required.")
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
should_run = render_run_button("Run Transaction Analysis", PREFIX, len(selected))

# Show previous results
prev_results = st.session_state.get(f"{PREFIX}_last_results")
prev_errors = st.session_state.get(f"{PREFIX}_last_error")
prev_elapsed = st.session_state.get(f"{PREFIX}_last_elapsed", 0)
prev_out = st.session_state.get(f"{PREFIX}_last_out_dir", "")

if not should_run and (prev_results is not None or prev_errors):
    render_results(
        prev_results or {},
        Path(prev_out) if prev_out else Path("."),
        prev_elapsed,
        "txn",
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

bar, status_text = render_progress(PREFIX, "txn")

input_files: dict[str, Path] = {"tran": Path(txn_path)}
if odd_path and Path(odd_path).exists():
    input_files["odd"] = Path(odd_path)

client_config: dict = {"client_id": client_id}
if selected:
    client_config["module_ids"] = sorted(selected)

t0 = time.time()
pipeline_error: str | None = None
results: dict = {}

try:
    results = run_pipeline(
        "txn",
        input_files=input_files,
        output_dir=output_path,
        client_id=client_id,
        client_config=client_config,
        progress_callback=make_progress_callback(bar, status_text, "txn", PREFIX),
    )
    elapsed = round(time.time() - t0, 1)
    bar.progress(1.0, text=f"TXN complete -- {len(results)} results in {elapsed}s")
    status_text.empty()
    logger.info("TXN complete: %d results in %.1fs", len(results), elapsed)
except Exception:
    import traceback

    elapsed = round(time.time() - t0, 1)
    pipeline_error = traceback.format_exc()
    bar.progress(1.0, text=f"TXN FAILED ({elapsed}s)")
    logger.error("TXN failed:\n%s", pipeline_error)

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
        pipeline="txn",
        modules_run=sorted(selected),
        runtime_seconds=elapsed,
        status="success" if not pipeline_error else "error",
        output_dir=str(output_path),
        input_file_hash=hash_file(Path(txn_path)),
        result_count=len(results),
    )
    log_run(record)
except Exception:
    pass

# Render results
render_results(results, output_path, elapsed, "txn", errors=pipeline_error)
