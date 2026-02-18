"""Streamlit page: ICS Analysis pipeline."""

from __future__ import annotations

import time
import traceback
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="ICS Analysis", layout="wide")

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

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("ICS Analysis")

    with st.form("ics_form"):
        st.subheader("Data Sources")
        ics_path = st.text_input(
            "ICS Data File (.xlsx)",
            value=st.session_state.get("ics_data_path", ""),
            placeholder="/path/to/ics_data.xlsx",
        )

        st.subheader("Client")
        c1, c2 = st.columns(2)
        with c1:
            client_id = st.text_input("ID", value="", placeholder="e.g. 1453")
        with c2:
            client_name = st.text_input("Name", value="", placeholder="e.g. Connex CU")

        st.divider()
        submitted = st.form_submit_button("Run ICS Analysis")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.header("ICS Analysis")
st.caption("Instant Card Services: portfolio health, activation, usage trends")

if not submitted:
    st.info(
        "Enter the ICS data file path and client info in the sidebar, "
        "then click **Run ICS Analysis**."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors: list[str] = []
if not ics_path.strip():
    errors.append("ICS data file path is required.")
elif not Path(ics_path.strip()).exists():
    errors.append(f"ICS data file not found: `{ics_path.strip()}`")
if not client_id.strip():
    errors.append("Client ID is required.")
if not client_name.strip():
    errors.append("Client Name is required.")

if errors:
    for e in errors:
        st.error(e)
    st.stop()

st.session_state["ics_data_path"] = ics_path.strip()

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------
ics_file = Path(ics_path.strip())
output_dir = ics_file.parent / "output_ics"
output_dir.mkdir(parents=True, exist_ok=True)

progress_bar = st.progress(0, text="Initializing...")
status_box = st.status("Running ICS analysis...", expanded=True)

messages: list[str] = []


def _on_progress(msg: str) -> None:
    messages.append(msg)
    progress_bar.progress(min(len(messages) / 20, 0.95), text=msg)
    status_box.write(msg)


t0 = time.time()
try:
    from platform_app.orchestrator import run_pipeline

    with status_box:
        results = run_pipeline(
            "ics",
            input_files={"ics": ics_file},
            output_dir=output_dir,
            client_id=client_id.strip(),
            client_name=client_name.strip(),
            progress_callback=_on_progress,
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
# Results
# ---------------------------------------------------------------------------
st.subheader(f"{client_id.strip()} - {client_name.strip()}")

m1, m2 = st.columns(2)
m1.metric("Analyses", len(results))
m2.metric("Output Dir", str(output_dir))

if results:
    tabs = st.tabs(list(results.keys()))
    for tab, (name, ar) in zip(tabs, results.items()):
        with tab:
            st.markdown(f"**{ar.summary or name}**")
            for sheet_name, df in ar.data.items():
                with st.expander(sheet_name, expanded=False):
                    st.dataframe(df, use_container_width=True)

# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Export")

downloadable = sorted(
    f
    for f in output_dir.rglob("*")
    if f.is_file() and f.suffix in (".xlsx", ".pptx", ".png", ".csv", ".html")
)

if downloadable:
    for f in downloadable:
        mime = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".png": "image/png",
            ".csv": "text/csv",
            ".html": "text/html",
        }.get(f.suffix, "application/octet-stream")
        st.download_button(f.name, f.read_bytes(), file_name=f.name, mime=mime)
else:
    st.caption("No output files found.")

st.caption(f"Output saved to `{output_dir}`")
