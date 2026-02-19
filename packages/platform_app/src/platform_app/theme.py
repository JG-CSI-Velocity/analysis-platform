"""Analysis Platform -- Custom Streamlit theme (CSS + reusable styled components)."""

from __future__ import annotations

import streamlit as st

# Brand palette
NAVY = "#1B2A4A"
NAVY_LIGHT = "#2E4057"
SLATE = "#475569"
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
SUCCESS = "#10B981"
SUCCESS_BG = "#ECFDF5"
WARNING_BG = "#FFFBEB"
SURFACE = "#F8FAFC"
BORDER = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#64748B"


def inject_theme() -> None:
    """Inject the platform custom CSS into the Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = f"""
<style>
/* Sidebar */
section[data-testid="stSidebar"] {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
    padding-top: 1rem;
}}

/* Primary buttons */
button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background: {NAVY} !important;
    border: none !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: background 0.15s ease !important;
}}
button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {{
    background: {NAVY_LIGHT} !important;
}}

/* KPI cards (metric containers) */
[data-testid="stMetric"] {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 0.75rem 1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
[data-testid="stMetricValue"] {{
    color: {NAVY} !important;
    font-weight: 700 !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.05em !important;
}}

/* Step indicator */
.ars-stepper {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 1rem 0 0.5rem 0;
    margin-bottom: 0.5rem;
}}
.ars-step {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
}}
.ars-step-circle {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    flex-shrink: 0;
    transition: all 0.2s ease;
}}
.ars-step-circle.done {{
    background: {SUCCESS};
    color: white;
}}
.ars-step-circle.active {{
    background: {NAVY};
    color: white;
    box-shadow: 0 0 0 3px rgba(27, 42, 74, 0.15);
}}
.ars-step-circle.future {{
    background: {BORDER};
    color: {TEXT_SECONDARY};
}}
.ars-step-label {{
    font-size: 0.8rem;
    font-weight: 500;
    white-space: nowrap;
}}
.ars-step-label.done {{ color: {SUCCESS}; }}
.ars-step-label.active {{ color: {NAVY}; font-weight: 700; }}
.ars-step-label.future {{ color: {TEXT_SECONDARY}; }}
.ars-step-connector {{
    width: 48px;
    height: 2px;
    margin: 0 0.25rem;
    flex-shrink: 0;
}}
.ars-step-connector.done {{ background: {SUCCESS}; }}
.ars-step-connector.future {{ background: {BORDER}; }}

/* Success banner */
.ars-success-banner {{
    background: {SUCCESS_BG};
    border: 1px solid {SUCCESS};
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    text-align: center;
}}
.ars-success-banner h3 {{
    color: #065F46;
    margin: 0 0 0.25rem 0;
    font-size: 1.15rem;
}}
.ars-success-banner p {{
    color: #047857;
    margin: 0;
    font-size: 0.9rem;
}}

/* Hide default Streamlit chrome */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
</style>
"""


def step_indicator_html(current: int, labels: list[str]) -> str:
    """Build HTML for the visual step indicator."""
    parts = []
    for i, label in enumerate(labels):
        if i < current:
            state = "done"
            icon = "&#10003;"
        elif i == current:
            state = "active"
            icon = str(i + 1)
        else:
            state = "future"
            icon = str(i + 1)

        parts.append(
            f'<div class="ars-step">'
            f'  <div class="ars-step-circle {state}">{icon}</div>'
            f'  <span class="ars-step-label {state}">{label}</span>'
            f'</div>'
        )

        if i < len(labels) - 1:
            conn_state = "done" if i < current else "future"
            parts.append(f'<div class="ars-step-connector {conn_state}"></div>')

    return f'<div class="ars-stepper">{"".join(parts)}</div>'


def success_banner(title: str, subtitle: str = "") -> None:
    """Render a styled success banner."""
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="ars-success-banner"><h3>{title}</h3>{sub}</div>',
        unsafe_allow_html=True,
    )
