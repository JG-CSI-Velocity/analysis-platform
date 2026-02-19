"""Client Config page -- browse and edit client configurations."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from platform_app.components import kpi_row

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path.home() / ".ars_platform"
CONFIG_PATH = _CONFIG_DIR / "clients_config.json"

_CADENCE_OPTIONS = ["monthly", "bimonthly", "quarterly", "semiannual", "annual", "ad-hoc"]

_EMPTY_CLIENT: dict = {
    "ClientID": "",
    "ClientName": "",
    "AssignedCSM": "",
    "ICRate": "0.0050",
    "NSF_OD_Fee": "30",
    "EligibleStatusCodes": ["O"],
    "IneligibleStatusCodes": ["C", "F"],
    "EligibleProductCodes": [],
    "IneligibleProductCodes": [],
    "EligibleMailCode": "Yes",
    "IneligibleMailCode": "No",
    "RegEOptInCode": ["Y"],
    "BranchMapping": {},
    "Cadence": "monthly",
}


def load_clients_config() -> dict | None:
    """Load client config dict keyed by client ID, or None if missing."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "clients" in data:
            return {c["ClientID"]: c for c in data["clients"] if "ClientID" in c}
        if isinstance(data, dict):
            return data
        return data
    except (json.JSONDecodeError, KeyError):
        return None


