"""Streamlit page: ICS Analysis pipeline."""

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


st.set_page_config(page_title="ICS Analysis", layout="wide")
st.title("ICS Analysis")
st.markdown("Analyze ICS (Instant Card Services) data: portfolio health, activation, usage trends.")

client_id = st.text_input("Client ID", value="")
client_name = st.text_input("Client Name", value="")

uploaded = st.file_uploader("ICS Data File", type=["xlsx", "csv"])

if st.button("Run ICS Analysis", type="primary", disabled=uploaded is None):
    if uploaded is None:
        st.error("Please upload an ICS data file.")
        st.stop()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        file_path = tmpdir_path / uploaded.name
        file_path.write_bytes(uploaded.getvalue())

        output_dir = tmpdir_path / "output"
        output_dir.mkdir()

        progress = st.progress(0, text="Starting ICS analysis...")
        messages: list[str] = []

        def _on_progress(msg: str) -> None:
            messages.append(msg)
            progress.progress(min(len(messages) / 15, 0.95), text=msg)

        try:
            from platform_app.orchestrator import run_pipeline

            results = run_pipeline(
                "ics",
                input_files={"ics": file_path},
                output_dir=output_dir,
                client_id=client_id,
                client_name=client_name,
                progress_callback=_on_progress,
            )
            progress.progress(1.0, text="Complete!")
            st.success(f"ICS analysis complete: {len(results)} results.")

            for name, ar in results.items():
                with st.expander(ar.summary or name):
                    for sheet_name, df in ar.data.items():
                        st.dataframe(df, use_container_width=True)

            _offer_downloads(output_dir)
        except Exception as e:
            progress.empty()
            st.error(f"ICS pipeline failed: {e}")
            st.exception(e)
