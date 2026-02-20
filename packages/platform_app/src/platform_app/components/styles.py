"""Shared CSS styles injected into all pipeline pages."""

from __future__ import annotations

import streamlit as st

PAGE_CSS = """
<style>
/* Pipeline header accent bar */
.pipeline-header {
    border-left: 3px solid #2E4057;
    padding-left: 0.75rem;
    margin-bottom: 1rem;
}
.pipeline-header h2 {
    margin: 0;
    font-size: 1.4rem;
    color: #2E4057;
}
.pipeline-header p {
    margin: 0.15rem 0 0 0;
    font-size: 0.88rem;
    color: #64748B;
}

/* Sidebar section labels */
.sidebar-section {
    font-size: 0.72rem;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0.75rem 0 0.35rem 0;
}

/* Status chip */
.status-chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}
.status-ready { background: #D1FAE5; color: #065F46; }
.status-running { background: #DBEAFE; color: #1E40AF; }
.status-done { background: #F0FDF4; color: #166534; }
.status-error { background: #FEE2E2; color: #991B1B; }

/* File indicator */
.file-indicator {
    font-size: 0.82rem;
    color: #64748B;
    padding: 0.3rem 0;
}
.file-indicator code {
    background: #F1F5F9;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.78rem;
}
</style>
"""


def inject_page_css() -> None:
    """Inject shared page CSS. Call once at top of each pipeline page."""
    st.markdown(PAGE_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str) -> None:
    """Render a styled pipeline header with accent bar."""
    st.markdown(
        f'<div class="pipeline-header"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
