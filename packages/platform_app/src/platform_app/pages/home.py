"""UAP Home -- single-page CSM workflow: select client, pick template, run."""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import streamlit as st

from platform_app.core.module_registry import Product, get_registry
from platform_app.core.run_logger import RunRecord, generate_run_id, hash_file, log_run
from platform_app.core.session_manager import (
    KNOWN_DATA_ROOTS,
    auto_detect_files,
    discover_clients,
    discover_csm_folders,
    discover_months,
)
from platform_app.core.templates import load_templates
from platform_app.orchestrator import run_pipeline
from shared.format_odd import check_ics_ready, check_odd_formatted, format_odd

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">UNIFIED ANALYSIS PLATFORM</p>', unsafe_allow_html=True)
st.title("Run Analysis")

# =========================================================================
# STEP 1 -- Select client
# =========================================================================
st.markdown('<p class="uap-label">STEP 1 / SELECT CLIENT</p>', unsafe_allow_html=True)

# Auto-detect data root
available_roots = [str(p) for p in KNOWN_DATA_ROOTS if p.is_dir()]

if available_roots:
    saved = st.session_state.get("uap_data_root", "")
    default_idx = available_roots.index(saved) if saved in available_roots else 0
    data_root = Path(
        st.selectbox(
            "Data root",
            options=available_roots,
            index=default_idx,
            label_visibility="collapsed",
        )
    )
else:
    data_root_str = st.text_input(
        "Data root",
        value=st.session_state.get("uap_data_root", ""),
        placeholder=r"M:\ARS\Incoming\ODDD Files",
    )
    if not data_root_str.strip():
        st.info("Enter the path to your ODDD Files directory.")
        st.stop()
    data_root = Path(data_root_str.strip())

if not data_root.is_dir():
    st.error(f"Directory not found: `{data_root}`")
    st.stop()

st.session_state["uap_data_root"] = str(data_root)

# CSM / Month / Client -- three dropdowns in one row
csm_folders = discover_csm_folders(data_root)
if not csm_folders:
    st.warning(f"No CSM folders found in `{data_root}`")
    st.stop()

col_csm, col_month, col_client, col_name = st.columns([2, 1, 1, 2])

with col_csm:
    csm = st.selectbox(
        "CSM",
        options=csm_folders,
        index=csm_folders.index(st.session_state.get("uap_csm", csm_folders[0]))
        if st.session_state.get("uap_csm") in csm_folders
        else 0,
    )
    st.session_state["uap_csm"] = csm

csm_dir = data_root / csm
months = discover_months(csm_dir)

with col_month:
    if not months:
        st.selectbox("Month", options=["No months found"], disabled=True)
        st.stop()
    month = st.selectbox(
        "Month",
        options=months,
        index=months.index(st.session_state.get("uap_month", months[0]))
        if st.session_state.get("uap_month") in months
        else 0,
    )
    st.session_state["uap_month"] = month

month_dir = csm_dir / month
clients = discover_clients(month_dir)

with col_client:
    if not clients:
        st.selectbox("Client ID", options=["No clients found"], disabled=True)
        st.stop()
    client_id = st.selectbox(
        "Client ID",
        options=clients,
        index=clients.index(st.session_state.get("uap_client_id", clients[0]))
        if st.session_state.get("uap_client_id") in clients
        else 0,
    )
    st.session_state["uap_client_id"] = client_id

with col_name:
    client_name = st.text_input(
        "Client Name",
        value=st.session_state.get("uap_client_name", ""),
        placeholder="e.g. Connex CU",
    )
    st.session_state["uap_client_name"] = client_name

# ---------------------------------------------------------------------------
# Auto-detect files
# ---------------------------------------------------------------------------
client_dir = month_dir / client_id
if not client_dir.is_dir():
    st.warning(f"Client directory not found: `{client_dir}`")
    st.stop()

detected = auto_detect_files(client_dir, client_id=client_id)

# Store detected file paths in session
for key in ("oddd", "tran", "ics"):
    path = detected.get(key)
    if path and path.exists():
        st.session_state[f"uap_file_{key}"] = str(path)
    elif f"uap_file_{key}" in st.session_state:
        del st.session_state[f"uap_file_{key}"]

# File status badges
file_checks = [
    ("oddd", "ODD File"),
    ("tran", "Transaction"),
    ("ics", "ICS Data"),
]

badge_html_parts = []
for key, label in file_checks:
    path = detected.get(key)
    if path and path.exists():
        cls = "uap-badge-ready"
        txt = path.name
    else:
        cls = "uap-badge-muted"
        txt = "not found"
    badge_html_parts.append(
        f'<span class="uap-badge {cls}" style="margin-right:4px;">{label}</span>'
        f'<span style="font-family:var(--uap-mono);font-size:0.72rem;color:#64748B;margin-right:16px;">{txt}</span>'
    )

