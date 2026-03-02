"""ICS Pipeline -- dedicated page for ICS analysis + Referral Intelligence."""

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

logger = logging.getLogger("platform_app.pipeline_ics")

PREFIX = "ics_pipe"

st.markdown(
    '<h2 style="margin-bottom:0.2rem;">ICS Analysis</h2>'
    '<p style="color:#64748B;margin-bottom:1.5rem;">'
    "ICS account analysis -- source distribution, demographics, cohorts, "
    "activity, portfolio, and referral intelligence</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# File Inputs
# ---------------------------------------------------------------------------
st.markdown("**Data Files**")
ics_path = render_file_input(
    "ICS / ODD File (.xlsx)",
    f"{PREFIX}_ics",
    filetypes=".xlsx",
    help_text="ODD file with ICS columns (after ICS append) or standalone ICS file",
)

# Client ID
client_id = st.text_input(
    "Client ID",
    value=st.session_state.get(f"{PREFIX}_client_id", ""),
    key=f"_input_{PREFIX}_client_id",
    placeholder="e.g. 1234",
)
st.session_state[f"{PREFIX}_client_id"] = client_id

# ---------------------------------------------------------------------------
# Referral Intelligence
# ---------------------------------------------------------------------------
st.divider()
st.markdown("**Referral Intelligence**")
enable_referral = st.toggle(
    "Enable Referral Intelligence Engine",
    value=st.session_state.get(f"{PREFIX}_referral_on", False),
    key=f"_toggle_{PREFIX}_referral",
    help="Run the 8-step Referral Intelligence pipeline on a referral data file",
)
st.session_state[f"{PREFIX}_referral_on"] = enable_referral

referral_path = ""
if enable_referral:
    referral_path = render_file_input(
        "Referral File (.xlsx)",
        f"{PREFIX}_referral",
        filetypes=".xlsx",
        help_text="Excel file with referral source data (Referrer, Account, Date columns)",
    )

    # Referral analyses info
    st.caption(
        "Referral Intelligence produces 8 analyses: "
        "Top Referrers, Emerging Referrers, Staff Multipliers, "
        "Branch Influence Density, Code Health Report, "
        "Network Analysis, Temporal Velocity, Referrer Scorecard"
    )

# Per-Section Decks
st.divider()
st.markdown("**Output Options**")
per_section = st.toggle(
    "Generate per-section module decks",
    value=st.session_state.get(f"{PREFIX}_per_section", False),
    key=f"_toggle_{PREFIX}_per_section",
    help="Produce one PPTX per section (Summary, Portfolio Health, etc.) in addition to Primary + Secondary decks",
)
st.session_state[f"{PREFIX}_per_section"] = per_section

# Output directory
out_default = ""
if ics_path and Path(ics_path).exists():
    out_default = str(Path(ics_path).parent / "output_ics")
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
st.markdown("**Select ICS Analyses**")
render_preset_picker(Product.ICS, f"{PREFIX}_modules")
selected = render_module_picker(Product.ICS, f"{PREFIX}_modules")

st.divider()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors: list[str] = []
if not ics_path or not Path(ics_path).exists():
    errors.append("ICS/ODD file is required.")
if not client_id:
    errors.append("Client ID is required.")
if not out_dir:
    errors.append("Output directory is required.")
if enable_referral and (not referral_path or not Path(referral_path).exists()):
    errors.append("Referral file is required when Referral Intelligence is enabled.")

# Count total analyses (ICS + referral if enabled)
total_count = len(selected) + (8 if enable_referral else 0)

if errors:
    for e in errors:
        st.warning(e)

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
should_run = render_run_button("Run ICS Analysis", PREFIX, total_count)

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
        "ics",
        errors=prev_errors,
    )
    # Show referral results separately if they exist
    prev_ref = st.session_state.get(f"{PREFIX}_last_referral_results")
    prev_ref_err = st.session_state.get(f"{PREFIX}_last_referral_error")
    if prev_ref is not None or prev_ref_err:
        st.divider()
        st.markdown(
            '<p style="font-size:0.82rem;font-weight:700;color:#475569;'
            'text-transform:uppercase;">REFERRAL INTELLIGENCE RESULTS</p>',
            unsafe_allow_html=True,
        )
        if prev_ref_err:
            st.error("Referral pipeline failed")
            with st.expander("Error Details"):
                st.code(prev_ref_err)
        elif prev_ref:
            ref_result = prev_ref
            n_analyses = len(ref_result.get("analyses", []))
            n_charts = len(ref_result.get("chart_pngs", {}))
            cols = st.columns(3)
            cols[0].metric("Referral Analyses", n_analyses)
            cols[1].metric("Charts Generated", n_charts)
            cols[2].metric("Status", "Complete")
    st.stop()

if not should_run:
    st.stop()

if errors:
    st.session_state[f"{PREFIX}_running"] = False
    st.stop()

# ---------------------------------------------------------------------------
# Execution -- ICS Pipeline
# ---------------------------------------------------------------------------
run_id = generate_run_id()
output_path = Path(out_dir)
output_path.mkdir(parents=True, exist_ok=True)

bar, status_text = render_progress(PREFIX, "ics")

