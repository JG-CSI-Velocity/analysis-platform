"""Attrition Pipeline -- independent cross-program attrition analysis.

Supports segment filters to compare attrition across:
- All accounts (baseline)
- ARS Responders (accounts that responded to mailer campaigns)
- ICS Accounts (accounts opened via ICS referral/direct mail)

Key questions this answers:
- Do ARS responders have lower attrition than non-responders?
- Do ICS-sourced accounts have longer life / lower attrition?
- How many ICS accounts became ARS responders?
"""

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
    render_run_button,
)

logger = logging.getLogger("platform_app.pipeline_attrition")

PREFIX = "attr_pipe"

_SEGMENT_LABELS = {
    "all": "All Accounts",
    "ars_responders": "ARS Responders",
    "ics_accounts": "ICS Accounts",
    "ics_ars_crossover": "ICS + ARS Crossover",
}


def _render_segment_results(
    segments: dict,
    elapsed: float,
    errors: dict | None,
) -> None:
    """Render comparison results across segments."""
    if not segments:
        return

    st.divider()
    st.markdown(
        '<p style="font-size:0.82rem;font-weight:700;color:#475569;'
        'text-transform:uppercase;letter-spacing:0.03em;">SEGMENT COMPARISON</p>',
        unsafe_allow_html=True,
    )

    # Summary row
    n_segments = len(segments)
    n_ok = sum(1 for s in segments.values() if not s.get("error"))
    n_total_results = sum(len(s.get("results", {})) for s in segments.values())

    cols = st.columns(4)
    cols[0].metric("Segments", n_segments)
    cols[1].metric("Analyses", n_total_results)
    cols[2].metric("Runtime", f"{elapsed:.1f}s")
    cols[3].metric("Status", f"{n_ok}/{n_segments} OK")

    if n_ok == n_segments:
        st.success(f"All {n_segments} segments complete in {elapsed:.1f}s")
    else:
        st.warning(f"{n_ok}/{n_segments} segments complete, {n_segments - n_ok} failed")

    # Per-segment detail
    for seg_key, seg_data in segments.items():
        label = seg_data.get("label", seg_key)
        error = seg_data.get("error")
        results = seg_data.get("results", {})

        with st.expander(f"{label} -- {len(results)} analyses", expanded=not error):
            if error:
                st.error(f"{label} failed")
                st.code(error)
            else:
                st.caption(f"{len(results)} analyses completed")
                if results:
                    for name, result in sorted(results.items()):
                        status = "OK" if getattr(result, "success", True) else "FAIL"
                        color = "#16A34A" if status == "OK" else "#DC2626"
                        st.markdown(
                            f'<span style="color:{color};font-weight:600;">{status}</span> {name}',
                            unsafe_allow_html=True,
                        )