st.markdown(
    f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;padding:0.4rem 0;">{"".join(badge_html_parts)}</div>',
    unsafe_allow_html=True,
)

# Format validation for ODD file
oddd_path = st.session_state.get("uap_file_oddd", "")
ars_formatted = False
ics_ready = False

if oddd_path and Path(oddd_path).exists():
    try:
        ars_status = check_odd_formatted(oddd_path)
        ars_formatted = ars_status.is_formatted
    except Exception:
        ars_status = None

    try:
        ics_status = check_ics_ready(oddd_path)
        ics_ready = ics_status.is_formatted
    except Exception:
        ics_status = None

    format_parts = []
    if ars_formatted:
        format_parts.append('<span class="uap-badge uap-badge-ready">FORMATTED</span>')
    else:
        format_parts.append(
            '<span class="uap-badge" style="background:#FEE2E2;color:#991B1B;">UNFORMATTED</span>'
        )
    if ics_ready:
        format_parts.append('<span class="uap-badge uap-badge-ready">ICS READY</span>')

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;padding:0.2rem 0;">{" ".join(format_parts)}</div>',
        unsafe_allow_html=True,
    )

    # Offer inline format if unformatted
    if not ars_formatted:
        import pandas as pd

        if st.button("Format ODD Now", type="secondary", key="home_format_btn"):
            with st.spinner("Formatting..."):
                df = pd.read_excel(oddd_path)
                df = format_odd(df)
                p = Path(oddd_path)
                out = p.parent / f"{p.stem}-formatted.xlsx"
                df.to_excel(out, index=False, engine="openpyxl")
                st.session_state["uap_file_oddd"] = str(out)
            st.success(f"Saved: `{out.name}`")
            st.rerun()

st.divider()

# =========================================================================
# STEP 2 -- Pick analysis
# =========================================================================
st.markdown('<p class="uap-label">STEP 2 / SELECT ANALYSIS</p>', unsafe_allow_html=True)

templates = load_templates()
registry = get_registry()
module_map = {m.key: m for m in registry}

# Filter templates to those whose files are available
available_templates: dict[str, list[str]] = {}
for tpl_name, tpl_keys in templates.items():
    # Check what products this template needs
    products_needed = {module_map[k].product for k in tpl_keys if k in module_map}
    can_run = True
    if Product.ARS in products_needed and not detected.get("oddd"):
        can_run = False
    if Product.TXN in products_needed and not detected.get("tran"):
        can_run = False
    if Product.ICS in products_needed and not detected.get("ics"):
        can_run = False
    available_templates[tpl_name] = tpl_keys
    if not can_run:
        available_templates[tpl_name] = []  # mark as unavailable

# Template buttons
tpl_names = list(templates.keys())
n_cols = min(len(tpl_names), 4)
tpl_cols = st.columns(n_cols) if n_cols > 0 else []

selected_template = st.session_state.get("uap_selected_template", "")

for i, tpl_name in enumerate(tpl_names):
    tpl_keys = templates[tpl_name]
    is_available = bool(available_templates.get(tpl_name))
    with tpl_cols[i % n_cols]:
        # Count modules by product
        product_counts: dict[str, int] = {}
        for k in tpl_keys:
            if k in module_map:
                pname = module_map[k].product.value.upper()
                product_counts[pname] = product_counts.get(pname, 0) + 1

        detail = " / ".join(f"{ct} {p}" for p, ct in sorted(product_counts.items()))
        btn_type = "primary" if tpl_name == selected_template else "secondary"

        if st.button(
            tpl_name,
            key=f"home_tpl_{i}",
            use_container_width=True,
            type=btn_type,
            disabled=not is_available,
            help=f"{len(tpl_keys)} modules: {detail}" if is_available else "Missing data files",
        ):
            st.session_state["uap_selected_template"] = tpl_name
            st.session_state["uap_selected_modules"] = set(tpl_keys)
            st.rerun()

selected_modules = st.session_state.get("uap_selected_modules", set())

if selected_modules:
    st.caption(
        f"**{selected_template or 'Custom'}** -- {len(selected_modules)} modules selected"
    )
else:
    st.info("Pick an analysis template above to continue.")
    st.stop()

st.divider()

# =========================================================================
# STEP 3 -- Run
# =========================================================================
st.markdown('<p class="uap-label">STEP 3 / RUN</p>', unsafe_allow_html=True)

