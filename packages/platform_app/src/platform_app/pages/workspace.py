"""UAP Workspace -- CSM + month + client folder selection and file auto-detection."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from platform_app.core.session_manager import (
    auto_detect_files,
    discover_clients,
    discover_csm_folders,
    discover_months,
    resolve_workspace,
)
from shared.format_odd import check_ics_ready, check_odd_formatted

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">DATA / WORKSPACE</p>', unsafe_allow_html=True)
st.title("Workspace")
st.caption("Select your CSM folder, review month, and client to auto-detect data files.")

# ---------------------------------------------------------------------------
# Data root configuration
# ---------------------------------------------------------------------------
data_root_str = st.text_input(
    "Data root directory",
    value=st.session_state.get("uap_data_root", ""),
    placeholder=r"M:\ARS\Incoming\ODDD Files",
    help="Root directory containing CSM folders (e.g. M:\\ARS\\Incoming\\ODDD Files).",
)

if not data_root_str.strip():
    st.info("Enter the path to your data root directory to browse CSM folders.")
    st.stop()

data_root = Path(data_root_str.strip())
if not data_root.is_dir():
    st.error(f"Directory not found: `{data_root}`")
    st.stop()

st.session_state["uap_data_root"] = data_root_str.strip()

# ---------------------------------------------------------------------------
# CSM selection
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">CSM FOLDER</p>', unsafe_allow_html=True)

csm_folders = discover_csm_folders(data_root)
if not csm_folders:
    st.warning(f"No CSM folders found in `{data_root}`")
    st.stop()

csm = st.selectbox(
    "Select CSM",
    options=csm_folders,
    index=csm_folders.index(st.session_state.get("uap_csm", csm_folders[0]))
    if st.session_state.get("uap_csm") in csm_folders
    else 0,
)
st.session_state["uap_csm"] = csm

# ---------------------------------------------------------------------------
# Month selection
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">REVIEW MONTH</p>', unsafe_allow_html=True)

csm_dir = data_root / csm
months = discover_months(csm_dir)

if not months:
    st.warning(f"No month folders (YYYY.MM) found in `{csm_dir}`")
    st.stop()

month = st.selectbox(
    "Select month",
    options=months,
    index=months.index(st.session_state.get("uap_month", months[0]))
    if st.session_state.get("uap_month") in months
    else 0,
    help="Month folders are sorted newest first.",
)
st.session_state["uap_month"] = month

# ---------------------------------------------------------------------------
# Client selection
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">CLIENT</p>', unsafe_allow_html=True)

month_dir = csm_dir / month
clients = discover_clients(month_dir)

if not clients:
    st.warning(f"No client folders in `{month_dir}`")
    st.stop()

c1, c2 = st.columns([2, 1])
with c1:
    client_id = st.selectbox(
        "Client folder",
        options=clients,
        index=clients.index(st.session_state.get("uap_client_id", clients[0]))
        if st.session_state.get("uap_client_id") in clients
        else 0,
    )
with c2:
    client_name = st.text_input(
        "Client name",
        value=st.session_state.get("uap_client_name", ""),
        placeholder="e.g. Connex CU",
    )

st.session_state["uap_client_id"] = client_id
st.session_state["uap_client_name"] = client_name

# ---------------------------------------------------------------------------
# Auto-detect files
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">DETECTED FILES</p>', unsafe_allow_html=True)

client_dir = month_dir / client_id
if not client_dir.is_dir():
    st.warning(f"Client directory not found: `{client_dir}`")
    st.stop()

detected = auto_detect_files(client_dir, client_id=client_id)

# Display detected files as status indicators
file_types = [
    ("oddd", "ODDD (.xlsx)", "ARS Analysis"),
    ("tran", "Transaction (.csv)", "TXN Analysis"),
    ("ics", "ICS Data (.xlsx)", "ICS Analysis"),
    ("config", "Config (.json/.yaml)", "Client Config"),
]

cols = st.columns(4)
for col, (key, label, pipeline) in zip(cols, file_types):
    path = detected.get(key)
    with col:
        if path and path.exists():
            badge = '<span class="uap-badge uap-badge-ready">FOUND</span>'
            file_info = f'<span style="font-family: var(--uap-mono); font-size: 0.72rem; color: #475569;">{path.name}</span>'
        else:
            badge = '<span class="uap-badge uap-badge-muted">MISSING</span>'
            file_info = '<span style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8;">not detected</span>'

        # Extra validation badges for ODDD files
        extra_badges = ""
        if key == "oddd" and path and path.exists():
            try:
                ars_status = check_odd_formatted(path)
                st.session_state["_oddd_ars_status"] = ars_status
                if ars_status.is_formatted:
                    extra_badges += '<br><span class="uap-badge uap-badge-ready" style="font-size:0.6rem;">FORMATTED</span>'
                else:
                    extra_badges += '<br><span class="uap-badge" style="background:#FEE2E2;color:#991B1B;font-size:0.6rem;">UNFORMATTED</span>'
            except Exception:
                extra_badges += '<br><span class="uap-badge uap-badge-muted" style="font-size:0.6rem;">CHECK FAILED</span>'

            try:
                ics_status = check_ics_ready(path)
                st.session_state["_oddd_ics_status"] = ics_status
                if ics_status.is_formatted:
                    extra_badges += ' <span class="uap-badge uap-badge-ready" style="font-size:0.6rem;">ICS READY</span>'
                else:
                    extra_badges += ' <span class="uap-badge" style="background:#FEF3C7;color:#92400E;font-size:0.6rem;">ICS FIELDS MISSING</span>'
            except Exception:
                pass

        st.markdown(
            f"""<div class="uap-card" style="padding: 0.75rem;">
            <p style="font-family: var(--uap-mono); font-size: 0.65rem; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.35rem;">{label}</p>
            {badge}{extra_badges}<br>
            {file_info}
            <p style="font-size: 0.72rem; color: #94A3B8; margin-top: 0.25rem;">{pipeline}</p>
            </div>""",
            unsafe_allow_html=True,
        )

# Store workspace in session
ws = resolve_workspace(csm, client_id, client_name.strip(), data_root, month=month)
st.session_state["uap_workspace"] = ws

# Store detected file paths in session for downstream pages
for key, _, _ in file_types:
    path = detected.get(key)
    if path and path.exists():
        st.session_state[f"uap_file_{key}"] = str(path)

# Available pipelines
st.divider()
pipelines = ws.available_pipelines
if pipelines:
    st.success(f"Ready to run: **{', '.join(p.upper() for p in pipelines)}**")
else:
    st.warning("No data files detected. Upload files via **Data Ingestion** or check paths.")

# Manual file overrides
with st.expander("Manual file overrides", expanded=False):
    st.caption("Override auto-detected paths if needed.")
    for key, label, _ in file_types:
        path = st.text_input(
            label,
            value=str(detected[key]) if detected.get(key) else "",
            key=f"ws_override_{key}",
            placeholder="Leave empty to use auto-detected file",
        )
        if path.strip():
            st.session_state[f"uap_file_{key}"] = path.strip()
