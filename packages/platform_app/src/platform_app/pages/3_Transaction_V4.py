"""Streamlit page: Transaction Analysis V4 Storylines (S0-S9).

Modeled on the standalone v4_app.py reference implementation.
"""

from __future__ import annotations

import re
import time
import traceback
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="V4 Transaction Analysis",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
section[data-testid="stSidebar"] { background: #f8f9fa; }
.stFormSubmitButton > button {
    background: #2E4057 !important; color: #fff !important;
    font-weight: 600 !important; border: none !important; width: 100%;
}
.stFormSubmitButton > button:hover { background: #3d5470 !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


def _strip_html(text: str) -> str:
    """Remove HTML tags for plain-text contexts."""
    return re.sub(r"<[^>]+>", "", text)


# ---------------------------------------------------------------------------
# Storyline labels (imported at runtime to avoid circular deps)
# ---------------------------------------------------------------------------
try:
    from txn_analysis.v4_run import STORYLINE_LABELS
except ImportError:
    STORYLINE_LABELS = {
        "s0": "S0: Executive Summary",
        "s1": "S1: Portfolio Health",
        "s2": "S2: Merchant Intelligence",
        "s3": "S3: Competitive Landscape",
        "s3b": "S3B: Threat Intelligence",
        "s3c": "S3C: Account Segmentation",
        "s4": "S4: Financial Services",
        "s5": "S5: Demographics & Branches",
        "s6": "S6: Risk & Balance",
        "s7": "S7: Campaign Effectiveness",
        "s8": "S8: Payroll & Circular Economy",
        "s9": "S9: Lifecycle Management",
    }

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("V4 Transaction Analysis")

    with st.form("v4_form"):
        st.subheader("Data Sources")
        txn_dir = st.text_input(
            "Transaction directory",
            value=st.session_state.get("v4_txn_dir", ""),
            help="Folder with CSV/TXT files (year subfolders OK)",
            placeholder="/path/to/transaction-files/1453 - Connex",
        )
        c1, c2 = st.columns([2, 1])
        with c1:
            odd_path = st.text_input(
                "ODD file (.xlsx)",
                value=st.session_state.get("v4_odd_path", ""),
                placeholder="/path/to/1453-ODD.xlsx",
            )
        with c2:
            file_ext = st.selectbox("Type", ["csv", "txt"])

        config_path = st.text_input(
            "Config YAML (optional)",
            value=st.session_state.get("v4_config_path", ""),
            placeholder="/path/to/v4_config.yaml",
            help="Custom analysis config (competitor patterns, payroll, etc.)",
        )

        st.subheader("Client")
        id_col, name_col = st.columns(2)
        with id_col:
            client_id = st.text_input("ID", value="", placeholder="e.g. 1453")
        with name_col:
            client_name = st.text_input("Name", value="", placeholder="e.g. Connex CU")

        st.subheader("Storylines")
        all_on = st.checkbox("Select all", value=True, key="v4_select_all")
        selected: list[str] = []
        for key, label in STORYLINE_LABELS.items():
            if st.checkbox(label, value=all_on, key=f"v4_cb_{key}"):
                selected.append(key)

        st.divider()
        submitted = st.form_submit_button("Run Analysis")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.header("V4 Transaction Analysis")
st.caption("Debit card portfolio analytics -- storyline-based")

if not submitted:
    st.info(
        "Configure data sources and client info in the sidebar, "
        "select storylines, and click **Run Analysis**."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors: list[str] = []
if not txn_dir.strip():
    errors.append("Transaction directory is required.")
elif not Path(txn_dir.strip()).exists():
    errors.append(f"Transaction directory not found: `{txn_dir.strip()}`")
elif not list(Path(txn_dir.strip()).rglob(f"*.{file_ext}")):
    errors.append(f"No `.{file_ext}` files found in `{txn_dir.strip()}`")

if not odd_path.strip():
    errors.append("ODD file path is required.")
elif not Path(odd_path.strip()).exists():
    errors.append(f"ODD file not found: `{odd_path.strip()}`")

if not client_id.strip():
    errors.append("Client ID is required.")
if not client_name.strip():
    errors.append("Client Name is required.")
if not selected:
    errors.append("Select at least one storyline.")

if errors:
    for e in errors:
        st.error(e)
    st.stop()

# Remember paths for next run
st.session_state["v4_txn_dir"] = txn_dir.strip()
st.session_state["v4_odd_path"] = odd_path.strip()
st.session_state["v4_config_path"] = config_path.strip()

# ---------------------------------------------------------------------------
# Build config and run
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_DEFAULT_CONFIG = _HERE.parents[2] / "txn_analysis" / "src" / "txn_analysis" / "v4_config.yaml"

cfg_file = config_path.strip() if config_path.strip() else str(_DEFAULT_CONFIG)

from txn_analysis.v4_data_loader import load_config  # noqa: E402, I001

config = load_config(cfg_file) if Path(cfg_file).exists() else {}

config["transaction_dir"] = txn_dir.strip()
config["file_extension"] = file_ext
config["odd_file"] = odd_path.strip()
config["client_id"] = client_id.strip()
config["client_name"] = client_name.strip()
config["output_dir"] = str(
    Path(txn_dir.strip()).parent
    / "output"
    / f"{client_id.strip()}_{client_name.strip().replace(' ', '_')}"
)

progress_bar = st.progress(0, text="Initializing...")
status_box = st.status("Running V4 analysis...", expanded=True)


def _progress(step: int, total: int, label: str) -> None:
    pct = step / total if total > 0 else 0
    progress_bar.progress(pct, text=label)
    status_box.write(label)


t0 = time.time()
try:
    from txn_analysis.v4_run import run_pipeline

    with status_box:
        results, excel_path, html_path = run_pipeline(
            config,
            storylines=selected,
            progress_cb=_progress,
        )
    elapsed = time.time() - t0
    status_box.update(label=f"Complete in {elapsed:.1f}s", state="complete")
    progress_bar.progress(1.0, text="Complete!")
except Exception:
    status_box.update(label="Analysis failed", state="error")
    st.error("Pipeline error -- see traceback below.")
    st.code(traceback.format_exc())
    st.stop()

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
st.subheader(f"{client_id.strip()} - {client_name.strip()}")

total_sections = sum(len(r.get("sections", [])) for r in results.values())
total_figures = sum(
    len(s.get("figures", [])) for r in results.values() for s in r.get("sections", [])
)
total_sheets = sum(len(r.get("sheets", [])) for r in results.values())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Storylines", len(results))
m2.metric("Sections", total_sections)
m3.metric("Charts", total_figures)
m4.metric("Sheets", total_sheets)

# ---------------------------------------------------------------------------
# Tabbed results viewer
# ---------------------------------------------------------------------------
if results:
    tab_labels = []
    tab_keys = []
    for key in results:
        label = STORYLINE_LABELS.get(key, key)
        short = label.split(":")[0] if ":" in label else label
        tab_labels.append(short)
        tab_keys.append(key)

    tabs = st.tabs(tab_labels)

    for tab, key in zip(tabs, tab_keys):
        result = results[key]
        sections = result.get("sections", [])
        desc = result.get("description", "")

        with tab:
            if "Error:" in desc:
                st.error(desc)
                continue

            st.success(f"{len(sections)} sections")

            for section in sections:
                heading = section.get("heading", "")
                narrative = section.get("narrative", "")
                figures = section.get("figures", [])
                tables = section.get("tables", [])

                st.markdown(f"#### {_strip_html(heading)}")
                if narrative:
                    st.markdown(_strip_html(narrative))

                for fig in figures:
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key=f"{key}_{heading}_{id(fig)}",
                    )

                for tbl_title, tbl_df in tables:
                    with st.expander(f"Table: {tbl_title}"):
                        st.dataframe(tbl_df, use_container_width=True)

# ---------------------------------------------------------------------------
# Download section
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Export")

dl1, dl2, dl3 = st.columns(3)

if excel_path.exists():
    with open(excel_path, "rb") as f:
        dl1.download_button(
            "Download Excel Workbook",
            data=f.read(),
            file_name=excel_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

if html_path.exists():
    with open(html_path, "rb") as f:
        dl2.download_button(
            "Download HTML Dashboard",
            data=f.read(),
            file_name=html_path.name,
            mime="text/html",
            use_container_width=True,
        )

dl3.caption(f"Saved to `{config['output_dir']}`")
