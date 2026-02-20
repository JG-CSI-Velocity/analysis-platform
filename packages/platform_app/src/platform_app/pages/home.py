"""UAP Home -- system dashboard and quick launch."""

from __future__ import annotations

from datetime import date

import streamlit as st

from platform_app.core.module_registry import Product, get_modules_by_product, get_registry
from platform_app.core.run_logger import load_history
from platform_app.core.templates import load_templates

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    '<p class="uap-label">UNIFIED ANALYSIS PLATFORM</p>',
    unsafe_allow_html=True,
)
st.title("Dashboard")

# ---------------------------------------------------------------------------
# System metrics
# ---------------------------------------------------------------------------
registry = get_registry()
templates = load_templates()
history = load_history(limit=10)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Modules", len(registry))
c2.metric("Products", len(Product))
c3.metric("Templates", len(templates))
c4.metric("Recent Runs", len(history))
c5.metric("Date", date.today().strftime("%b %d"))

st.divider()

# ---------------------------------------------------------------------------
# Product breakdown
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">PRODUCT COVERAGE</p>', unsafe_allow_html=True)

cols = st.columns(4)
product_info = [
    (Product.ARS, "ARS", "OD/NSF portfolio analysis", "#3B82F6"),
    (Product.TXN, "Transaction", "Debit card M1-M10", "#10B981"),
    (Product.TXN_V4, "Transaction V4", "Storyline analytics S0-S9", "#8B5CF6"),
    (Product.ICS, "ICS", "Instant Card Services", "#F59E0B"),
]

for col, (product, label, desc, color) in zip(cols, product_info):
    modules_list = get_modules_by_product(product)
    categories = {m.category for m in modules_list}
    with col:
        st.markdown(
            f"""<div class="uap-card" style="border-top: 3px solid {color};">
            <h4>{label}</h4>
            <p>{desc}</p>
            <p style="margin-top: 0.5rem; font-family: var(--uap-mono); font-size: 0.72rem; color: #64748B;">
                {len(modules_list)} modules / {len(categories)} categories
            </p>
            </div>""",
            unsafe_allow_html=True,
        )

st.divider()

# ---------------------------------------------------------------------------
# Quick start
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">WORKFLOW</p>', unsafe_allow_html=True)

steps = [
    ("01", "Workspace", "Select CSM folder + client"),
    ("02", "Ingest", "Upload or auto-detect data files"),
    ("03", "Configure", "Choose modules or load a template"),
    ("04", "Execute", "Run analysis with progress tracking"),
    ("05", "Export", "Download Excel, PowerPoint, reports"),
]

step_cols = st.columns(5)
for col, (num, title, desc) in zip(step_cols, steps):
    with col:
        st.markdown(
            f"""<div style="text-align: center; padding: 0.5rem;">
            <span style="font-family: var(--uap-mono); font-size: 1.4rem; font-weight: 700; color: #3B82F6;">{num}</span>
            <p style="font-family: var(--uap-sans); font-weight: 600; font-size: 0.85rem; color: #0F172A; margin: 0.25rem 0 0.15rem;">{title}</p>
            <p style="font-family: var(--uap-sans); font-size: 0.75rem; color: #64748B; margin: 0;">{desc}</p>
            </div>""",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Recent runs (if any)
# ---------------------------------------------------------------------------
if history:
    st.divider()
    st.markdown('<p class="uap-label">RECENT RUNS</p>', unsafe_allow_html=True)

    for record in history[:5]:
        status_class = "uap-badge-ready" if record.status == "success" else "uap-badge-error"
        st.markdown(
            f"""<div style="display: flex; align-items: center; padding: 0.4rem 0; border-bottom: 1px solid #F1F5F9;">
            <span class="uap-badge {status_class}" style="margin-right: 0.75rem;">{record.status.upper()}</span>
            <span style="font-family: var(--uap-sans); font-size: 0.85rem; font-weight: 500; color: #0F172A; min-width: 120px;">{record.client_id} - {record.pipeline}</span>
            <span style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8; margin-left: auto;">{record.timestamp} // {record.runtime_seconds:.1f}s</span>
            </div>""",
            unsafe_allow_html=True,
        )
