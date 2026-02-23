"""RPE Home -- single-page CSM workflow: select client, pick template, run."""

from __future__ import annotations

import json as _json
import logging
import shutil
import tempfile
import time
import warnings
from pathlib import Path

import pandas as pd
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

logger = logging.getLogger("platform_app.home")

# Execution state -- must be initialized before any widget renders
if "uap_running" not in st.session_state:
    st.session_state["uap_running"] = False


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
    """Shorten a verbose progress callback to a readable one-liner."""
    short = msg
    # Strip verbose prefixes
    for prefix in ("Starting ", "ARS complete: ", "ICS complete: ", "TXN complete: "):
        if short.startswith(prefix):
            short = short[len(prefix) :]
            break
    # Make module progress more readable
    if short.startswith("Module ") and ": " in short:
        parts = short.split(": ", 1)
        module_name = parts[1] if len(parts) > 1 else short
        # Convert module_id to readable name (e.g. "dctr.penetration" -> "DCTR Penetration")
        readable = module_name.replace(".", " ").replace("_", " ").title()
        return f"{pipeline.upper()} {parts[0]} -- {readable}"
    return f"{pipeline.upper()} -- {short}"


def _read_tran_file(p: Path) -> pd.DataFrame:
    """Read a single transaction file, auto-detecting delimiter and header.

    Sniffs the first 2 lines to determine delimiter, then reads once.
    Handles comma, tab, and pipe delimiters. For headerless files (common with
    monthly transaction exports), skips the metadata row and assigns standard
    column names from the txn_analysis pipeline.
    """
    from txn_analysis.data_loader import TRANSACTION_COLUMNS, _sniff_delimiter

    sep, has_header = _sniff_delimiter(p)

    if has_header:
        df = pd.read_csv(p, sep=sep, low_memory=False)
        col_lower = {str(c).strip().lower().replace("-", "_") for c in df.columns}
        if col_lower & {"merchant_name", "amount", "transaction_date", "merchant", "amt", "date"}:
            return df

    # Headerless: skip metadata row, assign standard columns
    df = pd.read_csv(p, sep=sep, skiprows=1, header=None, low_memory=False)
    if len(df.columns) >= 4:
        df.columns = TRANSACTION_COLUMNS[: len(df.columns)]
        return df

    return pd.read_csv(p, low_memory=False)


def _combine_tran_files(file_paths: list[str], output_dir: Path) -> Path | None:
    """Combine multiple transaction files into a single CSV for the pipeline.

    Reads all .txt/.csv files, concatenates them, and writes a combined file.
    Returns the path to the combined file, or None if no files found.
    If only one file, returns it directly (no combine needed).
    Skips re-combining if output already exists and source files haven't changed.
    """
    if not file_paths:
        return None

    paths = [Path(p) for p in file_paths if Path(p).exists()]
    if not paths:
        return None

    if len(paths) == 1:
        return paths[0]

    from loguru import logger as _log

    # Check if combined file already exists and is newer than all source files
    out_path = output_dir / f"_combined_transactions_{len(paths)}files.csv"
    if out_path.exists():
        out_mtime = out_path.stat().st_mtime
        sources_unchanged = all(p.stat().st_mtime <= out_mtime for p in paths)
        if sources_unchanged:
            _log.info(
                "Using cached combined file: {} ({:,} bytes)",
                out_path.name,
                out_path.stat().st_size,
            )
            return out_path

    _log.info("Combining {} transaction files into one", len(paths))
    frames = []
    for p in sorted(paths):
        try:
            df = _read_tran_file(p)
            frames.append(df)
            _log.info("  Loaded {}: {:,} rows, {} cols", p.name, len(df), len(df.columns))
        except Exception as exc:
            _log.warning("  Skipping {}: {}", p.name, exc)

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    _log.info("Combined: {:,} total rows from {} files", len(combined), len(frames))

    output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)
    return out_path


