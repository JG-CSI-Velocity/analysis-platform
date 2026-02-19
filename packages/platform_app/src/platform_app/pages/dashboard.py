"""Dashboard page -- KPI overview and quick actions for all pipelines."""

from __future__ import annotations

import logging

import streamlit as st

from platform_app.components import kpi_row

logger = logging.getLogger(__name__)


def _get_page(name: str):
    return st.session_state.get("_pages", {}).get(name)


def render() -> None:
    try:
        _render_inner()
    except Exception:
        st.error("Something went wrong loading the dashboard. Please try refreshing.")
        logger.exception("Unhandled error in dashboard")


def _render_inner() -> None:
    st.title("Analysis Platform")
    st.caption("CSI Velocity -- ARS, Transaction, and ICS Pipelines")

    # Quick-action cards
    c1, c2, c3 = st.columns(3)
    run_pg = _get_page("run")
    results_pg = _get_page("results")
    config_pg = _get_page("config")

    with c1:
        with st.container(border=True):
            st.markdown(":material/play_circle: **Run Analysis**")
            st.caption("Start a single or batch analysis run")
            if run_pg and st.button("Go", key="dash_run", type="primary", use_container_width=True):
                st.switch_page(run_pg)

    with c2:
        with st.container(border=True):
            st.markdown(":material/monitoring: **View Results**")
            st.caption("Download Excel, PPTX, and browse charts")
            if results_pg and st.button("Go", key="dash_results", use_container_width=True):
                st.switch_page(results_pg)

    with c3:
        with st.container(border=True):
            st.markdown(":material/settings: **Client Config**")
            st.caption("Manage client settings and CSM assignments")
            if config_pg and st.button("Go", key="dash_config", use_container_width=True):
                st.switch_page(config_pg)

    # Session KPIs
    history = st.session_state.get("run_history", [])
    total_runs = len(history)
    success_runs = sum(1 for r in history if r.get("success"))

    pipeline_counts: dict[str, int] = {}
    for r in history:
        p = r.get("pipeline", "unknown")
        pipeline_counts[p] = pipeline_counts.get(p, 0) + 1

    kpi_row([
        {"label": "Runs This Session", "value": str(total_runs)},
        {"label": "Successful", "value": str(success_runs)},
        {"label": "ARS Runs", "value": str(pipeline_counts.get("ars", 0))},
        {"label": "TXN/ICS Runs", "value": str(
            pipeline_counts.get("txn", 0)
            + pipeline_counts.get("txn_v4", 0)
            + pipeline_counts.get("ics", 0)
        )},
    ])

    # Recent runs table
    if history:
        st.markdown("### Recent Runs")
        display_data = []
        for r in reversed(history[-10:]):
            display_data.append({
                "Pipeline": r.get("pipeline", "").upper(),
                "Client": f"{r.get('client_id', '')} -- {r.get('client_name', '')}",
                "Status": "Success" if r.get("success") else "Failed",
                "Time (s)": f"{r.get('elapsed', 0):.1f}",
                "Timestamp": r.get("timestamp", "")[:16],
            })
        st.dataframe(display_data, use_container_width=True, hide_index=True)
