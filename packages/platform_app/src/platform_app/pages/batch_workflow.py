"""UAP Batch Run -- run multiple pipelines sequentially for multiple clients."""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import streamlit as st

from platform_app.components.results_display import render_results
from platform_app.core.run_logger import RunRecord, generate_run_id, log_run

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">ANALYSIS / BATCH RUN</p>', unsafe_allow_html=True)
st.title("Batch Run")
st.caption("Queue multiple pipelines and execute sequentially.")

# ---------------------------------------------------------------------------
# Config -- main area, not sidebar
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">CLIENT</p>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    client_id = st.text_input(
        "Client ID", value=st.session_state.get("uap_client_id", ""), key="batch_cid"
    )
with c2:
    client_name = st.text_input(
        "Client Name", value=st.session_state.get("uap_client_name", ""), key="batch_cname"
    )

st.divider()

# Pipeline selection
st.markdown('<p class="uap-label">PIPELINES</p>', unsafe_allow_html=True)
p1, p2, p3 = st.columns(3)
with p1:
    run_ars = st.checkbox("ARS Analysis", key="batch_ars")
with p2:
    run_txn = st.checkbox("Transaction Base", key="batch_txn")
with p3:
    run_ics = st.checkbox("ICS Analysis", key="batch_ics")

selected: list[str] = []
if run_ars:
    selected.append("ars")
if run_txn:
    selected.append("txn")
if run_ics:
    selected.append("ics")

st.divider()

# File paths -- only show fields for selected pipelines
st.markdown('<p class="uap-label">DATA FILES</p>', unsafe_allow_html=True)

oddd_path = ""
tran_path = ""
ics_path = ""

if not selected:
    st.info("Select at least one pipeline above to configure data files.")
else:
    if run_ars:
        oddd_path = st.text_input(
            "ODDD file",
            value=st.session_state.get("uap_file_oddd", ""),
            key="batch_oddd",
            placeholder="/path/to/9999-ODD.xlsx",
        )
    if run_txn:
        tran_path = st.text_input(
            "Transaction file",
            value=st.session_state.get("uap_file_tran", ""),
            key="batch_tran",
            placeholder="/path/to/transactions.csv (use Data Ingestion to merge multi-file)",
        )
    if run_ics:
        ics_path = st.text_input(
            "ICS data file",
            value=st.session_state.get("uap_file_ics", ""),
            key="batch_ics_file",
            placeholder="/path/to/ics_data.xlsx",
        )

st.divider()

output_base = st.text_input(
    "Output directory",
    key="batch_output",
    placeholder="Leave empty to auto-generate from input file location",
)

st.divider()

# ---------------------------------------------------------------------------
# Queue display
# ---------------------------------------------------------------------------
if not selected and "batch_results" not in st.session_state:
    st.info("Select pipelines above to build your execution queue.")
    st.stop()

pipeline_info = {
    "ars": ("ARS Analysis", "#3B82F6"),
    "txn": ("Transaction Base", "#10B981"),
    "ics": ("ICS Analysis", "#F59E0B"),
}

run_btn = st.button(
    f"Execute {len(selected)} Pipeline(s)" if selected else "Select pipelines",
    type="primary",
    disabled=not selected,
    key="batch_run",
    use_container_width=True,
)