# ---------------------------------------------------------------------------
# Results dashboard (reusable -- called after execution AND on page rerun)
# ---------------------------------------------------------------------------
def _render_results_dashboard() -> None:
    """Render the post-run results dashboard from session state."""
    all_results = st.session_state.get("uap_last_results", {})
    pipeline_errors = st.session_state.get("uap_last_errors", {})
    all_output_dirs = st.session_state.get("uap_last_output_dirs", {})
    run_id = st.session_state.get("uap_last_run_id", "")
    total_elapsed = st.session_state.get("uap_last_elapsed", 0)
    _client_label = st.session_state.get("uap_last_client", "")

    if not all_results and not pipeline_errors:
        return

    st.divider()
    st.markdown('<p class="uap-label">LAST RUN RESULTS</p>', unsafe_allow_html=True)
    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)

    _total_results = sum(len(r) for r in all_results.values())
    _ok_count = len(all_results)
    _fail_count = len(pipeline_errors)

    # Result KPI cards
    _result_cols = st.columns(4)
    with _result_cols[0]:
        _color = "#16A34A" if _fail_count == 0 else "#F59E0B"
        st.markdown(
            f'<div class="uap-result-card">'
            f'<div class="rc-num" style="color:{_color};">{_total_results}</div>'
            f'<div class="rc-label">Analyses Generated</div></div>',
            unsafe_allow_html=True,
        )
    with _result_cols[1]:
        st.markdown(
            f'<div class="uap-result-card">'
            f'<div class="rc-num" style="color:#1E293B;">{_ok_count}</div>'
            f'<div class="rc-label">Pipelines Complete</div></div>',
            unsafe_allow_html=True,
        )
    with _result_cols[2]:
        _fc = "#DC2626" if _fail_count else "#16A34A"
        st.markdown(
            f'<div class="uap-result-card">'
            f'<div class="rc-num" style="color:{_fc};">{_fail_count}</div>'
            f'<div class="rc-label">Errors</div></div>',
            unsafe_allow_html=True,
        )
    with _result_cols[3]:
        st.markdown(
            f'<div class="uap-result-card">'
            f'<div class="rc-num" style="color:#1E293B;">{total_elapsed}s</div>'
            f'<div class="rc-label">Total Runtime</div></div>',
            unsafe_allow_html=True,
        )

    # Status message
    if _fail_count == 0:
        st.success(
            f"**{_client_label}** -- {_total_results} analyses across "
            f"{_ok_count} pipeline{'s' if _ok_count > 1 else ''} in {total_elapsed}s"
        )
    else:
        st.warning(
            f"**{_client_label}** -- {_ok_count} passed, {_fail_count} failed in {total_elapsed}s"
        )

    # Error details
    if pipeline_errors:
        with st.expander("Error Details", expanded=True):
            for name, tb in pipeline_errors.items():
                st.markdown(f"**{name.upper()}**")
                st.code(tb)

    # Deliverables
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
        st.markdown(
            '<p class="uap-label" style="margin-top:1rem;">DELIVERABLES</p>',
            unsafe_allow_html=True,
        )
        for f in sorted(deliverables, key=lambda p: p.name):
            _ext = f.suffix.lstrip(".")
            _icon_cls = "dl-pptx" if _ext == "pptx" else "dl-xlsx"
            _size_kb = f.stat().st_size / 1024

            dl_cols = st.columns([5, 1])
            dl_cols[0].markdown(
                f'<div class="uap-dl-card">'
                f'<div class="uap-dl-icon {_icon_cls}">{_ext.upper()}</div>'
                f'<div class="uap-dl-info">'
                f'<div class="dl-name">{f.name}</div>'
                f'<div class="dl-path">{f.parent} -- {_size_kb:.0f} KB</div>'
                f"</div></div>",
                unsafe_allow_html=True,
            )
            dl_cols[1].download_button(
                "Download",
                f.read_bytes(),
                file_name=f.name,
                mime=_MIME.get(f.suffix, "application/octet-stream"),
                key=f"home_dl_{f.parent.name}_{f.name}",
            )


# ---------------------------------------------------------------------------
# Cached helpers -- avoid re-reading Excel / disk on every rerun
# ---------------------------------------------------------------------------
def _cached_detect_and_check(client_dir: Path, client_id: str) -> dict:
    """Detect files + format checks, cached in session_state by client path.

    Returns dict with keys: detected, ars_formatted, ics_ready.
    Only re-runs when the client directory changes.
    """
    cache_key = f"{client_dir}|{client_id}"
    cached = st.session_state.get("_detect_cache")
    if cached and cached.get("_key") == cache_key:
        return cached

    detected = auto_detect_files(client_dir, client_id=client_id)

    oddd_file = detected.get("oddd")
    oddd_path = str(oddd_file) if oddd_file and oddd_file.exists() else ""

    ars_formatted = False
    ics_ready = False

    if oddd_path:
        try:
            ars_status = check_odd_formatted(oddd_path)
            ars_formatted = ars_status.is_formatted
        except Exception:
            pass
        try:
            ics_status = check_ics_ready(oddd_path)
            ics_ready = ics_status.is_formatted
        except Exception:
            pass

    # ICS fallback: if ODD has ICS columns but no separate ICS file, use ODD
    if ics_ready and not detected.get("ics") and detected.get("oddd"):
        detected["ics"] = detected["oddd"]

    result = {
        "_key": cache_key,
        "detected": detected,
        "oddd_path": oddd_path,
        "ars_formatted": ars_formatted,
        "ics_ready": ics_ready,
    }
    st.session_state["_detect_cache"] = result
    return result