input_files: dict[str, Path] = {"ics": Path(ics_path)}
client_config: dict = {"client_id": client_id}
if selected:
    client_config["module_ids"] = sorted(selected)
if per_section:
    client_config["per_section"] = True

t0 = time.time()
pipeline_error: str | None = None
results: dict = {}

try:
    results = run_pipeline(
        "ics",
        input_files=input_files,
        output_dir=output_path,
        client_id=client_id,
        client_config=client_config,
        progress_callback=make_progress_callback(bar, status_text, "ics", PREFIX),
    )
    elapsed_ics = round(time.time() - t0, 1)
    bar.progress(1.0, text=f"ICS complete -- {len(results)} results in {elapsed_ics}s")
    status_text.empty()
    logger.info("ICS complete: %d results in %.1fs", len(results), elapsed_ics)
except Exception:
    import traceback

    elapsed_ics = round(time.time() - t0, 1)
    pipeline_error = traceback.format_exc()
    bar.progress(1.0, text=f"ICS FAILED ({elapsed_ics}s)")
    logger.error("ICS failed:\n%s", pipeline_error)

# ---------------------------------------------------------------------------
# Execution -- Referral Intelligence (if enabled)
# ---------------------------------------------------------------------------
referral_result_data: dict | None = None
referral_error: str | None = None

if enable_referral and referral_path and not pipeline_error:
    st.divider()
    st.markdown(
        '<p style="font-size:0.82rem;font-weight:700;color:#475569;'
        'text-transform:uppercase;">REFERRAL INTELLIGENCE</p>',
        unsafe_allow_html=True,
    )
    ref_bar = st.progress(0, text="Referral Intelligence -- Initializing...")
    ref_text = st.empty()

    try:
        from ics_toolkit.referral.pipeline import export_outputs
        from ics_toolkit.referral.pipeline import run_pipeline as run_referral
        from ics_toolkit.settings import ReferralSettings

        ref_settings = ReferralSettings(
            input_file=Path(referral_path),
            output_dir=output_path / "referral",
            client_id=client_id,
        )

        def _ref_progress(step: int, total: int, msg: str) -> None:
            frac = step / total if total > 0 else 0
            ref_bar.progress(min(frac, 0.99), text=f"Referral -- {msg}")
            ref_text.markdown(f"**REFERRAL** -- {msg}")

        t_ref = time.time()
        ref_result = run_referral(ref_settings, on_progress=_ref_progress)
        ref_elapsed = round(time.time() - t_ref, 1)

        # Export outputs
        export_outputs(ref_result)

        n_analyses = len(ref_result.analyses)
        n_charts = len(ref_result.chart_pngs)
        ref_bar.progress(
            1.0,
            text=f"Referral complete -- {n_analyses} analyses, {n_charts} charts in {ref_elapsed}s",
        )
        ref_text.empty()

        referral_result_data = {
            "analyses": [{"name": a.name, "error": a.error} for a in ref_result.analyses],
            "chart_pngs": {k: True for k in ref_result.chart_pngs},
        }
        logger.info(
            "Referral complete: %d analyses, %d charts in %.1fs", n_analyses, n_charts, ref_elapsed
        )
    except Exception:
        import traceback

        referral_error = traceback.format_exc()
        ref_bar.progress(1.0, text="Referral FAILED")
        logger.error("Referral failed:\n%s", referral_error)

elapsed = round(time.time() - t0, 1)

# Store results
st.session_state[f"{PREFIX}_running"] = False
st.session_state[f"{PREFIX}_last_results"] = results
st.session_state[f"{PREFIX}_last_error"] = pipeline_error
st.session_state[f"{PREFIX}_last_elapsed"] = elapsed
st.session_state[f"{PREFIX}_last_out_dir"] = str(output_path)
st.session_state[f"{PREFIX}_last_referral_results"] = referral_result_data
st.session_state[f"{PREFIX}_last_referral_error"] = referral_error

# Log run
try:
    record = RunRecord(
        run_id=run_id,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        csm="",
        client_id=client_id,
        client_name="",
        pipeline="ics" + ("+referral" if enable_referral else ""),
        modules_run=sorted(selected),
        runtime_seconds=elapsed,
        status="success" if not pipeline_error else "error",
        output_dir=str(output_path),
        input_file_hash=hash_file(Path(ics_path)),
        result_count=len(results),
    )
    log_run(record)
except Exception:
    pass

# Render results
render_results(results, output_path, elapsed, "ics", errors=pipeline_error)

if referral_result_data and not referral_error:
    st.divider()
    st.markdown(
        '<p style="font-size:0.82rem;font-weight:700;color:#475569;'
        'text-transform:uppercase;">REFERRAL INTELLIGENCE RESULTS</p>',
        unsafe_allow_html=True,
    )
    n_a = len(referral_result_data.get("analyses", []))
    n_c = len(referral_result_data.get("chart_pngs", {}))
    cols = st.columns(3)
    cols[0].metric("Referral Analyses", n_a)
    cols[1].metric("Charts Generated", n_c)
    cols[2].metric("Status", "Complete")
    st.success(f"Referral Intelligence -- {n_a} analyses, {n_c} charts")
elif referral_error:
    st.divider()
    st.error("Referral Intelligence failed")
    with st.expander("Referral Error Details"):
        st.code(referral_error)
