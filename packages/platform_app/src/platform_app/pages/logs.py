"""RPE Log Viewer -- browse and copy application logs without leaving the UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

st.markdown('<p class="uap-label">DIAGNOSTICS / LOGS</p>', unsafe_allow_html=True)
st.title("Application Logs")
st.caption(
    "All pipeline output, errors, and tracebacks are saved here. "
    "Select text below and copy it to share with support."
)

# ---------------------------------------------------------------------------
# Log file path
# ---------------------------------------------------------------------------
LOG_FILE = Path("logs/app.log")

if not LOG_FILE.exists():
    st.info("No log file found yet. Run an analysis first.")
    st.stop()

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    lines_to_show = st.selectbox(
        "Show last N lines",
        [50, 100, 200, 500, 1000],
        index=1,
        key="log_lines",
    )
with c2:
    level_filter = st.selectbox(
        "Filter level",
        ["ALL", "ERROR", "CRITICAL", "WARNING"],
        key="log_level_filter",
    )
with c3:
    search_term = st.text_input("Search", key="log_search", placeholder="keyword...")

# ---------------------------------------------------------------------------
# Read and filter
# ---------------------------------------------------------------------------
raw_lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()

# Take last N lines
tail = raw_lines[-lines_to_show:]

# Apply level filter
if level_filter != "ALL":
    tail = [ln for ln in tail if f"[{level_filter}]" in ln]

# Apply search filter
if search_term.strip():
    needle = search_term.strip().lower()
    tail = [ln for ln in tail if needle in ln.lower()]

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
st.markdown(
    f'<p class="uap-label">{len(tail)} LINES '
    f'(of {len(raw_lines)} total in log file)</p>',
    unsafe_allow_html=True,
)

if not tail:
    st.info("No matching log entries.")
    st.stop()

# Show as a code block -- easy to select-all and copy
log_text = "\n".join(tail)
st.code(log_text, language="log", line_numbers=True)

# Download button for full log
st.download_button(
    "Download Full Log",
    LOG_FILE.read_bytes(),
    file_name="app.log",
    mime="text/plain",
    key="dl_log",
)

# ---------------------------------------------------------------------------
# Quick error summary
# ---------------------------------------------------------------------------
error_lines = [ln for ln in raw_lines if "[ERROR]" in ln or "[CRITICAL]" in ln]
if error_lines:
    st.divider()
    st.markdown(
        f'<p class="uap-label">RECENT ERRORS ({len(error_lines)} total)</p>',
        unsafe_allow_html=True,
    )
    # Show last 10 errors
    for line in error_lines[-10:]:
        st.error(line, icon=None)
