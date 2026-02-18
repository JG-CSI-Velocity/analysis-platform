"""Streamlit entry point for the unified analysis platform.

Run with: streamlit run packages/platform_app/src/platform_app/app.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Analysis Platform",
    page_icon="chart_with_upwards_trend",
    layout="wide",
)

PIPELINE_OPTIONS = {
    "ARS Analysis": "ars",
    "Transaction Analysis (Base)": "txn",
    "Transaction Analysis (V4 Storylines)": "txn_v4",
    "ICS Analysis": "ics",
    "ICS Append Pipeline": "ics_append",
}


def main() -> None:
    st.title("Unified Analysis Platform")
    st.markdown("Run ARS, Transaction, and ICS analysis pipelines from a single interface.")

    # Sidebar - Pipeline Selection
    with st.sidebar:
        st.header("Pipeline Configuration")
        selected_pipeline = st.selectbox("Select Pipeline", list(PIPELINE_OPTIONS.keys()))
        pipeline_key = PIPELINE_OPTIONS[selected_pipeline]

        client_id = st.text_input("Client ID", value="")
        client_name = st.text_input("Client Name", value="")

    # Main area - File Upload
    st.header("Data Files")

    col1, col2 = st.columns(2)
    with col1:
        primary_file = st.file_uploader(
            "Primary Data File",
            type=["csv", "xlsx", "xls"],
            help=_file_help(pipeline_key),
        )

    with col2:
        secondary_file = st.file_uploader(
            "Secondary File (Optional)",
            type=["csv", "xlsx", "xls"],
            help="ODD file for V4 storylines, or leave empty.",
        )

    # Run Button
    if st.button("Run Analysis", type="primary", disabled=primary_file is None):
        if primary_file is None:
            st.error("Please upload a data file first.")
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Save uploaded files to temp directory
            primary_path = tmpdir_path / primary_file.name
            primary_path.write_bytes(primary_file.getvalue())

            input_files = _build_input_files(pipeline_key, primary_path)

            if secondary_file:
                secondary_path = tmpdir_path / secondary_file.name
                secondary_path.write_bytes(secondary_file.getvalue())
                input_files["odd"] = secondary_path

            output_dir = tmpdir_path / "output"
            output_dir.mkdir()

            # Run pipeline with progress
            progress_bar = st.progress(0, text="Starting...")
            log_area = st.empty()

            messages: list[str] = []

            def _progress(msg: str) -> None:
                messages.append(msg)
                log_area.code("\n".join(messages[-10:]))
                progress_bar.progress(
                    min(len(messages) / 20, 0.95),
                    text=msg,
                )

            try:
                from platform_app.orchestrator import run_pipeline

                results = run_pipeline(
                    pipeline_key,
                    input_files=input_files,
                    output_dir=output_dir,
                    client_id=client_id,
                    client_name=client_name,
                    progress_callback=_progress,
                )

                progress_bar.progress(1.0, text="Complete!")
                st.success(f"Analysis complete: {len(results)} results produced.")

                # Display results summary
                if results:
                    st.header("Results Summary")
                    for name, ar in results.items():
                        with st.expander(f"{ar.summary or name}"):
                            if "main" in ar.data:
                                st.dataframe(ar.data["main"], use_container_width=True)
                            elif ar.data:
                                for sheet_name, df in ar.data.items():
                                    st.subheader(sheet_name)
                                    st.dataframe(df, use_container_width=True)

                # Offer output files for download
                _offer_downloads(output_dir)

            except Exception as e:
                progress_bar.empty()
                st.error(f"Pipeline failed: {e}")
                st.exception(e)


def _file_help(pipeline: str) -> str:
    """Return help text for the primary file uploader."""
    return {
        "ars": "ODDD Excel file (.xlsx)",
        "txn": "Transaction CSV file (.csv)",
        "txn_v4": "Transaction file (.csv) -- also upload ODD as secondary",
        "ics": "ICS data file (.xlsx or .csv)",
        "ics_append": "Base directory path (not applicable for upload)",
    }.get(pipeline, "Data file")


def _build_input_files(pipeline: str, primary_path: Path) -> dict[str, Path]:
    """Map primary file to the right input key."""
    if pipeline == "ars":
        return {"oddd": primary_path}
    elif pipeline in ("txn", "txn_v4"):
        return {"tran": primary_path}
    elif pipeline == "ics":
        return {"ics": primary_path}
    elif pipeline == "ics_append":
        return {"base_dir": primary_path}
    return {}


def _offer_downloads(output_dir: Path) -> None:
    """Find generated output files and offer as Streamlit downloads."""
    files = list(output_dir.rglob("*"))
    downloadable = [
        f for f in files if f.is_file() and f.suffix in (".xlsx", ".html", ".pptx", ".csv")
    ]

    if downloadable:
        st.header("Download Outputs")
        for f in sorted(downloadable):
            with open(f, "rb") as fh:
                st.download_button(
                    label=f.name,
                    data=fh.read(),
                    file_name=f.name,
                    mime="application/octet-stream",
                )


if __name__ == "__main__":
    main()
