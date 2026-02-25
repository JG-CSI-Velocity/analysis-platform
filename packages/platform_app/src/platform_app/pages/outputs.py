"""RPE Outputs Dashboard -- visual results summary with KPIs, charts, and downloads."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from platform_app.components.download import MIME_MAP

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">OUTPUTS / DASHBOARD</p>', unsafe_allow_html=True)
st.title("Results Dashboard")

# ---------------------------------------------------------------------------
# Load last results from session
# ---------------------------------------------------------------------------
results = st.session_state.get("uap_last_results", {})
output_dirs = st.session_state.get("uap_last_output_dirs", {})
errors = st.session_state.get("uap_last_errors", {})
run_id = st.session_state.get("uap_last_run_id", "")
elapsed = st.session_state.get("uap_last_elapsed", 0.0)
client_label = st.session_state.get("uap_last_client", "")

if not results and not errors:
    st.info("No results yet. Run an analysis from **Run Analysis** or **Batch Run**.")
    st.stop()

# ---------------------------------------------------------------------------
# Collect files once (avoid repeated rglob on network drives)
# ---------------------------------------------------------------------------
_DELIVERABLE_EXTS = {".pptx", ".xlsx"}

deliverables: list[Path] = []
chart_paths: dict[str, list[Path]] = {}
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
total_deliverables = len(deliverables)

# ---------------------------------------------------------------------------
# Command Center -- dark KPI banner
# ---------------------------------------------------------------------------
_pipelines_str = " + ".join(sorted(results.keys())).upper() if results else "--"
_elapsed_str = f"{elapsed:.1f}s" if elapsed else "--"

st.markdown(
    f"""
<div class="uap-command-center">
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:1.5rem;">
    <div>
      <div class="cc-label">CLIENT</div>
      <div class="cc-value-sm">{client_label or "--"}</div>
    </div>
    <div>
      <div class="cc-label">PIPELINES</div>
      <div class="cc-value-sm">{_pipelines_str}</div>
    </div>
    <div>
      <div class="cc-label">ANALYSES</div>
      <div class="cc-value">{total_analyses}</div>
    </div>
    <div>
      <div class="cc-label">CHARTS</div>
      <div class="cc-value">{total_charts}</div>
    </div>
    <div>
      <div class="cc-label">RUNTIME</div>
      <div class="cc-value-sm">{_elapsed_str}</div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Key Findings -- extract summaries from analysis results
# ---------------------------------------------------------------------------
findings: list[dict[str, str]] = []
for pipeline_name, pipeline_results in results.items():
    for name, ar in pipeline_results.items():
        summary = ar.summary if hasattr(ar, "summary") else ""
        if summary and summary.strip():
            findings.append({"pipeline": pipeline_name, "name": name, "summary": summary})

if findings:
    st.markdown('<p class="uap-label">KEY FINDINGS</p>', unsafe_allow_html=True)
    # Show top 6 findings as cards
    top_findings = findings[:6]
    cols = st.columns(min(3, len(top_findings)))
    for i, f in enumerate(top_findings):
        with cols[i % 3]:
            badge_cls = "uap-badge-active"
            st.markdown(
                f"""<div class="uap-card">
                <span class="uap-badge {badge_cls}">{f["pipeline"].upper()}</span>
                <h4 style="margin-top:0.5rem;">{f["name"].replace("_", " ").title()}</h4>
                <p>{f["summary"][:200]}</p>
                </div>""",
                unsafe_allow_html=True,
            )
    if len(findings) > 6:
        with st.expander(f"View all {len(findings)} findings"):
            for f in findings[6:]:
                st.markdown(
                    f"**[{f['pipeline'].upper()}] {f['name'].replace('_', ' ').title()}**: "
                    f"{f['summary']}"
                )

# ---------------------------------------------------------------------------
# Tabs: Downloads | Charts | Data Tables
# ---------------------------------------------------------------------------
st.divider()

tab_dl, tab_charts, tab_data = st.tabs(
    [
        f"Downloads ({total_deliverables})",
        f"Charts ({total_charts})",
        f"Data Tables ({total_analyses})",
    ]
)

# --- Downloads tab ---
with tab_dl:
    if deliverables:
        for f in sorted(deliverables, key=lambda p: p.name):
            ext = f.suffix.lstrip(".").upper()
            icon_cls = "dl-pptx" if f.suffix == ".pptx" else "dl-xlsx"
            dl_cols = st.columns([0.6, 3, 1])
            with dl_cols[0]:
                st.markdown(
                    f'<div class="uap-dl-icon {icon_cls}">{ext}</div>',
                    unsafe_allow_html=True,
                )
            with dl_cols[1]:
                st.markdown(
                    f'<div class="uap-dl-info">'
                    f'<div class="dl-name">{f.name}</div>'
                    f'<div class="dl-path">{f.parent}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with dl_cols[2]:
                mime = MIME_MAP.get(f.suffix, "application/octet-stream")
                st.download_button(
                    "Download",
                    f.read_bytes(),
                    file_name=f.name,
                    mime=mime,
                    key=f"dl_{f.name}",
                )
    else:
        st.caption("No PPTX or Excel files generated.")

# --- Charts tab ---
with tab_charts:
    if chart_paths:
        for pipeline_name, charts in sorted(chart_paths.items()):
            st.markdown(
                f'<p class="uap-label">{pipeline_name.upper()} -- {len(charts)} CHARTS</p>',
                unsafe_allow_html=True,
            )
            charts_sorted = sorted(charts, key=lambda p: p.name)
            # 3-column grid
            cols = st.columns(3)
            for i, img_path in enumerate(charts_sorted):
                with cols[i % 3]:
                    st.image(str(img_path), caption=img_path.stem, use_container_width=True)
            st.divider()
    else:
        st.caption("No chart images generated.")

# --- Data Tables tab ---
with tab_data:
    if results:
        # Pipeline selector for large result sets
        pipeline_names = list(results.keys())
        if len(pipeline_names) > 1:
            selected_pipeline = st.selectbox(
                "Pipeline", pipeline_names, key="outputs_pipeline_select"
            )
        else:
            selected_pipeline = pipeline_names[0]

        pipeline_results = results.get(selected_pipeline, {})
        if pipeline_results:
            st.markdown(
                f'<p class="uap-label">{selected_pipeline.upper()} -- '
                f"{len(pipeline_results)} ANALYSES</p>",
                unsafe_allow_html=True,
            )
            for name, ar in pipeline_results.items():
                title = (
                    ar.title
                    if hasattr(ar, "title") and ar.title
                    else name.replace("_", " ").title()
                )
                with st.expander(title, expanded=False):
                    if hasattr(ar, "summary") and ar.summary:
                        st.caption(ar.summary)
                    for _sheet_name, df in ar.data.items():
                        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No data tables available.")

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
    for k in [
        "uap_last_results",
        "uap_last_output_dirs",
        "uap_last_errors",
        "uap_last_run_id",
        "uap_last_elapsed",
        "uap_last_client",
    ]:
        st.session_state.pop(k, None)
    st.rerun()
