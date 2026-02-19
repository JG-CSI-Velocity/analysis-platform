"""Run Analysis page -- unified wizard for ARS, Transaction, and ICS pipelines."""

from __future__ import annotations

import logging
import tempfile
import time
import traceback
from datetime import datetime
from pathlib import Path

import streamlit as st

from platform_app.components import PIPELINE_FILE_ROLES, kpi_row
from platform_app.theme import step_indicator_html, success_banner

logger = logging.getLogger(__name__)

WIZARD_STEPS = ["Select Pipeline", "Upload Data", "Confirm & Run", "Results"]
_TMP_DIR = Path(tempfile.gettempdir()) / "platform_uploads"

PIPELINE_LABELS = {
    "ars": "ARS Analysis",
    "txn": "Transaction (Base)",
    "txn_v4": "Transaction (V4)",
    "ics": "ICS Analysis",
}


def render() -> None:
    try:
        _render_inner()
    except Exception:
        st.error("Something went wrong. Please try refreshing the page.")
        logger.exception("Unhandled error in run_analysis")


def _render_inner() -> None:
    _init_wizard()

    st.title("Run Analysis")

    # Wizard flow
    st.markdown(step_indicator_html(st.session_state.wiz_step, WIZARD_STEPS), unsafe_allow_html=True)
    st.markdown("")

    step = st.session_state.wiz_step
    if step == 0:
        _step_select_pipeline()
    elif step == 1:
        _step_upload_data()
    elif step == 2:
        _step_confirm_and_run()
    elif step == 3:
        _step_results()