@st.cache_resource(show_spinner=False)
def _cached_config_path() -> Path | None:
    """Resolve master config path once per session."""
    return resolve_master_config_path()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">RPE ANALYSIS PLATFORM</p>', unsafe_allow_html=True)
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
@st.cache_data(ttl=60, show_spinner=False)
def _cached_csm_folders(root: str) -> list[str]:
    return discover_csm_folders(Path(root))


csm_folders = _cached_csm_folders(str(data_root))
if not csm_folders:
    st.warning(f"No CSM folders found in `{data_root}`")
    st.stop()

col_csm, col_month, col_client = st.columns([2, 1, 1])

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


@st.cache_data(ttl=60, show_spinner=False)
def _cached_months(csm_path: str) -> list[str]:
    return discover_months(Path(csm_path))


months = _cached_months(str(csm_dir))

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


@st.cache_data(ttl=60, show_spinner=False)
def _cached_clients(month_path: str) -> list[str]:
    return discover_clients(Path(month_path))


clients = _cached_clients(str(month_dir))

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
# Auto-detect files (cached -- only re-reads when client changes)
# ---------------------------------------------------------------------------
client_dir = month_dir / client_id
if not client_dir.is_dir():
    st.warning(f"Client directory not found: `{client_dir}`")
    st.stop()

_cache = _cached_detect_and_check(client_dir, client_id)
detected = _cache["detected"]
oddd_path = _cache["oddd_path"]
ars_formatted = _cache["ars_formatted"]
ics_ready = _cache["ics_ready"]

# Auto-populate client name from ODD filename (e.g. "1759_Connex CU_2026.02.xlsx")
_auto_name = ""
oddd_detected = detected.get("oddd")
if oddd_detected:
    _stem = oddd_detected.stem.replace("-formatted", "")
    _parts = _stem.split("_", maxsplit=2)
    if len(_parts) > 1:
        _auto_name = _parts[1]
if not _auto_name:
    try:
        _cfg_path = _cached_config_path()
        if _cfg_path:
            from ics_toolkit.client_registry import load_master_config

            _reg = load_master_config(_cfg_path)
            _entry = _reg.get(client_id)
            if _entry and _entry.client_name:
                _auto_name = _entry.client_name
    except Exception:
        pass

client_name = _auto_name or client_id
st.session_state["uap_client_name"] = client_name

# ---------------------------------------------------------------------------
# Store detected file paths in session
# ---------------------------------------------------------------------------
for key in ("oddd", "tran", "ics"):
    path = detected.get(key)
    if path and path.exists():
        st.session_state[f"uap_file_{key}"] = str(path)
    elif f"uap_file_{key}" in st.session_state:
        del st.session_state[f"uap_file_{key}"]

# Store all transaction file paths for multi-file combine
_tran_files: list[Path] = detected.get("tran_files", [])
if _tran_files:
    st.session_state["uap_tran_files"] = [str(p) for p in _tran_files]
else:
    st.session_state.pop("uap_tran_files", None)

# Show resolved client name
if _auto_name:
    st.caption(f"**{client_id}** -- {_auto_name}")

# ---------------------------------------------------------------------------
# File status badges (compact single row)
# ---------------------------------------------------------------------------
file_checks = [
    ("oddd", "ODD File"),
    ("tran", "Transaction"),
    ("ics", "ICS Data"),
]

badge_html_parts = []
for key, label in file_checks:
    path = detected.get(key)
    if key == "tran" and _tran_files:
        cls = "uap-badge-ready"
        txt = f"{len(_tran_files)} files"
    elif path and path.exists():
        cls = "uap-badge-ready"
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

# Add format badges inline
if oddd_path:
    if ars_formatted:
        badge_html_parts.append(
            '<span class="uap-badge uap-badge-ready" style="margin-right:4px;">FORMATTED</span>'
        )
    else:
        badge_html_parts.append(
            '<span class="uap-badge" style="background:#FEE2E2;color:#991B1B;margin-right:4px;">UNFORMATTED</span>'
        )
    if ics_ready:
        badge_html_parts.append(
            '<span class="uap-badge uap-badge-ready" style="margin-right:4px;">ICS READY</span>'
        )

