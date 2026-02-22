"""UAP Run Analysis -- execute selected modules with progress tracking."""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import streamlit as st

from platform_app.core.module_registry import Product, get_registry
from platform_app.core.run_logger import RunRecord, generate_run_id, hash_file, log_run
from platform_app.orchestrator import run_pipeline
from shared.format_odd import check_ics_ready, check_odd_formatted

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">ANALYSIS / RUN</p>', unsafe_allow_html=True)
st.title("Run Analysis")

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
selected_modules = st.session_state.get("uap_selected_modules", set())
client_id = st.session_state.get("uap_client_id", "")
client_name = st.session_state.get("uap_client_name", "")

# Determine which pipelines are needed based on selected modules
registry = get_registry()
module_map = {m.key: m for m in registry}

needed_products: set[Product] = set()
for key in selected_modules:
    if key in module_map:
        needed_products.add(module_map[key].product)

# File readiness
file_status: dict[str, tuple[bool, str]] = {}
oddd_path = st.session_state.get("uap_file_oddd", "")
tran_path = st.session_state.get("uap_file_tran", "")
odd_path = st.session_state.get("uap_file_odd", "")
ics_path = st.session_state.get("uap_file_ics", "")

if Product.ARS in needed_products:
    file_status["ARS"] = (bool(oddd_path and Path(oddd_path).exists()), oddd_path)
if Product.TXN in needed_products:
    file_status["TXN"] = (bool(tran_path and Path(tran_path).exists()), tran_path)
    if odd_path:
        file_status["TXN ODD"] = (bool(Path(odd_path).exists()), odd_path)
if Product.ICS in needed_products:
    file_status["ICS"] = (bool(ics_path and Path(ics_path).exists()), ics_path)

# ---------------------------------------------------------------------------
# Pre-flight summary
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">PRE-FLIGHT CHECK</p>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Modules", len(selected_modules))
c2.metric("Pipelines", len(needed_products))
c3.metric("Client", client_id or "Not set")
c4.metric("Files Ready", f"{sum(v[0] for v in file_status.values())}/{len(file_status)}")