def _init_wizard():
    defaults = {
        "wiz_step": 0,
        "wiz_pipeline": "ars",
        "wiz_client_id": "",
        "wiz_client_name": "",
        "wiz_files": {},
        "wiz_results": None,
        "wiz_output_dir": None,
        "wiz_elapsed": 0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_wizard():
    st.session_state.wiz_step = 0
    st.session_state.wiz_files = {}
    st.session_state.wiz_results = None
    st.session_state.wiz_output_dir = None
    st.session_state.wiz_elapsed = 0


def _go_next():
    if st.session_state.wiz_step < len(WIZARD_STEPS) - 1:
        st.session_state.wiz_step += 1


def _go_back():
    if st.session_state.wiz_step > 0:
        st.session_state.wiz_step -= 1


# -- Step 0: Select Pipeline & Client --

def _step_select_pipeline():
    st.markdown("### Select a pipeline and enter client info")

    pipeline = st.radio(
        "Pipeline",
        list(PIPELINE_LABELS.keys()),
        format_func=PIPELINE_LABELS.get,
        horizontal=True,
        index=list(PIPELINE_LABELS.keys()).index(st.session_state.wiz_pipeline),
    )
    st.session_state.wiz_pipeline = pipeline

    # Pipeline description
    descriptions = {
        "ars": "OD/NSF portfolio analysis -- 20 analytics modules across 7 sections with Excel + PowerPoint output.",
        "txn": "Debit card transaction analysis -- base modules M1-M10.",
        "txn_v4": "V4 storyline analytics -- S0-S9 with charts, Excel, and optional PowerPoint.",
        "ics": "Instant Card Services portfolio analysis with append and analytics.",
    }
    st.caption(descriptions.get(pipeline, ""))

    col1, col2 = st.columns(2)
    with col1:
        client_id = st.text_input("Client ID", value=st.session_state.wiz_client_id, placeholder="e.g. 9999")
    with col2:
        client_name = st.text_input("Client Name", value=st.session_state.wiz_client_name, placeholder="e.g. Test CU")

    st.session_state.wiz_client_id = client_id
    st.session_state.wiz_client_name = client_name

    if client_id.strip():
        st.button("Next", type="primary", on_click=_go_next, use_container_width=True)
    else:
        st.info("Enter a Client ID to continue.")


# -- Step 1: Upload Data Files --

def _step_upload_data():
    pipeline = st.session_state.wiz_pipeline
    file_roles = PIPELINE_FILE_ROLES.get(pipeline, [])

    st.markdown(f"### Upload data for {PIPELINE_LABELS.get(pipeline, pipeline)}")

    files = st.session_state.wiz_files

    for role_info in file_roles:
        role = role_info["role"]
        label = role_info["label"]
        types = role_info["types"]

        # Check for existing file
        existing = files.get(role)
        if existing and Path(existing).exists():
            st.success(f"{label}: {Path(existing).name}")

        uploaded = st.file_uploader(
            label,
            type=types,
            key=f"upload_{role}",
            help=f"Upload the {label.lower()} for this analysis.",
        )

        if uploaded:
            _TMP_DIR.mkdir(parents=True, exist_ok=True)
            file_path = _TMP_DIR / uploaded.name
            file_path.write_bytes(uploaded.getvalue())
            files[role] = str(file_path)
            st.success(f"Loaded: {uploaded.name}")

    st.session_state.wiz_files = files

    # Navigation
    col_back, col_next = st.columns([1, 3])
    with col_back:
        st.button("Back", on_click=_go_back, use_container_width=True)
    with col_next:
        required_roles = {r["role"] for r in file_roles}
        have_roles = {k for k, v in files.items() if v and Path(v).exists()}
        if required_roles <= have_roles:
            st.button("Next", type="primary", on_click=_go_next, use_container_width=True)
        else:
            missing = required_roles - have_roles
            st.info(f"Upload required files: {', '.join(missing)}")


# -- Step 2: Confirm & Run --

def _step_confirm_and_run():
    pipeline = st.session_state.wiz_pipeline
    client_id = st.session_state.wiz_client_id
    client_name = st.session_state.wiz_client_name
    files = st.session_state.wiz_files

    st.markdown("### Review and run")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Pipeline:** {PIPELINE_LABELS.get(pipeline, pipeline)}")
            st.markdown(f"**Client:** {client_id} -- {client_name}")
        with col2:
            for role, path in files.items():
                if path:
                    st.markdown(f"**{role}:** {Path(path).name}")

    col_back, col_run = st.columns([1, 3])
    with col_back:
        st.button("Back", on_click=_go_back, use_container_width=True)
    with col_run:
        if st.button("Run Analysis", type="primary", use_container_width=True):
            _execute_pipeline()


def _execute_pipeline():
    pipeline = st.session_state.wiz_pipeline
    client_id = st.session_state.wiz_client_id
    client_name = st.session_state.wiz_client_name
    files = st.session_state.wiz_files

    input_files = {role: Path(path) for role, path in files.items() if path}
    output_dir = _TMP_DIR / "output" / f"{client_id}_{pipeline}"
    output_dir.mkdir(parents=True, exist_ok=True)

    progress_bar = st.progress(0, text="Initializing...")
    status_box = st.status(f"Running {PIPELINE_LABELS.get(pipeline, pipeline)}...", expanded=True)

    messages: list[str] = []

    def _on_progress(msg: str) -> None:
        messages.append(msg)
        progress_bar.progress(min(len(messages) / 20, 0.95), text=msg)
        status_box.write(msg)

    t0 = time.time()
    try:
        from platform_app.orchestrator import run_pipeline

        with status_box:
            results = run_pipeline(
                pipeline,
                input_files=input_files,
                output_dir=output_dir,
                client_id=client_id.strip(),
                client_name=client_name.strip(),
                progress_callback=_on_progress,
            )

        elapsed = time.time() - t0
        status_box.update(label=f"Complete in {elapsed:.1f}s", state="complete")
        progress_bar.progress(1.0, text="Complete!")

        st.session_state.wiz_results = results
        st.session_state.wiz_output_dir = str(output_dir)
        st.session_state.wiz_elapsed = elapsed

        # Record in history
        st.session_state.setdefault("run_history", []).append({
            "pipeline": pipeline,
            "client_id": client_id,
            "client_name": client_name,
            "success": True,
            "elapsed": elapsed,
            "output_dir": str(output_dir),
            "timestamp": datetime.now().isoformat(),
            "result_count": len(results),
        })

        st.session_state.wiz_step = 3
        st.rerun()

    except Exception:
        elapsed = time.time() - t0
        status_box.update(label="Analysis failed", state="error")
        st.error("Pipeline error -- see traceback below.")
        st.code(traceback.format_exc())

        st.session_state.setdefault("run_history", []).append({
            "pipeline": pipeline,
            "client_id": client_id,
            "client_name": client_name,
            "success": False,
            "elapsed": elapsed,
            "timestamp": datetime.now().isoformat(),
        })


# -- Step 3: Results --

def _step_results():
    pipeline = st.session_state.wiz_pipeline
    results = st.session_state.wiz_results
    output_dir = st.session_state.wiz_output_dir
    elapsed = st.session_state.wiz_elapsed

    if not results:
        st.warning("No results available.")
        st.button("Start Over", on_click=_reset_wizard, type="primary")
        return

    success_banner(
        f"{PIPELINE_LABELS.get(pipeline, pipeline)} Complete",
        f"{len(results)} analyses in {elapsed:.1f}s",
    )

    # KPI row
    kpi_row([
        {"label": "Analyses", "value": str(len(results))},
        {"label": "Pipeline", "value": pipeline.upper()},
        {"label": "Time", "value": f"{elapsed:.1f}s"},
    ])

    # Download section
    if output_dir and Path(output_dir).exists():
        st.markdown("### Downloads")
        downloadable = sorted(
            f for f in Path(output_dir).rglob("*")
            if f.is_file() and f.suffix in (".xlsx", ".pptx", ".png", ".csv")
        )
        if downloadable:
            cols = st.columns(min(len(downloadable), 4))
            for i, f in enumerate(downloadable[:8]):
                mime = {
                    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    ".png": "image/png",
                    ".csv": "text/csv",
                }.get(f.suffix, "application/octet-stream")
                with cols[i % len(cols)]:
                    st.download_button(f.name, f.read_bytes(), file_name=f.name, mime=mime, use_container_width=True)

    # Results detail
    if results:
        st.markdown("### Analysis Results")
        for name, ar in results.items():
            with st.expander(f"{name}: {ar.summary or ar.name}", expanded=False):
                if ar.data:
                    for sheet_name, df in ar.data.items():
                        st.dataframe(df, use_container_width=True, hide_index=True)
                if ar.charts:
                    for chart_path in ar.charts:
                        if Path(chart_path).exists():
                            st.image(str(chart_path), use_container_width=True)

    st.markdown("---")
    st.button("Run Another Analysis", on_click=_reset_wizard, type="primary", use_container_width=True)