st.markdown(
    f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;padding:0.4rem 0;">{"".join(badge_html_parts)}</div>',
    unsafe_allow_html=True,
)

# Offer inline format if unformatted
if oddd_path and not ars_formatted:
    if st.button("Format ODD Now", type="secondary", key="home_format_btn"):
        with st.spinner("Formatting..."), warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
            df = pd.read_excel(oddd_path)
            df = format_odd(df)
            p = Path(oddd_path)
            out = p.parent / f"{p.stem}-formatted.xlsx"
            df.to_excel(out, index=False, engine="openpyxl")
            st.session_state["uap_file_oddd"] = str(out)
            # Invalidate cache so next rerun picks up the formatted file
            st.session_state.pop("_detect_cache", None)
        st.success(f"Saved: `{out.name}`")
        st.rerun()

st.divider()

# =========================================================================
# STEP 2 -- Pick pipelines
# =========================================================================
st.markdown('<p class="uap-label">STEP 2 / SELECT PIPELINES</p>', unsafe_allow_html=True)
st.caption("Toggle which pipelines to run. Multiple can be active at once.")


@st.cache_data(show_spinner=False)
def _cached_templates():
    return load_templates()


templates = _cached_templates()
registry = get_registry()
module_map = {m.key: m for m in registry}

# Determine which products have data available
_product_available = {
    Product.ARS: bool(detected.get("oddd")),
    Product.TXN: bool(detected.get("tran") or detected.get("tran_files")),
    Product.ICS: bool(detected.get("ics") or ics_ready),
}

# Map each pipeline to its full suite template
_PIPELINE_TEMPLATE: dict[Product, str] = {
    Product.ARS: "ARS Full Suite",
    Product.ICS: "ICS Full Suite",
    Product.TXN: "TXN Full Suite",
}
_PIPELINE_LABELS: dict[Product, tuple[str, str, str]] = {
    Product.ARS: ("ARS", "OD/NSF account analysis, DCTR, mailers, Reg E", ":material/analytics:"),
    Product.ICS: (
        "ICS",
        "ICS account analysis, referral sources, activity",
        ":material/account_tree:",
    ),
    Product.TXN: ("TXN", "Transaction intelligence, competitors, MCC", ":material/credit_card:"),
}

# Initialize active pipelines from session state
_active_pipelines: set[Product] = st.session_state.get("uap_active_pipelines", set())

# Pipeline toggle buttons -- one per pipeline type
_pip_cols = st.columns(3)
for col, product in zip(_pip_cols, [Product.ARS, Product.ICS, Product.TXN]):
    label, desc, icon = _PIPELINE_LABELS[product]
    is_available = _product_available.get(product, False)
    is_active = product in _active_pipelines

    with col:
        if is_active:
            btn_type = "primary"
            status_icon = "ON"
        else:
            btn_type = "secondary"
            status_icon = "OFF" if is_available else "--"

        if st.button(
            f"{label}  {status_icon}",
            key=f"home_pip_{product.value}",
            width="stretch",
            type=btn_type,
            disabled=not is_available,
            help=desc if is_available else f"No {label} data file detected",
        ):
            if product in _active_pipelines:
                _active_pipelines.discard(product)
            else:
                _active_pipelines.add(product)
            st.session_state["uap_active_pipelines"] = _active_pipelines

            # Build combined module set from all active pipelines
            combined_modules: set[str] = set()
            for p in _active_pipelines:
                tpl_name = _PIPELINE_TEMPLATE.get(p, "")
                if tpl_name and tpl_name in templates:
                    combined_modules.update(templates[tpl_name])
            st.session_state["uap_selected_modules"] = combined_modules
            active_names = " + ".join(
                _PIPELINE_LABELS[p][0] for p in sorted(_active_pipelines, key=lambda x: x.value)
            )
            st.session_state["uap_selected_template"] = active_names or ""
            st.rerun()

selected_modules = st.session_state.get("uap_selected_modules", set())
selected_template = st.session_state.get("uap_selected_template", "")

if selected_modules:
    _n_pipelines = len(_active_pipelines)
    st.caption(
        f"**{selected_template}** -- {len(selected_modules)} modules across "
        f"{_n_pipelines} pipeline{'s' if _n_pipelines > 1 else ''}"
    )

# ---------------------------------------------------------------------------
# Module detail (collapsed by default -- for power users)
# ---------------------------------------------------------------------------
_modules_by_product: dict[Product, list] = {}
for m in registry:
    _modules_by_product.setdefault(m.product, []).append(m)

