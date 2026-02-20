"""UAP Outputs -- view results and download generated files."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from platform_app.components.download import MIME_MAP

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">OUTPUTS / VIEW</p>', unsafe_allow_html=True)
st.title("View Outputs")

# ---------------------------------------------------------------------------
# Load last results from session
# ---------------------------------------------------------------------------
results = st.session_state.get("uap_last_results", {})
output_dirs = st.session_state.get("uap_last_output_dirs", {})
errors = st.session_state.get("uap_last_errors", {})
run_id = st.session_state.get("uap_last_run_id", "")

if not results and not errors:
    st.info("No results yet. Run an analysis from **Run Analysis** or **Batch Run**.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">LAST RUN</p>', unsafe_allow_html=True)

total_analyses = sum(len(r) for r in results.values())
total_charts = 0
all_files: list[Path] = []

for out_dir in output_dirs.values():
    if out_dir and Path(out_dir).is_dir():
        charts = sorted(Path(out_dir).rglob("*.png"))
        total_charts += len(charts)
        all_files.extend(
            f for f in Path(out_dir).rglob("*") if f.is_file() and f.suffix in MIME_MAP
        )

m1, m2, m3, m4 = st.columns(4)
m1.metric("Pipelines", len(results))
m2.metric("Analyses", total_analyses)
m3.metric("Charts", total_charts)
m4.metric("Run ID", run_id or "--")

st.divider()

# ---------------------------------------------------------------------------
# Results by pipeline
# ---------------------------------------------------------------------------
if results:
    pipeline_tabs = st.tabs([name.upper() for name in results])

    for tab, (pipeline_name, pipeline_results) in zip(pipeline_tabs, results.items()):
        with tab:
            out_dir = output_dirs.get(pipeline_name)

            # Per-pipeline metrics
            c1, c2 = st.columns(2)
            c1.metric("Analyses", len(pipeline_results))
            if out_dir:
                chart_count = (
                    len(sorted(Path(out_dir).rglob("*.png"))) if Path(out_dir).is_dir() else 0
                )
                c2.metric("Charts", chart_count)

            # Data tables
            st.markdown('<p class="uap-label">DATA TABLES</p>', unsafe_allow_html=True)
            for name, ar in pipeline_results.items():
                with st.expander(ar.summary or name, expanded=False):
                    for sheet_name, df in ar.data.items():
                        st.dataframe(df, use_container_width=True, hide_index=True)

            # Charts
            if out_dir and Path(out_dir).is_dir():
                charts = sorted(Path(out_dir).rglob("*.png"))
                if charts:
                    st.markdown('<p class="uap-label">CHARTS</p>', unsafe_allow_html=True)
                    chart_cols = st.columns(2)
                    for i, img_path in enumerate(charts):
                        with chart_cols[i % 2]:
                            st.image(str(img_path), caption=img_path.stem, use_container_width=True)

# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">DOWNLOADS</p>', unsafe_allow_html=True)

if all_files:
    # Group by type
    by_type: dict[str, list[Path]] = {}
    for f in sorted(all_files, key=lambda p: p.name):
        by_type.setdefault(f.suffix, []).append(f)

    for ext, files in sorted(by_type.items()):
        ext_label = ext.lstrip(".").upper()
        st.markdown(
            f'<p style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8; margin: 0.5rem 0 0.25rem;">'
            f"{ext_label} FILES ({len(files)})</p>",
            unsafe_allow_html=True,
        )
        for f in files:
            mime = MIME_MAP.get(f.suffix, "application/octet-stream")
            st.download_button(
                f.name,
                f.read_bytes(),
                file_name=f.name,
                mime=mime,
                key=f"dl_{pipeline_name}_{f.name}",
            )
else:
    st.caption("No downloadable files found.")

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
if errors:
    st.divider()
    st.markdown('<p class="uap-label">ERRORS</p>', unsafe_allow_html=True)
    for name, tb in errors.items():
        with st.expander(f"{name.upper()} -- Error", expanded=False):
            st.code(tb)

# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------
st.divider()
if st.button("Clear Results", key="outputs_clear"):
    for k in ["uap_last_results", "uap_last_output_dirs", "uap_last_errors", "uap_last_run_id"]:
        st.session_state.pop(k, None)
    st.rerun()
