"""Analysis Platform -- Streamlit multi-page application.

Run with: streamlit run packages/platform_app/src/platform_app/app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Analysis Platform",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from platform_app.pages.config_page import render as config_render  # noqa: E402
from platform_app.pages.dashboard import render as dashboard_render  # noqa: E402
from platform_app.pages.history import render as history_render  # noqa: E402
from platform_app.pages.results_viewer import render as results_render  # noqa: E402
from platform_app.pages.run_analysis import render as run_render  # noqa: E402
from platform_app.theme import inject_theme  # noqa: E402

inject_theme()

# Define pages
dashboard_page = st.Page(
    dashboard_render,
    title="Dashboard",
    icon=":material/dashboard:",
    url_path="dashboard",
)
run_page = st.Page(
    run_render,
    title="Run Analysis",
    icon=":material/play_circle:",
    url_path="run",
    default=True,
)
results_page = st.Page(
    results_render,
    title="View Results",
    icon=":material/monitoring:",
    url_path="results",
)
history_page = st.Page(
    history_render,
    title="Run History",
    icon=":material/history:",
    url_path="history",
)
config_page = st.Page(
    config_render,
    title="Client Config",
    icon=":material/settings:",
    url_path="config",
)

# Store page objects for cross-page navigation
st.session_state["_pages"] = {
    "dashboard": dashboard_page,
    "run": run_page,
    "results": results_page,
    "history": history_page,
    "config": config_page,
}

if "run_history" not in st.session_state:
    st.session_state["run_history"] = []

pg = st.navigation(
    {
        "Analysis": [dashboard_page, run_page, results_page],
        "Management": [history_page, config_page],
    }
)

with st.sidebar:
    st.markdown("---")
    st.caption("Analysis Platform v2.0")

pg.run()