if selected_modules:
    with st.expander("Module Detail", expanded=False):
        for product in sorted(_active_pipelines, key=lambda x: x.value):
            modules = _modules_by_product.get(product, [])
            _by_cat: dict[str, list] = {}
            for m in sorted(modules, key=lambda x: x.run_order):
                _by_cat.setdefault(m.category, []).append(m)

            _n_selected = sum(1 for m in modules if m.key in selected_modules)
            st.markdown(f"**{product.value.upper()}** -- {_n_selected}/{len(modules)} modules")
            _lines: list[str] = ['<div style="column-count:2;column-gap:2rem;">']
            for cat_name, cat_modules in _by_cat.items():
                _lines.append(
                    f'<div style="break-inside:avoid;margin-bottom:0.5rem;">'
                    f'<div style="margin-bottom:0.1rem;">'
                    f'<b style="color:#475569;font-size:0.82rem;text-transform:uppercase;'
                    f'letter-spacing:0.03em;">{cat_name}</b></div>'
                )
                for m in cat_modules:
                    is_selected = m.key in selected_modules
                    if is_selected:
                        _lines.append(
                            f'<div style="padding:2px 0 2px 10px;border-left:3px solid #16A34A;">'
                            f'<b style="color:#1E293B;">{m.name}</b> '
                            f'<span style="color:#64748B;font-size:0.78rem;">{m.description}</span></div>'
                        )
                    else:
                        _lines.append(
                            f'<div style="padding:2px 0 2px 10px;border-left:3px solid transparent;">'
                            f'<span style="color:#CBD5E1;">{m.name}</span></div>'
                        )
                _lines.append("</div>")
            _lines.append("</div>")
            st.markdown("".join(_lines), unsafe_allow_html=True)

if not selected_modules:
    st.info("Select one or more pipelines above to continue.")
    st.stop()

st.divider()

# =========================================================================
# STEP 3 -- Run (Executive Analytics Dashboard)
# =========================================================================
st.markdown('<p class="uap-label">STEP 3 / RUN</p>', unsafe_allow_html=True)

# Resolve config (cached)
_config_path = _cached_config_path()
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
    _tran_file_list = st.session_state.get("uap_tran_files", [])
    if not tran_path and not _tran_file_list:
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

# ---------------------------------------------------------------------------
# Run Summary -- clean card with key config visible
# ---------------------------------------------------------------------------
_raw_entry: dict = {}
if _config_path:
    _raw_entry = load_raw_client_entry(_config_path, client_id)

_pipelines_str = " + ".join(p.value.upper() for p in sorted(needed_products, key=lambda x: x.value))
_ic = _raw_entry.get("ICRate", "--")
_fee = _raw_entry.get("NSF_OD_Fee", "--")

# Key metrics row
_metric_cols = st.columns(4)
_metric_cols[0].metric("Client", client_id)
_metric_cols[1].metric("Pipelines", _pipelines_str)
_metric_cols[2].metric("IC Rate", str(_ic))
_metric_cols[3].metric("NSF/OD Fee", f"${_fee}")

