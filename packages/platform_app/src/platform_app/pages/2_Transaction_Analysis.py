"""Streamlit page: Transaction Analysis pipeline (base + V4 storylines)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st


def _offer_downloads(output_dir: Path) -> None:
    files = sorted(
        f for f in output_dir.rglob("*")
        if f.is_file() and f.suffix in (".xlsx", ".pptx", ".csv", ".html", ".png")
    )
    if files:
        st.header("Downloads")
        for f in files:
            st.download_button(f.name, f.read_bytes(), file_name=f.name, mime="application/octet-stream")


st.set_page_config(page_title="Transaction Analysis", layout="wide")
st.title("Transaction Analysis")
st.markdown("Analyze debit card transaction data.")

mode = st.radio("Pipeline Mode", ["Base (M1-M10)", "V4 Storylines (S1-S9)"], horizontal=True)
pipeline_key = "txn" if mode.startswith("Base") else "txn_v4"

client_id = st.text_input("Client ID", value="")
client_name = st.text_input("Client Name", value="")

col1, col2 = st.columns(2)
with col1:
    tran_file = st.file_uploader("Transaction CSV", type=["csv"])
with col2:
    odd_file = st.file_uploader("ODD File (V4 only)", type=["csv", "xlsx"]) if pipeline_key == "txn_v4" else None

if st.button("Run Transaction Analysis", type="primary", disabled=tran_file is None):
    if tran_file is None:
        st.error("Please upload a transaction file.")
        st.stop()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        tran_path = tmpdir_path / tran_file.name
        tran_path.write_bytes(tran_file.getvalue())

        input_files: dict[str, Path] = {"tran": tran_path}

        if odd_file:
            odd_path = tmpdir_path / odd_file.name
            odd_path.write_bytes(odd_file.getvalue())
            input_files["odd"] = odd_path

        output_dir = tmpdir_path / "output"
        output_dir.mkdir()

        progress = st.progress(0, text="Starting transaction analysis...")
        messages: list[str] = []

        def _on_progress(msg: str) -> None:
            messages.append(msg)
            progress.progress(min(len(messages) / 20, 0.95), text=msg)

        try:
            from platform_app.orchestrator import run_pipeline

            results = run_pipeline(
                pipeline_key,
                input_files=input_files,
                output_dir=output_dir,
                client_id=client_id,
                client_name=client_name,
                progress_callback=_on_progress,
            )
            progress.progress(1.0, text="Complete!")
            st.success(f"Transaction analysis complete: {len(results)} results.")

            for name, ar in results.items():
                with st.expander(ar.summary or name):
                    for sheet_name, df in ar.data.items():
                        st.dataframe(df, use_container_width=True)

            _offer_downloads(output_dir)
        except Exception as e:
            progress.empty()
            st.error(f"Transaction pipeline failed: {e}")
            st.exception(e)
