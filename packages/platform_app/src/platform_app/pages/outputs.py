"""RPE Outputs -- view results and download generated files."""

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
# Collect files once (avoid repeated rglob on network drives)
# ---------------------------------------------------------------------------
_DELIVERABLE_EXTS = {".pptx", ".xlsx"}

deliverables: list[Path] = []
chart_paths: dict[str, list[Path]] = {}  # pipeline -> [chart paths]
total_analyses = sum(len(r) for r in results.values())

for pipeline_name, out_dir in output_dirs.items():
    if not out_dir or not Path(out_dir).is_dir():
        continue
    for f in Path(out_dir).rglob("*"):
        if not f.is_file():
            continue
        if f.suffix in _DELIVERABLE_EXTS:
            deliverables.append(f)
        elif f.suffix == ".png":
            chart_paths.setdefault(pipeline_name, []).append(f)

total_charts = sum(len(v) for v in chart_paths.values())

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">LAST RUN</p>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Pipelines", len(results))
m2.metric("Analyses", total_analyses)
m3.metric("Charts", total_charts)
m4.metric("Run ID", run_id or "--")

# ---------------------------------------------------------------------------
# Deliverable downloads (PPTX, Excel) -- top priority
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">DELIVERABLES</p>', unsafe_allow_html=True)

if deliverables:
    for f in sorted(deliverables, key=lambda p: p.name):
        ext_label = f.suffix.lstrip(".").upper()
        badge_cls = "uap-badge-ready" if f.suffix == ".pptx" else "uap-badge-active"
        dl_cols = st.columns([1, 4, 1])
        dl_cols[0].markdown(
            f'<span class="uap-badge {badge_cls}">{ext_label}</span>',
            unsafe_allow_html=True,
        )
        dl_cols[1].markdown(
            f'<span style="font-family:var(--uap-mono);font-size:0.82rem;">{f.name}</span>'
            f'<br><span style="font-size:0.7rem;color:#94A3B8;">{f.parent}</span>',
            unsafe_allow_html=True,
        )
        mime = MIME_MAP.get(f.suffix, "application/octet-stream")
        dl_cols[2].download_button(
            "Download",
            f.read_bytes(),
            file_name=f.name,
            mime=mime,
            key=f"dl_{f.name}",
        )
else:
    st.caption("No PPTX or Excel files found.")

# ---------------------------------------------------------------------------
# Data tables (from analysis results)
# ---------------------------------------------------------------------------
if results:
    st.divider()
    st.markdown('<p class="uap-label">DATA TABLES</p>', unsafe_allow_html=True)

    for pipeline_name, pipeline_results in results.items():
        with st.expander(
            f"{pipeline_name.upper()} -- {len(pipeline_results)} analyses", expanded=False
        ):
            for name, ar in pipeline_results.items():
                st.markdown(
                    f'<span style="font-family:var(--uap-mono);font-size:0.75rem;color:var(--uap-dim);">'
                    f"{name}</span>",
                    unsafe_allow_html=True,
                )
                for _sheet_name, df in ar.data.items():
                    st.dataframe(df, width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
# Charts -- lazy load behind expander (avoids 75+ PNG network reads)
# ---------------------------------------------------------------------------
if chart_paths:
    st.divider()
    st.markdown('<p class="uap-label">CHARTS</p>', unsafe_allow_html=True)
    st.caption(f"{total_charts} chart images available. Expand a section to view.")

    for pipeline_name, charts in chart_paths.items():
        charts_sorted = sorted(charts, key=lambda p: p.name)
        with st.expander(
            f"{pipeline_name.upper()} -- {len(charts_sorted)} charts",
            expanded=False,
        ):
            chart_cols = st.columns(2)
            for i, img_path in enumerate(charts_sorted):
                with chart_cols[i % 2]:
                    st.image(str(img_path), caption=img_path.stem, width="stretch")

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
