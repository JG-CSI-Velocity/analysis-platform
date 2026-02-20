"""UAP Module Library -- browse, search, and select analysis modules."""

from __future__ import annotations

import streamlit as st

from platform_app.core.module_registry import (
    ModuleInfo,
    Product,
    get_registry,
)
from platform_app.core.templates import load_templates

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">ANALYSIS / MODULE LIBRARY</p>', unsafe_allow_html=True)
st.title("Module Library")
st.caption("Browse all available analysis modules. Select modules or load a template.")

# ---------------------------------------------------------------------------
# Search + filter bar
# ---------------------------------------------------------------------------
f1, f2, f3 = st.columns([2, 1, 1])
with f1:
    search = st.text_input(
        "Search modules",
        placeholder="e.g. competitor, cohort, revenue...",
        key="mod_search",
        label_visibility="collapsed",
    )
with f2:
    product_filter = st.selectbox(
        "Product",
        options=["All"] + [p.value.upper() for p in Product],
        key="mod_product",
    )
with f3:
    status_filter = st.selectbox(
        "Status",
        options=["All", "stable", "beta", "draft"],
        key="mod_status",
    )

# ---------------------------------------------------------------------------
# Filter registry
# ---------------------------------------------------------------------------
registry = get_registry()

filtered = registry
if product_filter != "All":
    filtered = [m for m in filtered if m.product.value == product_filter.lower()]
if status_filter != "All":
    filtered = [m for m in filtered if m.status.value == status_filter]
if search.strip():
    q = search.strip().lower()
    filtered = [
        m
        for m in filtered
        if q in m.name.lower()
        or q in m.description.lower()
        or q in m.category.lower()
        or any(q in t for t in m.tags)
    ]

# Stats
st.markdown(
    f'<p style="font-family: var(--uap-mono); font-size: 0.72rem; color: #94A3B8;">'
    f"Showing {len(filtered)} of {len(registry)} modules</p>",
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Templates section
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">SAVED TEMPLATES</p>', unsafe_allow_html=True)

templates = load_templates()
template_names = list(templates.keys())

t1, t2 = st.columns([3, 1])
with t1:
    selected_template = st.selectbox(
        "Load template",
        options=["-- Select --"] + template_names,
        key="mod_template",
        label_visibility="collapsed",
    )
with t2:
    load_btn = st.button("Load Template", key="mod_load_template", use_container_width=True)

if load_btn and selected_template != "-- Select --":
    module_keys = templates[selected_template]
    st.session_state["uap_selected_modules"] = set(module_keys)
    st.success(f"Loaded **{selected_template}** ({len(module_keys)} modules)")
    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Module grid by category
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">ALL MODULES</p>', unsafe_allow_html=True)

# Initialize selection
if "uap_selected_modules" not in st.session_state:
    st.session_state["uap_selected_modules"] = set()

selected: set[str] = st.session_state["uap_selected_modules"]

# Group by category
categories: dict[str, list[ModuleInfo]] = {}
for m in filtered:
    cat = f"{m.product.value.upper()} / {m.category}"
    categories.setdefault(cat, []).append(m)

# Product color map
_COLORS = {
    Product.ARS: "#3B82F6",
    Product.TXN: "#10B981",
    Product.TXN_V4: "#8B5CF6",
    Product.ICS: "#F59E0B",
}

for cat_name, modules in sorted(categories.items()):
    product = modules[0].product
    color = _COLORS.get(product, "#94A3B8")
    count_selected = sum(1 for m in modules if m.key in selected)

    with st.expander(
        f"{cat_name} ({len(modules)} modules"
        + (f", {count_selected} selected" if count_selected else "")
        + ")",
        expanded=False,
    ):
        # Select all in category
        cat_keys = [m.key for m in modules]
        all_in_cat = all(k in selected for k in cat_keys)

        if st.checkbox(
            f"Select all in {cat_name}",
            value=all_in_cat,
            key=f"cat_all_{cat_name}",
        ):
            selected.update(cat_keys)
        elif all_in_cat:
            selected.difference_update(cat_keys)

        for m in modules:
            c1, c2 = st.columns([1, 4])
            with c1:
                checked = st.checkbox(
                    m.name,
                    value=m.key in selected,
                    key=f"mod_{m.key}",
                    label_visibility="collapsed",
                )
                if checked:
                    selected.add(m.key)
                else:
                    selected.discard(m.key)
            with c2:
                status_badge = {
                    "stable": "uap-badge-ready",
                    "beta": "uap-badge-active",
                    "draft": "uap-badge-muted",
                }.get(m.status.value, "uap-badge-muted")

                st.markdown(
                    f'<div style="padding: 0.15rem 0;">'
                    f'<span style="font-family: var(--uap-sans); font-weight: 500; font-size: 0.88rem; color: #0F172A;">{m.name}</span>'
                    f' <span class="uap-badge {status_badge}">{m.status.value}</span>'
                    + (
                        f' <span style="font-size: 0.78rem; color: #64748B;"> -- {m.description}</span>'
                        if m.description
                        else ""
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )

st.session_state["uap_selected_modules"] = selected

# ---------------------------------------------------------------------------
# Selection summary
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">SELECTION SUMMARY</p>', unsafe_allow_html=True)

if selected:
    # Group selected by product
    by_product: dict[str, int] = {}
    for m in registry:
        if m.key in selected:
            label = m.product.value.upper()
            by_product[label] = by_product.get(label, 0) + 1

    cols = st.columns(len(by_product) + 1)
    cols[0].metric("Total Selected", len(selected))
    for i, (prod, count) in enumerate(sorted(by_product.items()), 1):
        cols[i].metric(prod, count)

    # Save as template
    with st.expander("Save selection as template", expanded=False):
        new_name = st.text_input("Template name", key="save_template_name")
        if st.button("Save", key="save_template_btn") and new_name.strip():
            from platform_app.core.templates import save_template

            save_template(new_name.strip(), sorted(selected))
            st.success(f"Saved template: **{new_name.strip()}**")
            st.rerun()
else:
    st.info("No modules selected. Browse above or load a template.")