# Eligible config -- always visible
if _raw_entry:
    _cfg_html = '<div class="uap-cfg-grid">'

    # Eligible Status Codes
    _esc = _raw_entry.get("EligibleStatusCodes", [])
    _esc_pills = " ".join(
        f'<span class="uap-pill uap-pill-green">{c}</span>'
        for c in (_esc if isinstance(_esc, list) else [_esc] if _esc else [])
    )
    _cfg_html += f'<div class="uap-cfg-item"><div class="cfg-label">Eligible Status</div><div>{_esc_pills or "--"}</div></div>'

    # Eligible Product Codes
    _epc = _raw_entry.get("EligibleProductCodes", [])
    _epc_pills = " ".join(
        f'<span class="uap-pill uap-pill-green">{c}</span>'
        for c in (_epc if isinstance(_epc, list) else [_epc] if _epc else [])
    )
    _cfg_html += f'<div class="uap-cfg-item" style="grid-column:span 2;"><div class="cfg-label">Eligible Products</div><div>{_epc_pills or "--"}</div></div>'

    # Mail Code
    _mc = _raw_entry.get("EligibleMailCode", "--")
    _cfg_html += f'<div class="uap-cfg-item"><div class="cfg-label">Mail Code</div><div class="cfg-val">{_mc}</div></div>'

    _cfg_html += "</div>"
    st.markdown(_cfg_html, unsafe_allow_html=True)

    # Extended config -- expandable
    _has_extra = (
        _raw_entry.get("IneligibleStatusCodes")
        or _raw_entry.get("IneligibleProductCodes")
        or _raw_entry.get("RegEOptInCode")
        or _raw_entry.get("BranchMapping")
    )
    if _has_extra:
        with st.expander("Extended Configuration", expanded=False):
            _ext_html = '<div class="uap-cfg-grid">'

            _isc = _raw_entry.get("IneligibleStatusCodes", [])
            if _isc:
                _isc_pills = " ".join(
                    f'<span class="uap-pill uap-pill-red">{c}</span>'
                    for c in (_isc if isinstance(_isc, list) else [_isc])
                )
                _ext_html += f'<div class="uap-cfg-item"><div class="cfg-label">Ineligible Status</div><div>{_isc_pills}</div></div>'

            _ipc = _raw_entry.get("IneligibleProductCodes", [])
            if _ipc:
                _ipc_pills = " ".join(
                    f'<span class="uap-pill uap-pill-red">{c}</span>'
                    for c in (_ipc if isinstance(_ipc, list) else [_ipc])
                )
                _ext_html += f'<div class="uap-cfg-item"><div class="cfg-label">Ineligible Products</div><div>{_ipc_pills}</div></div>'

            _re = _raw_entry.get("RegEOptInCode", [])
            if _re:
                _re_pills = " ".join(
                    f'<span class="uap-pill uap-pill-blue">{c}</span>'
                    for c in (_re if isinstance(_re, list) else [_re])
                )
                _ext_html += f'<div class="uap-cfg-item"><div class="cfg-label">Reg E Opt-In</div><div>{_re_pills}</div></div>'

            _branches = _raw_entry.get("BranchMapping", {})
            if _branches:
                _br_pills = " ".join(
                    f'<span class="uap-pill">{k}={v}</span>' for k, v in _branches.items()
                )
                _ext_html += f'<div class="uap-cfg-item" style="grid-column:span 2;"><div class="cfg-label">Branch Mapping</div><div>{_br_pills}</div></div>'

            _ext_html += "</div>"
            st.markdown(_ext_html, unsafe_allow_html=True)

    if _config_path:
        st.caption(f"Config: {_config_path}")
else:
    st.warning(f"Client {client_id} not found in config. Analysis will use defaults.")

# ---------------------------------------------------------------------------
# Run button -- NO form (avoids Streamlit's blue progress bar)
# ---------------------------------------------------------------------------
_is_running = st.session_state.get("uap_running", False)


def _on_run_click() -> None:
    """Callback fires BEFORE the page reruns -- disables button immediately."""
    st.session_state["uap_running"] = True


st.markdown('<div class="uap-run-btn">', unsafe_allow_html=True)
run_btn = st.button(
    "Running..." if _is_running else f"Run {len(selected_modules)} Modules",
    type="primary",
    width="stretch",
    key="home_run_btn",
    disabled=_is_running,
    on_click=_on_run_click,
)
st.markdown("</div>", unsafe_allow_html=True)

if not run_btn and not _is_running:
    _render_results_dashboard()
    st.stop()

# ---------------------------------------------------------------------------
# Execution -- full analytics dashboard
# ---------------------------------------------------------------------------

run_id = generate_run_id()
all_results: dict[str, dict] = {}
all_output_dirs: dict[str, Path] = {}
pipeline_errors: dict[str, str] = {}

tran_path = st.session_state.get("uap_file_tran", "")
_all_tran_paths = st.session_state.get("uap_tran_files", [])
ics_path = st.session_state.get("uap_file_ics", "")
odd_path = st.session_state.get("uap_file_odd", "")
t0 = time.time()
total_pipelines = len(needed_products)

_pipelines_label = " + ".join(
    p.value.upper() for p in sorted(needed_products, key=lambda x: x.value)
)

# ---- Single progress tracker: one st.status() per phase ----

# PHASE 1: Data preparation
_data_status = st.status(
    f"Step 1 of {total_pipelines + 1} -- Loading data files...", expanded=True
)
_data_status.write(f"Client **{client_id}** -- {_pipelines_label}")

_local_oddd: str = oddd_path
_local_dir = Path(tempfile.mkdtemp(prefix="uap_run_"))
_needs_odd = Product.ARS in needed_products or Product.ICS in needed_products

if _needs_odd and oddd_path and Path(oddd_path).exists():
    _data_status.write("Reading ODD Excel from network drive...")
    logger.info("Loading ODD Excel: %s", oddd_path)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        _oddd_df = pd.read_excel(oddd_path)
    _local_csv = _local_dir / (Path(oddd_path).stem + ".csv")
    _oddd_df.to_csv(_local_csv, index=False)
    _local_oddd = str(_local_csv)
    _data_status.write(f"ODD loaded: {len(_oddd_df):,} accounts")
    logger.info("ODD loaded: %d rows", len(_oddd_df))
    del _oddd_df