# Status grid
if file_status:
    for name, (ready, path) in file_status.items():
        badge = "uap-badge-ready" if ready else "uap-badge-error"
        status = "READY" if ready else "MISSING"
        file_display = Path(path).name if path else "no file"
        st.markdown(
            f'<div style="display: flex; align-items: center; padding: 0.3rem 0;">'
            f'<span class="uap-badge {badge}" style="min-width: 60px; text-align: center;">{status}</span>'
            f'<span style="font-family: var(--uap-sans); font-size: 0.88rem; margin-left: 0.75rem;">{name}</span>'
            f'<span style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8; margin-left: auto;">{file_display}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

# Format validation gates
if Product.ARS in needed_products and oddd_path and Path(oddd_path).exists():
    try:
        ars_status = check_odd_formatted(oddd_path)
        badge_cls = "uap-badge-ready" if ars_status.is_formatted else "uap-badge-error"
        badge_txt = "FORMATTED" if ars_status.is_formatted else "UNFORMATTED"
        st.markdown(
            f'<div style="display: flex; align-items: center; padding: 0.3rem 0;">'
            f'<span class="uap-badge {badge_cls}" style="min-width: 60px; text-align: center;">{badge_txt}</span>'
            f'<span style="font-family: var(--uap-sans); font-size: 0.88rem; margin-left: 0.75rem;">ARS Format</span>'
            f'<span style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8; margin-left: auto;">'
            f'{len(ars_status.found_columns)}/{len(ars_status.found_columns) + len(ars_status.missing_columns)} columns</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        ars_status = None
else:
    ars_status = None

if Product.ICS in needed_products and oddd_path and Path(oddd_path).exists():
    try:
        ics_status = check_ics_ready(oddd_path)
        badge_cls = "uap-badge-ready" if ics_status.is_formatted else "uap-badge-error"
        badge_txt = "ICS READY" if ics_status.is_formatted else "ICS MISSING"
        st.markdown(
            f'<div style="display: flex; align-items: center; padding: 0.3rem 0;">'
            f'<span class="uap-badge {badge_cls}" style="min-width: 60px; text-align: center;">{badge_txt}</span>'
            f'<span style="font-family: var(--uap-sans); font-size: 0.88rem; margin-left: 0.75rem;">ICS Fields</span>'
            f'<span style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8; margin-left: auto;">'
            f'{len(ics_status.found_columns)}/{len(ics_status.found_columns) + len(ics_status.missing_columns)} columns</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    except Exception:
        ics_status = None
else:
    ics_status = None

# Validation
errors: list[str] = []
if not selected_modules:
    errors.append("No modules selected. Go to **Module Library** to choose modules.")
if not client_id:
    errors.append("Client ID not set. Go to **Workspace** to configure.")
for name, (ready, _) in file_status.items():
    if not ready:
        errors.append(f"{name} data file missing. Go to **Data Ingestion** to upload.")
if Product.ARS in needed_products and ars_status and not ars_status.is_formatted:
    errors.append(
        "ARS ODD file is unformatted. Format via **Data Ingestion** or CLI `ars format`."
    )
if Product.ICS in needed_products and ics_status and not ics_status.is_formatted:
    errors.append(
        "ODD file missing ICS fields (ICS Account, ICS Source). Run ICS append first."
    )

if errors:
    st.divider()
    for e in errors:
        st.error(e)
    st.stop()

# ---------------------------------------------------------------------------
# Output configuration
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">OUTPUT</p>', unsafe_allow_html=True)

output_base = st.text_input(
    "Output directory",
    value=st.session_state.get("uap_output_dir", ""),
    placeholder="Leave empty to auto-generate from input file location",
)

# ---------------------------------------------------------------------------
# Run button
# ---------------------------------------------------------------------------
st.divider()

run_btn = st.button(
    f"Execute {len(selected_modules)} Modules",
    type="primary",
    use_container_width=True,
    key="run_execute",
)

if not run_btn:
    st.stop()

# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
run_id = generate_run_id()
all_results: dict[str, dict] = {}
all_output_dirs: dict[str, Path] = {}
pipeline_errors: dict[str, str] = {}

overall_progress = st.progress(0, text="Initializing...")
total_pipelines = len(needed_products)
completed = 0

for product in sorted(needed_products, key=lambda p: p.value):
    pipeline_name = product.value
    completed += 1
    overall_progress.progress(
        completed / (total_pipelines + 1),
        text=f"[{completed}/{total_pipelines}] Running {pipeline_name.upper()}...",
    )

    # Resolve input files
    input_files: dict[str, Path] = {}
    if product == Product.ARS:
        input_files["oddd"] = Path(oddd_path)
        out = (
            Path(oddd_path).parent / "output"
            if not output_base.strip()
            else Path(output_base.strip()) / "ars"
        )
    elif product == Product.TXN:
        input_files["tran"] = Path(tran_path)
        if odd_path and Path(odd_path).exists():
            input_files["odd"] = Path(odd_path)
        out = (
            Path(tran_path).parent / "output_txn"
            if not output_base.strip()
            else Path(output_base.strip()) / "txn"
        )
    elif product == Product.ICS:
        input_files["ics"] = Path(ics_path)
        out = (
            Path(ics_path).parent / "output_ics"
            if not output_base.strip()
            else Path(output_base.strip()) / "ics"
        )
    else:
        continue

    out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    try:
        with st.status(f"Running {pipeline_name.upper()}...", expanded=True) as status:
            messages: list[str] = []

            def _on_progress(msg: str, msgs: list[str] = messages, st_status=status) -> None:
                msgs.append(msg)
                st_status.write(msg)

            results = run_pipeline(
                pipeline_name,
                input_files=input_files,
                output_dir=out,
                client_id=client_id,
                client_name=client_name,
                progress_callback=_on_progress,
            )
            elapsed = time.time() - t0
            status.update(
                label=f"{pipeline_name.upper()} -- {elapsed:.1f}s", state="complete", expanded=False
            )

        all_results[pipeline_name] = results
        all_output_dirs[pipeline_name] = out
    except Exception:
        elapsed = time.time() - t0
        pipeline_errors[pipeline_name] = traceback.format_exc()
        st.error(f"{pipeline_name.upper()} failed after {elapsed:.1f}s")

overall_progress.progress(1.0, text="Complete!")

# ---------------------------------------------------------------------------
# Log the run
# ---------------------------------------------------------------------------
total_time = time.time() - t0 if not all_results else sum(1 for _ in [])  # approximate
status = "success" if not pipeline_errors else ("partial" if all_results else "error")

# Get first input file for hashing
first_file = oddd_path or tran_path or ics_path
record = RunRecord(
    run_id=run_id,
    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    csm=st.session_state.get("uap_csm", ""),
    client_id=client_id,
    client_name=client_name,
    pipeline=",".join(sorted(p.value for p in needed_products)),
    modules_run=sorted(selected_modules),
    runtime_seconds=round(time.time() - t0, 1) if "t0" in dir() else 0,
    status=status,
    output_dir=output_base.strip() or str(out),
    input_file_hash=hash_file(Path(first_file)) if first_file else "",
    result_count=sum(len(r) for r in all_results.values()),
)

try:
    log_run(record)
except Exception:
    pass  # logging failure shouldn't block results

# Store results
st.session_state["uap_last_results"] = all_results
st.session_state["uap_last_output_dirs"] = all_output_dirs
st.session_state["uap_last_errors"] = pipeline_errors
st.session_state["uap_last_run_id"] = run_id

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">RUN COMPLETE</p>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("Pipelines", f"{len(all_results)}/{total_pipelines}")
m2.metric("Results", sum(len(r) for r in all_results.values()))
m3.metric("Run ID", run_id)

if pipeline_errors:
    for name, tb in pipeline_errors.items():
        with st.expander(f"Error: {name.upper()}", expanded=False):
            st.code(tb)

if all_results:
    st.success("Go to **View Outputs** to see results and download files.")
    st.toast("Analysis complete!", icon=":material/check_circle:")
