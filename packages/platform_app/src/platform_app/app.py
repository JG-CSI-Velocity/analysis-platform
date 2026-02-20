"""Unified Analysis Platform v2.0 -- Streamlit entry point.

Run with: streamlit run packages/platform_app/src/platform_app/app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="UAP",
    page_icon=":material/terminal:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Industrial theme -- dark sidebar, monospace accents, dense layout
# Aesthetic: Bloomberg terminal meets modern data platform
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

/* Root variables */
:root {
    --uap-ink: #0F172A;
    --uap-slate: #1E293B;
    --uap-dim: #475569;
    --uap-muted: #94A3B8;
    --uap-surface: #F8FAFC;
    --uap-border: #E2E8F0;
    --uap-accent: #3B82F6;
    --uap-accent-dim: #1D4ED8;
    --uap-success: #10B981;
    --uap-warn: #F59E0B;
    --uap-error: #EF4444;
    --uap-mono: 'JetBrains Mono', 'SF Mono', 'Fira Code', monospace;
    --uap-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: var(--uap-ink) !important;
    border-right: 1px solid #1E293B;
}
section[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}
section[data-testid="stSidebar"] .stMarkdown p {
    font-family: var(--uap-mono);
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--uap-muted) !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
}

/* Nav items */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a {
    font-family: var(--uap-sans) !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a[aria-current="page"] {
    background: rgba(59, 130, 246, 0.15) !important;
    border-left: 2px solid var(--uap-accent) !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a:hover {
    background: rgba(255, 255, 255, 0.05) !important;
}

/* Hide defaults */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* Main content */
.main .block-container {
    padding-top: 2rem;
}

/* Typography */
h1, h2, h3 {
    font-family: var(--uap-sans) !important;
    color: var(--uap-ink) !important;
}
h1 { font-weight: 700 !important; font-size: 1.6rem !important; letter-spacing: -0.02em; }
h2 { font-weight: 600 !important; font-size: 1.2rem !important; }
h3 { font-weight: 600 !important; font-size: 1.0rem !important; }

/* Mono labels */
.uap-label {
    font-family: var(--uap-mono);
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--uap-muted);
    margin-bottom: 0.25rem;
}

/* Status indicators */
.uap-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-family: var(--uap-mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.uap-badge-ready { background: #DCFCE7; color: #166534; }
.uap-badge-active { background: #DBEAFE; color: #1E40AF; }
.uap-badge-error { background: #FEE2E2; color: #991B1B; }
.uap-badge-muted { background: #F1F5F9; color: #64748B; }

/* Cards */
.uap-card {
    border: 1px solid var(--uap-border);
    border-radius: 6px;
    padding: 1.25rem;
    background: #FFFFFF;
    transition: border-color 0.15s;
}
.uap-card:hover {
    border-color: var(--uap-accent);
}
.uap-card h4 {
    font-family: var(--uap-sans);
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--uap-ink);
    margin: 0 0 0.35rem 0;
}
.uap-card p {
    font-family: var(--uap-sans);
    font-size: 0.82rem;
    color: var(--uap-dim);
    line-height: 1.45;
    margin: 0;
}

/* Metric overrides */
div[data-testid="stMetric"] {
    background: var(--uap-surface);
    border: 1px solid var(--uap-border);
    border-radius: 6px;
    padding: 0.75rem 1rem !important;
}
div[data-testid="stMetric"] label {
    font-family: var(--uap-mono) !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: var(--uap-muted) !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-family: var(--uap-sans) !important;
    font-weight: 700 !important;
    color: var(--uap-ink) !important;
}

/* Data tables */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--uap-border);
    border-radius: 6px;
}

/* Forms */
.stTextInput input, .stSelectbox select {
    font-family: var(--uap-sans) !important;
    font-size: 0.88rem !important;
}

/* Buttons */
.stButton > button[kind="primary"] {
    background: var(--uap-accent) !important;
    border: none !important;
    font-family: var(--uap-sans) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.01em;
}
.stButton > button[kind="primary"]:hover {
    background: var(--uap-accent-dim) !important;
}

/* Progress bar */
div[data-testid="stProgress"] > div > div {
    background-color: var(--uap-accent) !important;
}

/* Dividers */
hr {
    border-color: var(--uap-border) !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-family: var(--uap-sans) !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}

/* Version watermark */
.uap-version {
    font-family: var(--uap-mono);
    font-size: 0.62rem;
    color: #475569;
    letter-spacing: 0.05em;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
home = st.Page("pages/home.py", title="Home", icon=":material/terminal:", default=True)

workspace = st.Page("pages/workspace.py", title="Workspace", icon=":material/folder_open:")
data_ingest = st.Page(
    "pages/data_ingestion.py", title="Data Ingestion", icon=":material/upload_file:"
)

modules = st.Page("pages/module_library.py", title="Module Library", icon=":material/apps:")
run_page = st.Page("pages/run_analysis.py", title="Run Analysis", icon=":material/play_circle:")
batch = st.Page("pages/batch_workflow.py", title="Batch Run", icon=":material/playlist_play:")

outputs = st.Page("pages/outputs.py", title="View Outputs", icon=":material/download:")
history = st.Page("pages/run_history.py", title="Run History", icon=":material/history:")

pg = st.navigation(
    {
        "": [home],
        "DATA": [workspace, data_ingest],
        "ANALYSIS": [modules, run_page, batch],
        "OUTPUTS": [outputs, history],
    }
)

# Sidebar footer
with st.sidebar:
    st.divider()
    st.markdown('<p class="uap-version">UAP v2.0 // ANALYSIS PLATFORM</p>', unsafe_allow_html=True)

pg.run()