# Determine which pipelines are needed
needed_products: set[Product] = set()
for key in selected_modules:
    if key in module_map:
        needed_products.add(module_map[key].product)

# Pre-flight validation
errors: list[str] = []
if not client_id:
    errors.append("Client ID not set.")
if Product.ARS in needed_products:
    if not oddd_path or not Path(oddd_path).exists():
        errors.append("ARS ODD file not found.")
    elif not ars_formatted:
        errors.append("ODD file is unformatted. Click **Format ODD Now** above.")
if Product.TXN in needed_products:
    tran_path = st.session_state.get("uap_file_tran", "")
    if not tran_path or not Path(tran_path).exists():
        errors.append("Transaction file not found.")
if Product.ICS in needed_products:
    if not oddd_path or not Path(oddd_path).exists():
        errors.append("ICS ODD file not found.")
    elif not ics_ready:
        errors.append("ODD file missing ICS fields. Run ICS append first.")

if errors:
    for e in errors:
        st.error(e)
    st.stop()

# Pre-flight summary
pf1, pf2, pf3 = st.columns(3)
pf1.metric("Client", client_id)
pf2.metric("Pipelines", ", ".join(p.value.upper() for p in sorted(needed_products, key=lambda x: x.value)))
pf3.metric("Modules", len(selected_modules))

run_btn = st.button(
    f"Run {len(selected_modules)} Modules",
    type="primary",
    use_container_width=True,
    key="home_run_btn",
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

tran_path = st.session_state.get("uap_file_tran", "")
ics_path = st.session_state.get("uap_file_ics", "")
odd_path = st.session_state.get("uap_file_odd", "")
t0 = time.time()

for product in sorted(needed_products, key=lambda p: p.value):
    pipeline_name = product.value
    completed += 1
    overall_progress.progress(
        completed / (total_pipelines + 1),
        text=f"[{completed}/{total_pipelines}] Running {pipeline_name.upper()}...",
    )

    input_files: dict[str, Path] = {}
    if product == Product.ARS:
        input_files["oddd"] = Path(oddd_path)
        out = Path(oddd_path).parent / "output"
    elif product == Product.TXN:
        input_files["tran"] = Path(tran_path)
        if odd_path and Path(odd_path).exists():
            input_files["odd"] = Path(odd_path)
        out = Path(tran_path).parent / "output_txn"
    elif product == Product.ICS:
        input_files["ics"] = Path(ics_path) if ics_path else Path(oddd_path)
        out = Path(oddd_path).parent / "output_ics"
    else:
        continue

    out.mkdir(parents=True, exist_ok=True)

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
                label=f"{pipeline_name.upper()} -- {elapsed:.1f}s",
                state="complete",
                expanded=False,
            )

        all_results[pipeline_name] = results
        all_output_dirs[pipeline_name] = out
    except Exception:
        elapsed = time.time() - t0
        pipeline_errors[pipeline_name] = traceback.format_exc()
        st.error(f"{pipeline_name.upper()} failed after {elapsed:.1f}s")

overall_progress.progress(1.0, text="Complete!")

# ---------------------------------------------------------------------------
# Log run
# ---------------------------------------------------------------------------
run_status = "success" if not pipeline_errors else ("partial" if all_results else "error")
first_file = oddd_path or tran_path or ics_path

record = RunRecord(
    run_id=run_id,
    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    csm=csm,
    client_id=client_id,
    client_name=client_name,
    pipeline=",".join(sorted(p.value for p in needed_products)),
    modules_run=sorted(selected_modules),
    runtime_seconds=round(time.time() - t0, 1),
    status=run_status,
    output_dir=str(out),
    input_file_hash=hash_file(Path(first_file)) if first_file else "",
    result_count=sum(len(r) for r in all_results.values()),
)

try:
    log_run(record)
except Exception:
    pass

# Store results
st.session_state["uap_last_results"] = all_results
st.session_state["uap_last_output_dirs"] = all_output_dirs
st.session_state["uap_last_errors"] = pipeline_errors
st.session_state["uap_last_run_id"] = run_id

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">COMPLETE</p>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("Pipelines", f"{len(all_results)}/{total_pipelines}")
m2.metric("Results", sum(len(r) for r in all_results.values()))
m3.metric("Run ID", run_id)

if pipeline_errors:
    for name, tb in pipeline_errors.items():
        with st.expander(f"Error: {name.upper()}", expanded=False):
            st.code(tb)

if all_results:
    st.success("Analysis complete! Go to **View Outputs** to download files.")
    st.toast("Analysis complete!", icon=":material/check_circle:")
