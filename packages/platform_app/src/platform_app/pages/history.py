"""Run History page -- compact log of past pipeline executions across all pipelines."""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

import streamlit as st

from platform_app.components import kpi_row

logger = logging.getLogger(__name__)

_HISTORY_DIR = Path.home() / ".ars_platform"
HISTORY_PATH = _HISTORY_DIR / "run_history.json"


def _get_page(name: str):
    return st.session_state.get("_pages", {}).get(name)


def render() -> None:
    try:
        _render_inner()
    except Exception:
        st.error("Something went wrong loading history. Please try refreshing.")
        logger.exception("Unhandled error in history")


def _render_inner() -> None:
    st.title("Run History")
    st.caption("Review past pipeline executions across ARS, Transaction, and ICS")

    history = _load_full_history()

    if not history:
        st.info("No runs recorded yet. Run an analysis to see history here.")
        run_pg = _get_page("run")
        if run_pg and st.button("Go to Run Analysis", type="primary"):
            st.switch_page(run_pg)
        return

    # KPI summary
    total = len(history)
    successes = sum(1 for r in history if r.get("success"))
    avg_time = sum(r.get("elapsed", 0) for r in history) / total if total else 0

    if total >= 3:
        kpi_row([
            {"label": "Total Runs", "value": str(total)},
            {"label": "Successful", "value": str(successes)},
            {"label": "Failed", "value": str(total - successes)},
            {"label": "Avg Time", "value": f"{avg_time:.1f}s"},
        ])

    # Filters
    all_pipelines = sorted(set(r.get("pipeline", "") for r in history) - {""})
    col1, col2 = st.columns(2)
    with col1:
        pipeline_filter = st.selectbox(
            "Filter by Pipeline",
            ["All Pipelines"] + [p.upper() for p in all_pipelines],
        )
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Success", "Failed"],
        )

    # Apply filters
    filtered = history
    if pipeline_filter != "All Pipelines":
        filtered = [r for r in filtered if r.get("pipeline", "").upper() == pipeline_filter]
    if status_filter == "Success":
        filtered = [r for r in filtered if r.get("success")]
    elif status_filter == "Failed":
        filtered = [r for r in filtered if not r.get("success")]

    # Table
    if filtered:
        display_data = []
        for r in reversed(filtered):
            display_data.append({
                "Pipeline": r.get("pipeline", "").upper(),
                "Client": f"{r.get('client_id', '')} -- {r.get('client_name', '')}",
                "Status": "Success" if r.get("success") else "Failed",
                "Results": r.get("result_count", 0),
                "Time (s)": f"{r.get('elapsed', 0):.1f}",
                "Timestamp": r.get("timestamp", "")[:19],
            })
        st.dataframe(display_data, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(filtered)} of {len(history)} runs")
    else:
        st.info("No runs match your filters.")

    # Export
    if history:
        csv_buffer = io.StringIO()
        fieldnames = ["pipeline", "client_id", "client_name", "success", "elapsed", "timestamp"]
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in history:
            writer.writerow(r)
        st.download_button(
            "Export as CSV",
            data=csv_buffer.getvalue(),
            file_name="run_history.csv",
            mime="text/csv",
        )


def _load_full_history() -> list[dict]:
    """Load history from session state + persisted file."""
    session_history = st.session_state.get("run_history", [])

    persisted: list[dict] = []
    if HISTORY_PATH.exists():
        try:
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                persisted = data
        except (json.JSONDecodeError, OSError):
            pass

    seen_timestamps = {r.get("timestamp") for r in persisted}
    merged = list(persisted)
    for r in session_history:
        if r.get("timestamp") not in seen_timestamps:
            merged.append(r)

    return merged
