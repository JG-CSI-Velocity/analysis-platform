"""TXN Pipeline -- dedicated page for transaction intelligence.

Supports account segment filters to analyze transactions for:
- All accounts (full portfolio)
- ARS Responders (accounts that responded to mailer campaigns)
- ICS Accounts (accounts opened via ICS referral/direct mail)
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
    render_results,
    render_run_button,
)

logger = logging.getLogger("platform_app.pipeline_txn")

PREFIX = "txn_pipe"

_SEGMENT_LABELS = {
    "all": "All Accounts",
    "ars_responders": "ARS Responders",
    "ics_accounts": "ICS Accounts",
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
        st.warning(
            f"{n_ok}/{n_segments} segments complete, {n_segments - n_ok} failed"
        )

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
                        status = (
                            "OK" if getattr(result, "success", True) else "FAIL"
                        )
                        color = "#16A34A" if status == "OK" else "#DC2626"
                        st.markdown(
                            f'<span style="color:{color};font-weight:600;">'
                            f"{status}</span> {name}",
                            unsafe_allow_html=True,
                        )


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
    help_text="Required for Demographics (M11), Campaigns (M12), Lifecycle (M14), "
    "and for ARS/ICS segment filtering",
)

if not odd_path:
    st.caption(
        "Without ODD: Demographics, Campaigns, Lifecycle analyses will be skipped. "
        "Account segment filters require ODD."
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
# Account Segment Filters
# ---------------------------------------------------------------------------
st.markdown("**Account Segments**")
st.caption(
    "Filter transactions to specific account populations. "
    "ARS/ICS segments require the ODD file with mailer and ICS columns."
)

seg_all = st.checkbox(
    "All Accounts (full portfolio)",
    value=st.session_state.get(f"{PREFIX}_seg_all", True),
    key=f"_cb_{PREFIX}_seg_all",
    help="Full transaction portfolio -- no account filtering",
)
st.session_state[f"{PREFIX}_seg_all"] = seg_all

seg_ars = st.checkbox(
    "ARS Responders",
    value=st.session_state.get(f"{PREFIX}_seg_ars", False),
    key=f"_cb_{PREFIX}_seg_ars",
    help="Transactions from accounts that responded to ARS mailer campaigns. "
    'Answers: "Where do ARS responders spend?"',
)
st.session_state[f"{PREFIX}_seg_ars"] = seg_ars

seg_ics = st.checkbox(
    "ICS Accounts",
    value=st.session_state.get(f"{PREFIX}_seg_ics", False),
    key=f"_cb_{PREFIX}_seg_ics",
    help="Transactions from accounts opened via ICS (referral or direct mail). "
    'Answers: "What spending patterns do ICS accounts have?"',
)
st.session_state[f"{PREFIX}_seg_ics"] = seg_ics

segments_selected: list[str] = []
if seg_all:
    segments_selected.append("all")
if seg_ars:
    segments_selected.append("ars_responders")
if seg_ics:
    segments_selected.append("ics_accounts")

if not segments_selected:
    st.warning("Select at least one segment.")

# Warn if segment filter needs ODD
if (seg_ars or seg_ics) and not odd_path:
    st.warning("ARS/ICS segment filters require the ODD file.")

st.divider()

# ---------------------------------------------------------------------------
# Analysis Selection
# ---------------------------------------------------------------------------
st.markdown("**Select Analyses**")
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
    auto_added.append("Competitor Detection (required by selected competitor analyses)")
if selected & _FINANCIAL_DEPS and "txn_financial_services_detection" not in selected:
    selected.add("txn_financial_services_detection")
    auto_added.append("Financial Services Detection (required by Financial Summary)")
if selected & _SCORECARD_DEPS:
    for dep in ("txn_interchange_summary", "txn_member_segments"):
        if dep not in selected:
            selected.add(dep)
            auto_added.append(
                f"{dep.replace('txn_', '').replace('_', ' ').title()} (required by Scorecard)"
            )

if auto_added:
    st.info("Auto-added dependencies: " + "; ".join(auto_added))
    st.session_state[f"{PREFIX}_modules"] = selected

# ODD-dependent analysis warnings
_ODD_ANALYSES = {"txn_demographics", "txn_campaigns", "txn_lifecycle"}
if selected & _ODD_ANALYSES and not odd_path:
    st.warning(
        "Selected analyses require ODD file: "
        + ", ".join(
            m.replace("txn_", "").replace("_", " ").title()
            for m in sorted(selected & _ODD_ANALYSES)
        )
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
if not segments_selected:
    errors.append("Select at least one account segment.")

if errors:
    for e in errors:
        st.warning(e)

# Total runs = segments x analyses
n_segments = len(segments_selected)
run_label = (
    f"Run TXN ({len(selected)} analyses x "
    f"{n_segments} segment{'s' if n_segments > 1 else ''})"
)

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
should_run = render_run_button(run_label, PREFIX, len(selected) * n_segments)

# Show previous results
prev_results = st.session_state.get(f"{PREFIX}_last_results")
prev_errors = st.session_state.get(f"{PREFIX}_last_error")
prev_elapsed = st.session_state.get(f"{PREFIX}_last_elapsed", 0)
prev_out = st.session_state.get(f"{PREFIX}_last_out_dir", "")
prev_segments = st.session_state.get(f"{PREFIX}_last_segments", {})

if not should_run and (prev_results is not None or prev_errors):
    if prev_segments and len(prev_segments) > 1:
        _render_segment_results(prev_segments, prev_elapsed, prev_errors)
    else:
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
# Execution -- run TXN for each segment
# ---------------------------------------------------------------------------
run_id = generate_run_id()
output_path = Path(out_dir)
output_path.mkdir(parents=True, exist_ok=True)

t0 = time.time()

# Single segment (All only) -- simple path
if segments_selected == ["all"]:
    bar, status_text = render_progress(PREFIX, "txn")

    input_files: dict[str, Path] = {"tran": Path(txn_path)}
    if odd_path and Path(odd_path).exists():
        input_files["odd"] = Path(odd_path)

    client_config: dict = {"client_id": client_id}
    if selected:
        client_config["module_ids"] = sorted(selected)

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
    st.session_state[f"{PREFIX}_last_segments"] = {}

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

    render_results(results, output_path, elapsed, "txn", errors=pipeline_error)

else:
    # Multi-segment path
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

        bar, status_text = render_progress(
            f"{PREFIX}_{segment}", f"txn ({seg_label})"
        )

        input_files = {"tran": Path(txn_path)}
        if odd_path and Path(odd_path).exists():
            input_files["odd"] = Path(odd_path)

        client_config = {
            "client_id": client_id,
            "txn_segment": segment,
        }
        if selected:
            client_config["module_ids"] = sorted(selected)

        try:
            seg_out.mkdir(parents=True, exist_ok=True)
            results = run_pipeline(
                "txn",
                input_files=input_files,
                output_dir=seg_out,
                client_id=client_id,
                client_config=client_config,
                progress_callback=make_progress_callback(
                    bar, status_text, f"txn ({seg_label})", PREFIX
                ),
            )
            bar.progress(
                1.0, text=f"{seg_label} complete -- {len(results)} results"
            )
            status_text.empty()
            segment_results[segment] = results
            logger.info("TXN %s complete: %d results", segment, len(results))
        except Exception:
            import traceback

            tb = traceback.format_exc()
            segment_errors[segment] = tb
            bar.progress(1.0, text=f"{seg_label} FAILED")
            logger.error("TXN %s failed:\n%s", segment, tb)

    elapsed = round(time.time() - t0, 1)

    # Store results
    st.session_state[f"{PREFIX}_running"] = False
    st.session_state[f"{PREFIX}_last_results"] = segment_results
    st.session_state[f"{PREFIX}_last_error"] = (
        segment_errors if segment_errors else None
    )
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
            pipeline="txn",
            modules_run=sorted(selected),
            runtime_seconds=elapsed,
            status="success" if not segment_errors else "partial",
            output_dir=str(output_path),
            input_file_hash=hash_file(Path(txn_path)),
            result_count=sum(len(r) for r in segment_results.values()),
        )
        log_run(record)
    except Exception:
        pass

    _render_segment_results(
        st.session_state[f"{PREFIX}_last_segments"],
        elapsed,
        segment_errors if segment_errors else None,
    )
