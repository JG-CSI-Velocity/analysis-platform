"""Streamlit entry point for the unified analysis platform.

Run with: streamlit run packages/platform_app/src/platform_app/app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Analysis Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
section[data-testid="stSidebar"] { background: #f8f9fa; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

st.title("Unified Analysis Platform")
st.markdown("Select a pipeline from the sidebar to get started.")

st.markdown("""
### Available Pipelines

- **ARS Analysis** -- OD/NSF analysis from ODDD Excel files
- **Transaction Analysis (Base)** -- Debit card M1-M10 modules
- **Transaction Analysis (V4)** -- V4 storyline analytics (S0-S9)
- **ICS Analysis** -- Instant Card Services portfolio analysis
""")
