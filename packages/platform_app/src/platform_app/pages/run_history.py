"""RPE Run History -- visual timeline of pipeline executions with charts."""

from __future__ import annotations

from collections import Counter

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
success_rate = (successes / total * 100) if total else 0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Runs", total)
m2.metric("Success", successes)
m3.metric("Partial", partials)
m4.metric("Failed", failures)
m5.metric("Avg Time", f"{avg_time:.1f}s")
m6.metric("Success Rate", f"{success_rate:.0f}%")

# ---------------------------------------------------------------------------
# Visual charts (only if enough data)
# ---------------------------------------------------------------------------
if total >= 3:
    st.divider()
    st.markdown('<p class="uap-label">TRENDS</p>', unsafe_allow_html=True)

    chart_col1, chart_col2 = st.columns(2)

    # Status breakdown bar chart
    with chart_col1:
        status_counts = Counter(r.status for r in history)
        status_df = pd.DataFrame(
            {"Status": list(status_counts.keys()), "Count": list(status_counts.values())}
        )
        st.bar_chart(status_df, x="Status", y="Count", color="#16A34A")

    # Runtime over time (line chart of last 20 runs)
    with chart_col2:
        recent = history[:20]
        runtime_df = pd.DataFrame(
            {
                "Run": [r.run_id[:8] for r in recent],
                "Runtime (s)": [r.runtime_seconds for r in recent],
            }
        )
        st.line_chart(runtime_df, x="Run", y="Runtime (s)", color="#0090D4")

    # Pipeline breakdown
    pipeline_counts = Counter(r.pipeline for r in history)
    if len(pipeline_counts) > 1:
        pipeline_df = pd.DataFrame(
            {"Pipeline": list(pipeline_counts.keys()), "Runs": list(pipeline_counts.values())}
        )
        st.bar_chart(pipeline_df, x="Pipeline", y="Runs", color="#F59E0B")

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