_effective_tran: Path | None = None
if Product.TXN in needed_products:
    n_tran = len(_all_tran_paths)
    _data_status.write(f"Reading {n_tran} transaction file{'s' if n_tran != 1 else ''}...")
    logger.info("Combining %d transaction files", n_tran)
    _effective_tran = _combine_tran_files(
        _all_tran_paths, Path(oddd_path).parent if oddd_path else Path(".")
    )
    if not _effective_tran and tran_path:
        _effective_tran = Path(tran_path)
    if _effective_tran:
        _data_status.write(f"Transaction data ready: {_effective_tran.name}")

_data_elapsed = round(time.time() - t0, 1)
_data_status.update(
    label=f"Step 1 of {total_pipelines + 1} -- Data loaded ({_data_elapsed}s)",
    state="complete",
    expanded=False,
)

# PHASE 2+: Pipeline execution -- one st.status() per pipeline
_pipeline_statuses: list = []
for product in sorted(needed_products, key=lambda p: p.value):
    _pipeline_statuses.append(
        st.status(
            f"Step {len(_pipeline_statuses) + 2} of {total_pipelines + 1} "
            f"-- {product.value.upper()} pipeline queued",
            expanded=False,
        )
    )

for idx, product in enumerate(sorted(needed_products, key=lambda p: p.value)):
    pipeline_name = product.value
    _ps = _pipeline_statuses[idx]
    _step_num = idx + 2
    _ps.update(
        label=f"Step {_step_num} of {total_pipelines + 1} "
        f"-- Running {pipeline_name.upper()} pipeline...",
        state="running",
        expanded=True,
    )

    input_files: dict[str, Path] = {}
    if product == Product.ARS:
        input_files["oddd"] = Path(_local_oddd)
        out = Path(oddd_path).parent / "output"
    elif product == Product.TXN:
        if _effective_tran:
            input_files["tran"] = _effective_tran
        if odd_path and Path(odd_path).exists():
            input_files["odd"] = Path(odd_path)
        out = (_effective_tran.parent if _effective_tran else Path(".")) / "output_txn"
    elif product == Product.ICS:
        input_files["ics"] = Path(ics_path) if ics_path else Path(_local_oddd)
        out = Path(oddd_path).parent / "output_ics"
    else:
        continue

    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _err_msg = (
            f"Cannot create output directory: {out}\n\n"
            f"If this is a network path (M: drive), check that the drive is connected.\n\n"
            f"{type(exc).__name__}: {exc}"
        )
        pipeline_errors[pipeline_name] = _err_msg
        logger.error("Output dir creation failed for %s: %s", pipeline_name, exc)
        _ps.update(
            label=f"Step {_step_num} of {total_pipelines + 1} "
            f"-- {pipeline_name.upper()} FAILED (output dir)",
            state="error", expanded=True,
        )
        _ps.write(f"ERROR: {_err_msg}")
        continue

    _module_count = 0

    def _on_progress(
        msg: str,
        _status=_ps,
        _pipe=pipeline_name,
    ) -> None:
        _short = _make_status_line(msg, _pipe)
        _status.write(_short)

    _product_keys = [
        k for k in selected_modules if module_map.get(k) and module_map[k].product == product
    ]
    _pipeline_config = {**_client_config}
    if _product_keys:
        _pipeline_config["module_ids"] = _product_keys

    _ps.write(f"Running {len(_product_keys)} modules...")

    step_t0 = time.time()
    try:
        results = run_pipeline(
            pipeline_name,
            input_files=input_files,
            output_dir=out,
            client_id=client_id,
            client_name=client_name,
            client_config=_pipeline_config,
            progress_callback=_on_progress,
        )
        all_results[pipeline_name] = results
        all_output_dirs[pipeline_name] = out
        _step_elapsed = round(time.time() - step_t0, 1)
        _ps.update(
            label=f"Step {_step_num} of {total_pipelines + 1} "
            f"-- {pipeline_name.upper()} complete "
            f"({len(results)} results, {_step_elapsed}s)",
            state="complete", expanded=False,
        )
        logger.info("Pipeline %s complete: %d results in %.1fs", pipeline_name, len(results), _step_elapsed)
    except Exception:
        import traceback as _tb

        _step_elapsed = round(time.time() - step_t0, 1)
        _tb_str = _tb.format_exc()
        pipeline_errors[pipeline_name] = _tb_str
        _ps.update(
            label=f"Step {_step_num} of {total_pipelines + 1} "
            f"-- {pipeline_name.upper()} FAILED ({_step_elapsed}s)",
            state="error", expanded=True,
        )
        _ps.code(_tb_str[-500:], language="python")
        logger.error("Pipeline %s failed for client %s:\n%s", pipeline_name, client_id, _tb_str)