if selected and not run_btn and "batch_results" not in st.session_state:
    st.markdown('<p class="uap-label">EXECUTION QUEUE</p>', unsafe_allow_html=True)

    for i, key in enumerate(selected, 1):
        label, color = pipeline_info.get(key, (key, "#94A3B8"))
        st.markdown(
            f'<div style="display: flex; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #F1F5F9;">'
            f'<span style="font-family: var(--uap-mono); font-size: 1.1rem; font-weight: 700; color: {color}; min-width: 2rem;">{i:02d}</span>'
            f'<span style="font-family: var(--uap-sans); font-weight: 500; font-size: 0.95rem; color: #0F172A;">{label}</span>'
            f'<span class="uap-badge uap-badge-muted" style="margin-left: auto;">QUEUED</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.stop()

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------
if run_btn:
    # Validation
    if not client_id.strip():
        st.error("Client ID is required.")
        st.stop()

    from platform_app.orchestrator import run_pipeline

    run_id = generate_run_id()
    all_results: dict[str, dict] = {}
    all_output_dirs: dict[str, Path] = {}
    all_timings: dict[str, float] = {}
    errors: dict[str, str] = {}

    overall_progress = st.progress(0, text="Starting batch...")

    for i, key in enumerate(selected):
        overall_progress.progress(
            i / len(selected),
            text=f"[{i + 1}/{len(selected)}] Running {key.upper()}...",
        )

        # Resolve files
        input_files: dict[str, Path] = {}
        if key == "ars":
            p = oddd_path.strip() if run_ars else ""
            if not p or not Path(p).exists():
                errors[key] = f"ODDD file not found: {p}"
                continue
            input_files["oddd"] = Path(p)
            out = (
                Path(p).parent / "output"
                if not output_base.strip()
                else Path(output_base.strip()) / "ars"
            )
        elif key == "txn":
            p = tran_path.strip() if run_txn else ""
            if not p or not Path(p).exists():
                errors[key] = f"Transaction file not found: {p}"
                continue
            input_files["tran"] = Path(p)
            out = (
                Path(p).parent / "output_txn"
                if not output_base.strip()
                else Path(output_base.strip()) / "txn"
            )
        elif key == "ics":
            p = ics_path.strip() if run_ics else ""
            if not p or not Path(p).exists():
                errors[key] = f"ICS file not found: {p}"
                continue
            input_files["ics"] = Path(p)
            out = (
                Path(p).parent / "output_ics"
                if not output_base.strip()
                else Path(output_base.strip()) / "ics"
            )
        else:
            continue

        out.mkdir(parents=True, exist_ok=True)

        t0 = time.time()
        try:
            with st.status(f"Running {key.upper()}...", expanded=True) as status:
                messages: list[str] = []

                def _cb(msg: str, msgs: list[str] = messages, s=status) -> None:
                    msgs.append(msg)
                    s.write(msg)

                results = run_pipeline(
                    key,
                    input_files=input_files,
                    output_dir=out,
                    client_id=client_id.strip(),
                    client_name=client_name.strip(),
                    progress_callback=_cb,
                )
                elapsed = time.time() - t0
                status.update(
                    label=f"{key.upper()} -- {elapsed:.1f}s", state="complete", expanded=False
                )

            all_results[key] = results
            all_output_dirs[key] = out
            all_timings[key] = elapsed
        except Exception:
            all_timings[key] = time.time() - t0
            errors[key] = traceback.format_exc()

    overall_progress.progress(1.0, text="Batch complete!")

    total_time = sum(all_timings.values())
    if errors:
        st.warning(
            f"Batch done: {len(all_results)} succeeded, {len(errors)} failed in {total_time:.1f}s"
        )
    else:
        st.success(f"All {len(all_results)} pipelines completed in {total_time:.1f}s")
        st.toast("Batch complete!", icon=":material/check_circle:")

    # Log
    record = RunRecord(
        run_id=run_id,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        csm=st.session_state.get("uap_csm", ""),
        client_id=client_id.strip(),
        client_name=client_name.strip(),
        pipeline=",".join(selected),
        modules_run=selected,
        runtime_seconds=round(total_time, 1),
        status="success" if not errors else "partial",
        output_dir=output_base.strip() or str(out),
        result_count=sum(len(r) for r in all_results.values()),
    )
    try:
        log_run(record)
    except Exception:
        pass

    # Store
    st.session_state["batch_results"] = all_results
    st.session_state["batch_output_dirs"] = all_output_dirs
    st.session_state["batch_errors"] = errors
    st.session_state["batch_timings"] = all_timings

    # Also store as last results for outputs page
    st.session_state["uap_last_results"] = all_results
    st.session_state["uap_last_output_dirs"] = all_output_dirs
    st.session_state["uap_last_errors"] = errors
    st.session_state["uap_last_run_id"] = run_id

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
if "batch_results" in st.session_state:
    results = st.session_state["batch_results"]
    output_dirs = st.session_state.get("batch_output_dirs", {})
    errors = st.session_state.get("batch_errors", {})
    timings = st.session_state.get("batch_timings", {})

    st.divider()
    st.markdown('<p class="uap-label">RESULTS</p>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Succeeded", len(results))
    m2.metric("Failed", len(errors))
    m3.metric("Total Time", f"{sum(timings.values()):.1f}s")

    # Errors
    for key, tb in errors.items():
        with st.expander(f"Error: {key.upper()}", expanded=False):
            st.code(tb)

    # Tabbed results
    if results:
        tabs = st.tabs([k.upper() for k in results])
        for tab, key in zip(tabs, results):
            with tab:
                render_results(
                    results[key],
                    output_dir=output_dirs.get(key),
                    client_id=st.session_state.get("uap_client_id", ""),
                )

    st.divider()
    if st.button("Clear Results", key="batch_clear"):
        for k in ["batch_results", "batch_output_dirs", "batch_errors", "batch_timings"]:
            st.session_state.pop(k, None)
        st.rerun()