def save_clients_config(data: dict) -> None:
    """Save client config dict back to JSON with backup."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        shutil.copy2(CONFIG_PATH, CONFIG_PATH.with_suffix(".json.bak"))
    CONFIG_PATH.write_text(json.dumps(data, indent=4), encoding="utf-8")


def render() -> None:
    try:
        _render_inner()
    except Exception:
        st.error("Something went wrong loading client config. Please try refreshing.")
        logger.exception("Unhandled error in config_page")


def _render_inner() -> None:
    st.title("Client Configuration")
    st.caption("Manage client settings for ARS, Transaction, and ICS pipelines")

    data = load_clients_config()

    if data is None:
        _render_setup()
        return

    clients = data
    client_ids = sorted(clients.keys())

    # KPI summary
    csms = {clients[cid].get("AssignedCSM", "") for cid in client_ids} - {""}
    last_modified = "Unknown"
    if CONFIG_PATH.exists():
        mtime = CONFIG_PATH.stat().st_mtime
        last_modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    kpi_row([
        {"label": "Total Clients", "value": str(len(client_ids))},
        {"label": "CSMs", "value": str(len(csms))},
        {"label": "Last Updated", "value": last_modified},
    ])

    tab_browse, tab_edit = st.tabs(["Browse Clients", "Edit Client"])

    with tab_browse:
        _render_browse_tab(clients, client_ids, csms, data)

    with tab_edit:
        _render_edit_tab(clients, client_ids, data)


def _render_browse_tab(clients: dict, client_ids: list, csms: set, data: dict) -> None:
    col_search, col_csm_filter = st.columns([3, 2])
    with col_search:
        search = st.text_input("Search", placeholder="Client ID or name...", label_visibility="collapsed")
    with col_csm_filter:
        csm_list = ["All CSMs"] + sorted(csms)
        csm_filter = st.selectbox("Filter by CSM", csm_list, label_visibility="collapsed")

    filtered_ids = client_ids
    if search:
        search_lower = search.lower()
        filtered_ids = [
            cid for cid in filtered_ids
            if search_lower in cid.lower()
            or search_lower in clients[cid].get("ClientName", "").lower()
        ]
    if csm_filter != "All CSMs":
        filtered_ids = [cid for cid in filtered_ids if clients[cid].get("AssignedCSM", "") == csm_filter]

    if filtered_ids:
        table_data = []
        for cid in filtered_ids:
            c = clients[cid]
            table_data.append({
                "Client ID": cid,
                "Name": c.get("ClientName", ""),
                "CSM": c.get("AssignedCSM", ""),
                "IC Rate": c.get("ICRate", ""),
                "NSF/OD Fee": c.get("NSF_OD_Fee", ""),
                "Eligible Stats": ", ".join(c.get("EligibleStatusCodes", [])),
            })
        st.dataframe(table_data, use_container_width=True, hide_index=True,
                      height=min(400, 35 * len(table_data) + 38))
        st.caption(f"Showing {len(filtered_ids)} of {len(client_ids)} clients")
    else:
        st.info("No clients match your search.")

    col_add, col_export = st.columns([1, 1])
    with col_add:
        add_clicked = st.button("Add Client", type="primary", use_container_width=True)
    with col_export:
        st.download_button(
            "Export Config",
            data=json.dumps(data, indent=4),
            file_name="clients_config.json",
            mime="application/json",
            use_container_width=True,
        )

    if add_clicked:
        _render_add_client(data)


def _render_edit_tab(clients: dict, client_ids: list, data: dict) -> None:
    if not client_ids:
        st.info("No clients to edit. Add a client first.")
        return

    selected_id = st.selectbox(
        "Select client to edit",
        client_ids,
        index=None,
        placeholder="Start typing a client ID...",
        format_func=lambda cid: f"{cid} -- {clients[cid].get('ClientName', '')}",
    )

    if not selected_id:
        return

    client = clients[selected_id]

    with st.form(f"edit_{selected_id}"):
        with st.expander("Basic Info", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Client Name", value=client.get("ClientName", ""))
            with col2:
                csm = st.text_input("Assigned CSM", value=client.get("AssignedCSM", ""))
            with col3:
                cadence = st.selectbox(
                    "Cadence", _CADENCE_OPTIONS,
                    index=_CADENCE_OPTIONS.index(client.get("Cadence", "monthly")),
                )

        with st.expander("Rates", expanded=False):
            col4, col5 = st.columns(2)
            with col4:
                ic_rate = st.text_input("IC Rate", value=str(client.get("ICRate", "0.0050")))
            with col5:
                nsf_fee = st.text_input("NSF/OD Fee", value=str(client.get("NSF_OD_Fee", "30")))

        with st.expander("Eligibility", expanded=False):
            col6, col7 = st.columns(2)
            with col6:
                elig_stats = st.text_input("Eligible Stat Codes", value=", ".join(client.get("EligibleStatusCodes", [])))
                elig_prods = st.text_input("Eligible Product Codes", value=", ".join(client.get("EligibleProductCodes", [])))
            with col7:
                inelig_stats = st.text_input("Ineligible Stat Codes", value=", ".join(client.get("IneligibleStatusCodes", [])))
                inelig_prods = st.text_input("Ineligible Product Codes", value=", ".join(client.get("IneligibleProductCodes", [])))
            rege_codes = st.text_input("Reg E Opt-In Codes", value=", ".join(client.get("RegEOptInCode", [])))

        with st.expander("Branch Mapping", expanded=False):
            branch_map = client.get("BranchMapping", {})
            branch_text = "\n".join(f"{k}: {v}" for k, v in branch_map.items()) if branch_map else ""
            branches = st.text_area("Branches (one per line: code: name)", value=branch_text, height=100)

        col_save, col_delete = st.columns([3, 1])
        with col_save:
            save = st.form_submit_button("Save Changes", type="primary", use_container_width=True)
        with col_delete:
            delete = st.form_submit_button("Delete Client", use_container_width=True)

    if save:
        new_branches = {}
        for line in branches.strip().split("\n"):
            if ":" in line:
                code, bname = line.split(":", 1)
                new_branches[code.strip()] = bname.strip()

        data[selected_id] = {
            "ClientID": selected_id,
            "ClientName": name,
            "AssignedCSM": csm,
            "Cadence": cadence,
            "ICRate": ic_rate,
            "NSF_OD_Fee": nsf_fee,
            "EligibleStatusCodes": [s.strip() for s in elig_stats.split(",") if s.strip()],
            "IneligibleStatusCodes": [s.strip() for s in inelig_stats.split(",") if s.strip()],
            "EligibleProductCodes": [p.strip() for p in elig_prods.split(",") if p.strip()],
            "IneligibleProductCodes": [p.strip() for p in inelig_prods.split(",") if p.strip()],
            "RegEOptInCode": [r.strip() for r in rege_codes.split(",") if r.strip()],
            "BranchMapping": new_branches,
        }
        save_clients_config(data)
        st.success(f"Saved {selected_id} -- {name}")
        st.rerun()

    if delete:
        if selected_id in data:
            del data[selected_id]
            save_clients_config(data)
            st.success(f"Deleted {selected_id}")
            st.rerun()


def _render_setup() -> None:
    st.warning("No client configuration found.")
    st.markdown("### Get Started")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Start Empty**")
            st.caption("Creates a blank config file. Add clients one by one.")
        if st.button("Create Empty Config", type="primary", use_container_width=True):
            save_clients_config({})
            st.success("Empty config created.")
            st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("**Import Existing**")
            st.caption("Upload an existing clients_config.json file.")

    uploaded = st.file_uploader("Upload clients_config.json", type=["json"])
    if uploaded:
        try:
            imported = json.loads(uploaded.getvalue().decode("utf-8"))
            if isinstance(imported, dict):
                save_clients_config(imported)
                st.success(f"Imported {len(imported)} clients.")
                st.rerun()
            else:
                st.error("Config must be a JSON object.")
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")


def _render_add_client(data: dict) -> None:
    st.markdown("### Add New Client")
    with st.form("add_client"):
        col1, col2 = st.columns(2)
        with col1:
            new_id = st.text_input("Client ID", placeholder="e.g. 1200")
            new_name = st.text_input("Client Name", placeholder="e.g. First National CU")
            new_csm = st.text_input("Assigned CSM")
        with col2:
            new_ic = st.text_input("IC Rate", value="0.0050")
            new_fee = st.text_input("NSF/OD Fee", value="30")
            new_cadence = st.selectbox("Review Cadence", _CADENCE_OPTIONS)

        new_stats = st.text_input("Eligible Stat Codes", value="O")

        if st.form_submit_button("Add Client", type="primary"):
            if not new_id:
                st.error("Client ID is required.")
            elif new_id in data:
                st.error(f"Client {new_id} already exists.")
            else:
                client = dict(_EMPTY_CLIENT)
                client["ClientID"] = new_id
                client["ClientName"] = new_name
                client["AssignedCSM"] = new_csm
                client["ICRate"] = new_ic
                client["NSF_OD_Fee"] = new_fee
                client["Cadence"] = new_cadence
                client["EligibleStatusCodes"] = [s.strip() for s in new_stats.split(",") if s.strip()]
                data[new_id] = client
                save_clients_config(data)
                st.success(f"Added client {new_id} -- {new_name}")
                st.rerun()
