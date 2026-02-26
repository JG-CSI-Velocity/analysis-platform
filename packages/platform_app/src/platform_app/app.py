"""RPE Analysis Platform v2.0 -- Streamlit entry point.

Run with: streamlit run packages/platform_app/src/platform_app/app.py
"""

from __future__ import annotations

import logging
import sys
import warnings
from pathlib import Path

import streamlit as st
from PIL import Image

from platform_app.brand import PAGE_TITLE, TAGLINE

# ---------------------------------------------------------------------------
# File logging -- captures ALL output to logs/app.log so you never lose it
# ---------------------------------------------------------------------------
_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "app.log"

# Configure root logger to write to file + stderr
_root = logging.getLogger()
if not any(
    isinstance(h, logging.FileHandler) and getattr(h, "_uap_marker", False) for h in _root.handlers
):
    _fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    _fh._uap_marker = True  # type: ignore[attr-defined]
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _root.addHandler(_fh)
    _root.setLevel(logging.DEBUG)

    # Terminal output -- INFO+ so pipelines are visible in the console
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.INFO)
    _sh.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _root.addHandler(_sh)

    # Also capture uncaught exceptions to the log file
    def _exception_hook(exc_type, exc_value, exc_tb):
        logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _exception_hook

# Suppress PIL DecompressionBombWarning globally (large chart PNGs are expected)
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)

logging.getLogger("platform_app").info("App startup -- logging to %s", _LOG_FILE)