total_elapsed = round(time.time() - t0, 1)

# Re-enable the run button
st.session_state["uap_running"] = False

# Clean up local copy
shutil.rmtree(_local_dir, ignore_errors=True)

# Final summary line
_ok = len(all_results)
_fail = len(pipeline_errors)
if _fail:
    st.warning(f"Completed in {total_elapsed}s -- {_ok} pipeline(s) OK, {_fail} failed. Check errors above.")
else:
    st.success(f"All {_ok} pipeline(s) complete in {total_elapsed}s.")

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
st.session_state["uap_last_elapsed"] = total_elapsed
st.session_state["uap_last_client"] = client_name or client_id

# ---------------------------------------------------------------------------
# Results Dashboard (KPI cards + deliverables from session state)
# ---------------------------------------------------------------------------
_render_results_dashboard()

# ---------------------------------------------------------------------------
# Run report (slide-level diagnostics from JSON)
# ---------------------------------------------------------------------------
_run_reports: list[dict] = []
_seen_reports: set[str] = set()
for out_dir in all_output_dirs.values():
    if out_dir and Path(out_dir).is_dir():
        for rpt_path in Path(out_dir).rglob("*_run_report.json"):
            # Deduplicate by resolved path (avoids showing old + new from same dir)
            _rpt_key = str(rpt_path.resolve())
            if _rpt_key in _seen_reports:
                continue
            _seen_reports.add(_rpt_key)
            try:
                _run_reports.append(_json.loads(rpt_path.read_text()))
            except Exception:
                pass

if _run_reports:
    with st.expander("Slide Diagnostics", expanded=bool(pipeline_errors)):
        for rpt in _run_reports:
            _s = rpt.get("summary", {})
            _total = _s.get("total", 0)
            _ok = _s.get("ok", 0)
            _failed = _s.get("failed", 0)
            _no_chart = _s.get("no_chart", 0)

            # Compact summary badges
            _fail_badge = (
                f'<span class="uap-badge uap-badge-error">{_failed} FAIL</span> ' if _failed else ""
            )
            _nochart_badge = (
                f'<span class="uap-badge uap-badge-muted">{_no_chart} NO CHART</span>'
                if _no_chart
                else ""
            )
            st.markdown(
                f'<div style="margin-bottom:0.5rem;">'
                f'<span style="font-weight:600;">{rpt.get("client_id", "")} {rpt.get("month", "")}</span> '
                f'<span class="uap-badge uap-badge-ready">{_ok} OK</span> '
                f"{_fail_badge}{_nochart_badge}"
                f"</div>",
                unsafe_allow_html=True,
            )

            slides = rpt.get("slides", [])
            if slides:
                import pandas as _pd

                _df = _pd.DataFrame(slides)
                _df["status"] = _df.apply(
                    lambda r: (
                        "OK"
                        if r["success"] and r["has_chart"]
                        else ("FAIL" if not r["success"] else "NO CHART")
                    ),
                    axis=1,
                )

                # Group by module for cleaner display
                if "module_id" in _df.columns:
                    _df["module"] = (
                        _df["module_id"].str.split(".").str[0].str.upper().replace("", "—")
                    )
                    _df = _df.sort_values("slide_id")
                else:
                    _df["module"] = "—"

                _display_cols = [
                    "module",
                    "slide_id",
                    "status",
                    "title",
                    "has_chart",
                    "has_excel",
                    "error",
                ]
                _display_cols = [c for c in _display_cols if c in _df.columns]

                # Color-code status
                def _style_status(val: str) -> str:
                    if val == "OK":
                        return "color: #16A34A; font-weight: 600"
                    if val == "FAIL":
                        return "color: #DC2626; font-weight: 600"
                    return "color: #94A3B8"

                _styled = _df[_display_cols].style.map(_style_status, subset=["status"])
                st.dataframe(
                    _styled,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "module": st.column_config.TextColumn("Module", width="small"),
                        "status": st.column_config.TextColumn("Status", width="small"),
                        "slide_id": st.column_config.TextColumn("Slide", width="small"),
                        "title": st.column_config.TextColumn("Title", width="medium"),
                        "error": st.column_config.TextColumn("Error", width="large"),
                    },
                )
