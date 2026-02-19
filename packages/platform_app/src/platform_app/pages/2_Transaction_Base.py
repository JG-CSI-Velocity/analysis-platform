"""Streamlit page: Transaction Analysis (Base M1-M10).

Accepts a directory of transaction files (CSV or TXT), concatenates them,
and runs the M1-M10 analysis modules.
"""

from __future__ import annotations

import tempfile
import time
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Transaction Analysis (Base)", layout="wide")

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
    st.title("Transaction Analysis (Base)")

    with st.form("txn_base_form"):
        st.subheader("Data Sources")
        txn_dir = st.text_input(
            "Transaction directory",
            value=st.session_state.get("txn_base_dir", ""),
            help="Folder with CSV/TXT files (year subfolders OK)",
            placeholder="/path/to/transaction-files/1453 - Connex",
        )
        c1, c2 = st.columns([2, 1])
        with c1:
            single_file = st.text_input(
                "Or single file (optional)",
                value=st.session_state.get("txn_base_file", ""),
                placeholder="/path/to/transactions.csv",
                help="Use this instead of a directory for a single file",
            )
        with c2:
            file_ext = st.selectbox("Type", ["csv", "txt"])

        st.subheader("Client")
        c1, c2 = st.columns(2)
        with c1:
            client_id = st.text_input("ID", value="", placeholder="e.g. 1453")
        with c2:
            client_name = st.text_input("Name", value="", placeholder="e.g. Connex CU")

        st.divider()
        submitted = st.form_submit_button("Run Base Analysis")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.header("Transaction Analysis (Base)")
st.caption("Debit card portfolio analysis: M1-M10 modules")

if not submitted:
    st.info(
        "Point to a **directory** of transaction files (or a single file), "
        "enter client info, and click **Run Base Analysis**."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors: list[str] = []
use_dir = bool(txn_dir.strip())
use_file = bool(single_file.strip())

if not use_dir and not use_file:
    errors.append("Provide a transaction directory or a single file path.")
elif use_dir:
    txn_path = Path(txn_dir.strip())
    if not txn_path.exists():
        errors.append(f"Transaction directory not found: `{txn_path}`")
    elif not txn_path.is_dir():
        errors.append(f"Not a directory: `{txn_path}`")
    elif not list(txn_path.rglob(f"*.{file_ext}")):
        errors.append(f"No `.{file_ext}` files found in `{txn_path}`")
elif use_file:
    file_path = Path(single_file.strip())
    if not file_path.exists():
        errors.append(f"File not found: `{file_path}`")

if not client_id.strip():
    errors.append("Client ID is required.")
if not client_name.strip():
    errors.append("Client Name is required.")

if errors:
    for e in errors:
        st.error(e)
    st.stop()

# Remember paths for next run
if use_dir:
    st.session_state["txn_base_dir"] = txn_dir.strip()
if use_file:
    st.session_state["txn_base_file"] = single_file.strip()

# ---------------------------------------------------------------------------
# Discover and merge files
# ---------------------------------------------------------------------------
if use_dir:
    txn_path = Path(txn_dir.strip())
    all_files = sorted(txn_path.rglob(f"*.{file_ext}"))
    st.info(f"Found **{len(all_files)}** `.{file_ext}` files in `{txn_path.name}`")

    frames: list[pd.DataFrame] = []
    for f in all_files:
        try:
            if file_ext == "csv":
                df = pd.read_csv(f)
            else:
                df = pd.read_csv(f, sep="\t")
            frames.append(df)
        except Exception as exc:
            st.warning(f"Skipped `{f.name}`: {exc}")

    if not frames:
        st.error("No files could be loaded.")
        st.stop()

    merged = pd.concat(frames, ignore_index=True)
    st.success(f"Merged **{len(merged):,}** rows from **{len(frames)}** files")

    # Write merged data to a temp CSV the pipeline can read
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, prefix="txn_merged_")
    merged.to_csv(tmp.name, index=False)
    tran_file = Path(tmp.name)
    output_dir = (
        txn_path.parent
        / "output_base"
        / f"{client_id.strip()}_{client_name.strip().replace(' ', '_')}"
    )
else:
    tran_file = Path(single_file.strip())
    output_dir = tran_file.parent / "output_base"

output_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------
progress_bar = st.progress(0, text="Initializing...")
status_box = st.status("Running base transaction analysis...", expanded=True)

messages: list[str] = []


def _on_progress(msg: str) -> None:
    messages.append(msg)
    progress_bar.progress(min(len(messages) / 20, 0.95), text=msg)
    status_box.write(msg)


t0 = time.time()
try:
    from platform_app.orchestrator import run_pipeline  # noqa: E402

    with status_box:
        results = run_pipeline(
            "txn",
            input_files={"tran": tran_file},
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
m1.metric("Modules", len(results))
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