st.set_page_config(
    page_title=PAGE_TITLE,
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
    --uap-accent: #16A34A;
    --uap-accent-dim: #15803D;
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
    background: rgba(22, 163, 74, 0.15) !important;
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

/* Progress bar -- only color the fill bar, not the text label */
div[data-testid="stProgress"] [role="progressbar"] {
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

/* ---- Executive Run Dashboard ---- */

/* Command Center panel */
.uap-command-center {
    background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
    border-radius: 8px;
    padding: 1.5rem 2rem;
    margin: 0.5rem 0 1rem;
}
.uap-command-center .cc-label {
    font-family: var(--uap-mono);
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #64748B;
    margin: 0 0 0.15rem;
}
.uap-command-center .cc-value {
    font-family: var(--uap-sans);
    font-size: 1.5rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.2;
}
.uap-command-center .cc-value-sm {
    font-family: var(--uap-sans);
    font-size: 1rem;
    font-weight: 600;
    color: #CBD5E1;
    line-height: 1.2;
}
.uap-command-center .cc-sub {
    font-family: var(--uap-mono);
    font-size: 0.68rem;
    color: #475569;
    margin-top: 0.1rem;
}

/* Config grid */
.uap-cfg-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 0.75rem;
    margin: 0.5rem 0;
}
.uap-cfg-item {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 0.6rem 0.8rem;
}
.uap-cfg-item .cfg-label {
    font-family: var(--uap-mono);
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #94A3B8;
    margin: 0 0 0.15rem;
}
.uap-cfg-item .cfg-val {
    font-family: var(--uap-sans);
    font-size: 0.85rem;
    font-weight: 600;
    color: #1E293B;
}

/* Code pills for status/product codes */
.uap-pill {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-family: var(--uap-mono);
    font-size: 0.7rem;
    font-weight: 500;
    margin: 1px;
    background: #E2E8F0;
    color: #334155;
}
.uap-pill-green { background: #DCFCE7; color: #166534; }
.uap-pill-red { background: #FEE2E2; color: #991B1B; }
.uap-pill-blue { background: #DBEAFE; color: #1E40AF; }

/* Execution tracker */
.uap-exec-track {
    background: #FAFBFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin: 0.5rem 0;
}
.uap-exec-row {
    display: flex;
    align-items: center;
    padding: 0.35rem 0;
    border-bottom: 1px solid #F1F5F9;
}
.uap-exec-row:last-child { border-bottom: none; }
.uap-exec-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 0.6rem;
    flex-shrink: 0;
}
.dot-pending { background: #CBD5E1; }
.dot-running { background: #F59E0B; animation: pulse 1s infinite; }
.dot-done { background: #16A34A; }
.dot-fail { background: #DC2626; }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
.uap-exec-name {
    font-family: var(--uap-sans);
    font-size: 0.85rem;
    font-weight: 500;
    color: #334155;
    flex: 1;
}
.uap-exec-time {
    font-family: var(--uap-mono);
    font-size: 0.72rem;
    color: #94A3B8;
    margin-right: 1.5rem;
}

/* Result cards */
.uap-result-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 1.25rem;
    text-align: center;
}
.uap-result-card .rc-num {
    font-family: var(--uap-sans);
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
}
.uap-result-card .rc-label {
    font-family: var(--uap-mono);
    font-size: 0.62rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94A3B8;
    margin-top: 0.3rem;
}

/* Download cards */
.uap-dl-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    margin: 0.35rem 0;
    transition: border-color 0.15s;
}
.uap-dl-card:hover { border-color: #16A34A; }
.uap-dl-icon {
    width: 36px; height: 36px;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
    font-family: var(--uap-mono);
}
.dl-pptx { background: #FEF3C7; color: #92400E; }
.dl-xlsx { background: #DCFCE7; color: #166534; }
.uap-dl-info {
    flex: 1;
}
.uap-dl-info .dl-name {
    font-family: var(--uap-mono);
    font-size: 0.8rem;
    font-weight: 500;
    color: #1E293B;
}
.uap-dl-info .dl-path {
    font-family: var(--uap-mono);
    font-size: 0.65rem;
    color: #94A3B8;
}

/* Progress bar override -- only the fill bar, not text label */
div[data-testid="stProgress"] [role="progressbar"] {
    background-color: #16A34A !important;
}

/* Run button -- make it pop */
.uap-run-btn button {
    background: linear-gradient(135deg, #16A34A 0%, #15803D 100%) !important;
    border: none !important;
    font-family: var(--uap-sans) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em;
    padding: 0.65rem 2rem !important;
    border-radius: 6px !important;
    box-shadow: 0 2px 8px rgba(22, 163, 74, 0.25);
    transition: all 0.2s;
}
.uap-run-btn button:hover:not(:disabled) {
    background: linear-gradient(135deg, #15803D 0%, #166534 100%) !important;
    box-shadow: 0 4px 12px rgba(22, 163, 74, 0.35) !important;
    transform: translateY(-1px);
}
.uap-run-btn button:disabled {
    background: #94A3B8 !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
    opacity: 0.7;
    transform: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
home = st.Page("pages/home.py", title="Run Analysis", icon=":material/play_circle:", default=True)

ars_page = st.Page("pages/pipeline_ars.py", title="ARS Analysis", icon=":material/analytics:")
ics_page = st.Page(
    "pages/pipeline_ics.py", title="ICS Analysis", icon=":material/account_balance:"
)
txn_page = st.Page("pages/pipeline_txn.py", title="TXN Analysis", icon=":material/receipt_long:")
attrition_page = st.Page(
    "pages/pipeline_attrition.py", title="Attrition", icon=":material/trending_down:"
)

outputs = st.Page("pages/outputs.py", title="View Outputs", icon=":material/download:")
history = st.Page("pages/run_history.py", title="Run History", icon=":material/history:")

workspace = st.Page("pages/workspace.py", title="Workspace", icon=":material/folder_open:")
data_ingest = st.Page(
    "pages/data_ingestion.py", title="Data Ingestion", icon=":material/upload_file:"
)
modules = st.Page("pages/module_library.py", title="Module Library", icon=":material/apps:")
run_page = st.Page("pages/run_analysis.py", title="Run (Advanced)", icon=":material/tune:")
batch = st.Page("pages/batch_workflow.py", title="Batch Run", icon=":material/playlist_play:")
logs = st.Page("pages/logs.py", title="View Logs", icon=":material/description:")

pg = st.navigation(
    {
        "": [home],
        "PIPELINES": [ars_page, ics_page, txn_page, attrition_page],
        "OUTPUTS": [outputs, history],
        "ADVANCED": [workspace, data_ingest, modules, run_page, batch],
        "DIAGNOSTICS": [logs],
    }
)

# Sidebar footer
with st.sidebar:
    st.divider()
    st.markdown(f'<p class="uap-version">{TAGLINE}</p>', unsafe_allow_html=True)

pg.run()
