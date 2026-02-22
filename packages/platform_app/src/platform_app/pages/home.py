"""UAP Home -- single-page CSM workflow: select client, pick template, run."""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import streamlit as st

from ics_toolkit.client_registry import (
    load_raw_client_entry,
    resolve_master_config_path,
)
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


def _format_list(value: object) -> str:
    """Format a config value (list or string) as comma-separated string."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, str) and value:
        return value
    return ""


_FLAVOR = {
    "ars": [
        "Crunching debit card numbers...",
        "Digging into attrition patterns...",
        "Building the story for your client...",
        "Reg E, mailers, value tiers -- the works...",
    ],
    "ics": [
        "Mapping ICS account relationships...",
        "Tracing referral sources...",
        "This ICS data is looking interesting...",
    ],
    "txn": [
        "Scanning transaction patterns...",
        "Finding where the money goes...",
        "Competitor intel incoming...",
    ],
}


def _flavor_text(pipeline: str, phase: str = "start") -> str:
    """Return a concise flavor line for the progress bar."""
    import random

    lines = _FLAVOR.get(pipeline, [f"Running {pipeline.upper()}..."])
    return random.choice(lines)  # noqa: S311


def _make_status_line(msg: str, pipeline: str) -> str:
    """Shorten a verbose progress callback to a clean one-liner."""
    # Strip common prefixes from runner callbacks
    short = msg
    for prefix in ("Starting ", "ARS complete: ", "ICS complete: ", "TXN complete: "):
        if short.startswith(prefix):
            short = short[len(prefix) :]
            break
    # Capitalize pipeline tag
    return f"{pipeline.upper()} -- {short}"


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

# ---------------------------------------------------------------------------
# Auto-detect files (before name input so we can extract client name)
# ---------------------------------------------------------------------------
client_dir = month_dir / client_id
if not client_dir.is_dir():
    with col_name:
        client_name = st.text_input(
            "Client Name",
            value=st.session_state.get("uap_client_name", ""),
            placeholder="e.g. Connex CU",
        )
        st.session_state["uap_client_name"] = client_name
    st.warning(f"Client directory not found: `{client_dir}`")
    st.stop()

detected = auto_detect_files(client_dir, client_id=client_id)

# Extract client name from ODD filename (e.g. "1759_Connex CU_2026.02.xlsx")
_auto_name = st.session_state.get("uap_client_name", "")
if not _auto_name:
    oddd_detected = detected.get("oddd")
    if oddd_detected:
        _stem = oddd_detected.stem.replace("-formatted", "")
        _parts = _stem.split("_", maxsplit=2)
        if len(_parts) > 1:
            _auto_name = _parts[1]
    if not _auto_name:
        try:
            _cfg_path = resolve_master_config_path()
            if _cfg_path:
                from ics_toolkit.client_registry import load_master_config

                _reg = load_master_config(_cfg_path)
                _entry = _reg.get(client_id)
                if _entry and _entry.client_name:
                    _auto_name = _entry.client_name
        except Exception:
            pass

with col_name:
    client_name = st.text_input(
        "Client Name",
        value=_auto_name,
        placeholder="e.g. Connex CU",
    )
    st.session_state["uap_client_name"] = client_name

# ---------------------------------------------------------------------------
# Format validation (BEFORE badges so ICS fallback is applied first)
# ---------------------------------------------------------------------------
oddd_path = ""
_oddd_file = detected.get("oddd")
if _oddd_file and _oddd_file.exists():
    oddd_path = str(_oddd_file)

ars_formatted = False
ics_ready = False

if oddd_path:
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

# ICS fallback: if ODD has ICS columns but no separate ICS file, use ODD
if ics_ready and not detected.get("ics") and detected.get("oddd"):
    detected["ics"] = detected["oddd"]

# ---------------------------------------------------------------------------
# Store detected file paths in session
# ---------------------------------------------------------------------------
for key in ("oddd", "tran", "ics"):
    path = detected.get(key)
    if path and path.exists():
        st.session_state[f"uap_file_{key}"] = str(path)
    elif f"uap_file_{key}" in st.session_state:
        del st.session_state[f"uap_file_{key}"]

# ---------------------------------------------------------------------------
# File status badges
# ---------------------------------------------------------------------------
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
        # For ICS, note when using ODD as source
        if key == "ics" and detected.get("ics") == detected.get("oddd") and ics_ready:
            txt = f"{path.name} (in ODD)"
        else:
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

# Format status badges
if oddd_path:
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

# Determine which products have data available
_product_available = {
    Product.ARS: bool(detected.get("oddd")),
    Product.TXN: bool(detected.get("tran")),
    Product.ICS: bool(detected.get("ics")),
}

# Filter templates to those whose files are available
available_templates: dict[str, list[str]] = {}
for tpl_name, tpl_keys in templates.items():
    products_needed = {module_map[k].product for k in tpl_keys if k in module_map}
    can_run = all(_product_available.get(p, False) for p in products_needed)
    available_templates[tpl_name] = tpl_keys if can_run else []

# Template buttons
tpl_names = list(templates.keys())
n_cols = min(len(tpl_names), 4)
tpl_cols = st.columns(n_cols) if n_cols > 0 else []

selected_template = st.session_state.get("uap_selected_template", "")

for i, tpl_name in enumerate(tpl_names):
    tpl_keys = templates[tpl_name]
    is_available = bool(available_templates.get(tpl_name))
    with tpl_cols[i % n_cols]:
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
    st.caption(f"**{selected_template or 'Custom'}** -- {len(selected_modules)} modules selected")

# ---------------------------------------------------------------------------
# Module TOC grouped by pipeline
# ---------------------------------------------------------------------------
_modules_by_product: dict[Product, list] = {}
for m in registry:
    _modules_by_product.setdefault(m.product, []).append(m)

for product in (Product.ARS, Product.ICS, Product.TXN):
    modules = _modules_by_product.get(product, [])
    if not modules:
        continue

    avail = _product_available.get(product, False)
    status_icon = "available" if avail else "no data"
    status_color = "#16A34A" if avail else "#94A3B8"
    count = len(modules)

    with st.expander(
        f"{product.value.upper()} -- {count} modules ({status_icon})",
        expanded=avail and bool(selected_modules),
    ):
        for m in sorted(modules, key=lambda x: x.run_order):
            is_selected = m.key in selected_modules
            if is_selected:
                st.markdown(
                    f'<span style="color:{status_color};font-weight:600;">'
                    f'{m.name}</span>'
                    f' <span style="color:#64748B;font-size:0.8rem;">{m.description}</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span style="color:#94A3B8;">{m.name}</span>'
                    f' <span style="color:#CBD5E1;font-size:0.8rem;">{m.description}</span>',
                    unsafe_allow_html=True,
                )

if not selected_modules:
    st.info("Pick an analysis template above to continue.")
    st.stop()

st.divider()

# =========================================================================
# STEP 3 -- Run
# =========================================================================
st.markdown('<p class="uap-label">STEP 3 / RUN</p>', unsafe_allow_html=True)

# Resolve config early (used for both preview and execution)
_config_path = resolve_master_config_path()
_client_config = {"config_path": str(_config_path), "client_id": client_id} if _config_path else {}

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
pf2.metric(
    "Pipelines", ", ".join(p.value.upper() for p in sorted(needed_products, key=lambda x: x.value))
)
pf3.metric("Modules", len(selected_modules))

# ---------------------------------------------------------------------------
# Config preview
# ---------------------------------------------------------------------------
_raw_entry: dict = {}
if _config_path:
    _raw_entry = load_raw_client_entry(_config_path, client_id)

with st.expander("Client Configuration", expanded=False):
    if not _raw_entry:
        st.warning(f"Client {client_id} not found in config. Analysis will use defaults.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("IC Rate", _raw_entry.get("ICRate", "--"))
        c2.metric("NSF/OD Fee", f"${_raw_entry.get('NSF_OD_Fee', '--')}")
        _n_prods = len(_raw_entry.get("EligibleProductCodes", []))
        c3.metric("Eligible Products", _n_prods)
        _n_branches = len(_raw_entry.get("BranchMapping", {}))
        c4.metric("Branches", _n_branches)

        _detail_rows = [
            ("Eligible Status Codes", _format_list(_raw_entry.get("EligibleStatusCodes", []))),
            ("Ineligible Status Codes", _format_list(_raw_entry.get("IneligibleStatusCodes", []))),
            ("Eligible Product Codes", _format_list(_raw_entry.get("EligibleProductCodes", []))),
            ("Ineligible Product Codes", _format_list(_raw_entry.get("IneligibleProductCodes", []))),
            ("Eligible Mail Code", str(_raw_entry.get("EligibleMailCode", "--"))),
            ("Reg E Opt-In Code", _format_list(_raw_entry.get("RegEOptInCode", []))),
        ]
        for label, value in _detail_rows:
            st.markdown(f"**{label}**: {value or '--'}")

        _branches = _raw_entry.get("BranchMapping", {})
        if _branches:
            st.markdown("**Branch Mapping**:")
            _branch_str = " / ".join(f"{k} = {v}" for k, v in _branches.items())
            st.caption(_branch_str)

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

_progress_bar = st.progress(0, text="Warming up the engines...")
_status_line = st.empty()
total_pipelines = len(needed_products)
completed = 0

tran_path = st.session_state.get("uap_file_tran", "")
ics_path = st.session_state.get("uap_file_ics", "")
odd_path = st.session_state.get("uap_file_odd", "")
t0 = time.time()

for product in sorted(needed_products, key=lambda p: p.value):
    pipeline_name = product.value
    completed += 1
    pct = completed / (total_pipelines + 1)

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
    _progress_bar.progress(pct, text=_flavor_text(pipeline_name, "start"))

    def _on_progress(
        msg: str,
        _bar=_progress_bar,
        _line=_status_line,
        _pct=pct,
        _pipe=pipeline_name,
    ) -> None:
        _short = _make_status_line(msg, _pipe)
        _line.caption(_short)

    try:
        results = run_pipeline(
            pipeline_name,
            input_files=input_files,
            output_dir=out,
            client_id=client_id,
            client_name=client_name,
            client_config=_client_config,
            progress_callback=_on_progress,
        )
        all_results[pipeline_name] = results
        all_output_dirs[pipeline_name] = out
        elapsed = time.time() - t0
        _status_line.caption(f"{pipeline_name.upper()} done -- {len(results)} results in {elapsed:.1f}s")
    except Exception:
        elapsed = time.time() - t0
        pipeline_errors[pipeline_name] = traceback.format_exc()
        _status_line.caption(f"{pipeline_name.upper()} failed after {elapsed:.1f}s")

total_elapsed = round(time.time() - t0, 1)
_progress_bar.progress(1.0, text=f"All done in {total_elapsed}s")
_status_line.empty()

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

_total_results = sum(len(r) for r in all_results.values())
_ok_count = len(all_results)
_fail_count = len(pipeline_errors)

if _fail_count == 0:
    st.success(
        f"**{client_name or client_id}** -- {_total_results} analyses across "
        f"{_ok_count} pipeline{'s' if _ok_count > 1 else ''} in {total_elapsed}s"
    )
else:
    st.warning(
        f"**{client_name or client_id}** -- {_ok_count} passed, {_fail_count} failed in {total_elapsed}s"
    )

if pipeline_errors:
    with st.expander("Error details", expanded=False):
        for name, tb in pipeline_errors.items():
            st.markdown(f"**{name.upper()}**")
            st.code(tb)

if all_results:
    # Show key output files (PPTX, Excel) for immediate download
    _DELIVERABLE_EXTS = {".pptx", ".xlsx"}
    _MIME = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    deliverables: list[Path] = []
    for out_dir in all_output_dirs.values():
        if out_dir and Path(out_dir).is_dir():
            deliverables.extend(
                f for f in Path(out_dir).rglob("*") if f.is_file() and f.suffix in _DELIVERABLE_EXTS
            )

    if deliverables:
        for f in sorted(deliverables, key=lambda p: p.name):
            dl_cols = st.columns([4, 1])
            dl_cols[0].markdown(
                f'<span style="font-family:var(--uap-mono);font-size:0.82rem;">{f.name}</span>'
                f'<br><span style="font-size:0.7rem;color:#94A3B8;">{f.parent}</span>',
                unsafe_allow_html=True,
            )
            dl_cols[1].download_button(
                "Download",
                f.read_bytes(),
                file_name=f.name,
                mime=_MIME.get(f.suffix, "application/octet-stream"),
                key=f"home_dl_{f.name}",
            )
    else:
        st.info("No PPTX or Excel files generated. Check View Outputs for charts.")