# ---------------------------------------------------------------------------
# Page Layout
# ---------------------------------------------------------------------------
st.markdown(
    '<h2 style="margin-bottom:0.2rem;">Attrition Analysis</h2>'
    '<p style="color:#64748B;margin-bottom:1.5rem;">'
    "Cross-program attrition comparison -- analyze closure rates, retention, "
    "and revenue impact across All accounts, ARS Responders, and ICS accounts</p>",
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
    help_text="Formatted ODD Excel file with account data, Date Closed, ICS and mailer columns",
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
    out_default = str(Path(odd_path).parent / "output_attrition")
out_dir = st.text_input(
    "Output Directory",
    value=st.session_state.get(f"{PREFIX}_out_dir", out_default),
    key=f"_input_{PREFIX}_out_dir",
    placeholder="Where to write results...",
)
st.session_state[f"{PREFIX}_out_dir"] = out_dir

st.divider()

# ---------------------------------------------------------------------------
# Segment Filters -- the core value of this page
# ---------------------------------------------------------------------------
st.markdown("**Account Segments**")
st.caption(
    "Run attrition analysis on different account populations to compare "
    "program effectiveness. Each selected segment produces its own result set."
)

seg_all = st.checkbox(
    "All Accounts (baseline)",
    value=st.session_state.get(f"{PREFIX}_seg_all", True),
    key=f"_cb_{PREFIX}_seg_all",
    help="Full account population -- the control group",
)
st.session_state[f"{PREFIX}_seg_all"] = seg_all

seg_ars = st.checkbox(
    "ARS Responders",
    value=st.session_state.get(f"{PREFIX}_seg_ars", False),
    key=f"_cb_{PREFIX}_seg_ars",
    help="Accounts that responded to any ARS mailer campaign. "
    'Answers: "Do ARS responders have lower attrition?"',
)
st.session_state[f"{PREFIX}_seg_ars"] = seg_ars

seg_ics = st.checkbox(
    "ICS Accounts",
    value=st.session_state.get(f"{PREFIX}_seg_ics", False),
    key=f"_cb_{PREFIX}_seg_ics",
    help="Accounts opened via ICS (referral or direct mail). "
    'Answers: "Do ICS accounts have longer life / lower attrition?"',
)
st.session_state[f"{PREFIX}_seg_ics"] = seg_ics

seg_crossover = st.checkbox(
    "ICS + ARS Crossover",
    value=st.session_state.get(f"{PREFIX}_seg_crossover", False),
    key=f"_cb_{PREFIX}_seg_crossover",
    help="ICS accounts that also became ARS responders. "
    'Answers: "How many ICS accounts became ARS responders?"',
)
st.session_state[f"{PREFIX}_seg_crossover"] = seg_crossover

segments_selected = []
if seg_all:
    segments_selected.append("all")
if seg_ars:
    segments_selected.append("ars_responders")
if seg_ics:
    segments_selected.append("ics_accounts")
if seg_crossover:
    segments_selected.append("ics_ars_crossover")

if not segments_selected:
    st.warning("Select at least one segment.")

st.divider()

# ---------------------------------------------------------------------------
# Module Selection
# ---------------------------------------------------------------------------
st.markdown("**Select Analyses**")
render_preset_picker(Product.ATTRITION, f"{PREFIX}_modules")
selected = render_module_picker(Product.ATTRITION, f"{PREFIX}_modules")

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
if not segments_selected:
    errors.append("Select at least one account segment.")

if errors:
    for e in errors:
        st.warning(e)

# Total runs = segments x modules
total_runs = len(segments_selected)
run_label = (
    f"Run Attrition ({len(selected)} modules x "
    f"{total_runs} segment{'s' if total_runs > 1 else ''})"
)

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
should_run = render_run_button(run_label, PREFIX, len(selected) * total_runs)

# Show previous results
prev_results = st.session_state.get(f"{PREFIX}_last_results")
prev_errors = st.session_state.get(f"{PREFIX}_last_error")
prev_elapsed = st.session_state.get(f"{PREFIX}_last_elapsed", 0)
prev_segments = st.session_state.get(f"{PREFIX}_last_segments", {})

if not should_run and (prev_results is not None or prev_errors):
    _render_segment_results(prev_segments, prev_elapsed, prev_errors)
    st.stop()

if not should_run:
    st.stop()

if errors:
    st.session_state[f"{PREFIX}_running"] = False
    st.stop()

# ---------------------------------------------------------------------------
# Execution -- run attrition for each segment
# ---------------------------------------------------------------------------
run_id = generate_run_id()
output_path = Path(out_dir)
output_path.mkdir(parents=True, exist_ok=True)

t0 = time.time()
segment_results: dict[str, dict] = {}
segment_errors: dict[str, str] = {}

for seg_idx, segment in enumerate(segments_selected):
    seg_label = _SEGMENT_LABELS.get(segment, segment)
    seg_out = output_path / segment

    st.markdown(
        f'<p style="font-size:0.82rem;font-weight:700;color:#475569;'
        f'text-transform:uppercase;">SEGMENT {seg_idx + 1}/{len(segments_selected)}: '
        f"{seg_label}</p>",
        unsafe_allow_html=True,
    )

    bar, status_text = render_progress(f"{PREFIX}_{segment}", f"attrition ({seg_label})")

    input_files: dict[str, Path] = {"oddd": Path(odd_path)}
    client_config: dict = {
        "client_id": client_id,
        "attrition_segment": segment,
    }
    if selected:
        client_config["module_ids"] = sorted(selected)

    try:
        seg_out.mkdir(parents=True, exist_ok=True)
        results = run_pipeline(
            "ars",
            input_files=input_files,
            output_dir=seg_out,
            client_id=client_id,
            client_config=client_config,
            progress_callback=make_progress_callback(
                bar, status_text, f"attrition ({seg_label})", PREFIX
            ),
        )
        bar.progress(1.0, text=f"{seg_label} complete -- {len(results)} results")
        status_text.empty()
        segment_results[segment] = results
        logger.info("Attrition %s complete: %d results", segment, len(results))
    except Exception:
        import traceback

        tb = traceback.format_exc()
        segment_errors[segment] = tb
        bar.progress(1.0, text=f"{seg_label} FAILED")
        logger.error("Attrition %s failed:\n%s", segment, tb)

elapsed = round(time.time() - t0, 1)

# Store results
st.session_state[f"{PREFIX}_running"] = False
st.session_state[f"{PREFIX}_last_results"] = segment_results
st.session_state[f"{PREFIX}_last_error"] = segment_errors if segment_errors else None
st.session_state[f"{PREFIX}_last_elapsed"] = elapsed
st.session_state[f"{PREFIX}_last_out_dir"] = str(output_path)
st.session_state[f"{PREFIX}_last_segments"] = {
    seg: {
        "results": segment_results.get(seg, {}),
        "error": segment_errors.get(seg),
        "label": _SEGMENT_LABELS.get(seg, seg),
    }
    for seg in segments_selected
}

# Log run
try:
    record = RunRecord(
        run_id=run_id,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        csm="",
        client_id=client_id,
        client_name="",
        pipeline="attrition",
        modules_run=sorted(selected),
        runtime_seconds=elapsed,
        status="success" if not segment_errors else "partial",
        output_dir=str(output_path),
        input_file_hash=hash_file(Path(odd_path)),
        result_count=sum(len(r) for r in segment_results.values()),
    )
    log_run(record)
except Exception:
    pass

# Render segment comparison
_render_segment_results(
    st.session_state[f"{PREFIX}_last_segments"],
    elapsed,
    segment_errors if segment_errors else None,
)
