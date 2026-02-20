"""UAP Run History -- view past pipeline executions."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from platform_app.core.run_logger import load_history

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">OUTPUTS / RUN HISTORY</p>', unsafe_allow_html=True)
st.title("Run History")
st.caption("Track all pipeline executions with timing, status, and output paths.")

# ---------------------------------------------------------------------------
# Load history
# ---------------------------------------------------------------------------
history = load_history(limit=200)

if not history:
    st.info("No run history yet. Execute a pipeline from **Run Analysis** or **Batch Run**.")
    st.stop()

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
total = len(history)
successes = sum(1 for r in history if r.status == "success")
failures = sum(1 for r in history if r.status == "error")
partials = sum(1 for r in history if r.status == "partial")
avg_time = sum(r.runtime_seconds for r in history) / total if total else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Runs", total)
m2.metric("Success", successes)
m3.metric("Partial", partials)
m4.metric("Failed", failures)
m5.metric("Avg Time", f"{avg_time:.1f}s")

st.divider()

# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------
f1, f2 = st.columns(2)
with f1:
    client_filter = st.text_input("Filter by client ID", key="hist_client_filter")
with f2:
    status_filter = st.selectbox(
        "Status", ["All", "success", "partial", "error"], key="hist_status_filter"
    )

filtered = history
if client_filter.strip():
    filtered = [r for r in filtered if client_filter.strip().lower() in r.client_id.lower()]
if status_filter != "All":
    filtered = [r for r in filtered if r.status == status_filter]

# ---------------------------------------------------------------------------
# History table
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">RUNS</p>', unsafe_allow_html=True)

if not filtered:
    st.info("No matching runs.")
    st.stop()

# Build DataFrame for display
rows = []
for r in filtered:
    rows.append(
        {
            "Run ID": r.run_id,
            "Timestamp": r.timestamp,
            "CSM": r.csm,
            "Client": r.client_id,
            "Pipeline": r.pipeline,
            "Status": r.status.upper(),
            "Time (s)": f"{r.runtime_seconds:.1f}",
            "Results": r.result_count,
            "Output": r.output_dir,
        }
    )

df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Detailed view
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">DETAILS</p>', unsafe_allow_html=True)

for record in filtered[:10]:
    status_class = {
        "success": "uap-badge-ready",
        "partial": "uap-badge-active",
        "error": "uap-badge-error",
    }.get(record.status, "uap-badge-muted")

    with st.expander(f"{record.run_id} -- {record.client_id} / {record.pipeline}", expanded=False):
        d1, d2, d3 = st.columns(3)
        d1.markdown(f"**CSM:** {record.csm or '--'}")
        d2.markdown(f"**Client:** {record.client_id} - {record.client_name}")
        d3.markdown(f"**Runtime:** {record.runtime_seconds:.1f}s")

        if record.modules_run:
            st.markdown(
                '<p class="uap-label">MODULES EXECUTED</p>',
                unsafe_allow_html=True,
            )
            st.code(", ".join(record.modules_run), language=None)

        if record.error_message:
            st.error(record.error_message)

        st.caption(f"Output: `{record.output_dir}`")
        if record.input_file_hash:
            st.caption(f"Input hash: `{record.input_file_hash}`")
