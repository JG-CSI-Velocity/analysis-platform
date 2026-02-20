"""UAP Module Library -- browse, search, and select analysis modules."""

from __future__ import annotations

import streamlit as st

from platform_app.core.module_registry import (
    ModuleInfo,
    ModuleStatus,
    Product,
    get_categories,
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
f1, f2, f3, f4 = st.columns([3, 1, 1, 1])
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
    # Build category list based on product filter
    if product_filter != "All":
        _prod = Product(product_filter.lower())
        _cats = get_categories(_prod)
    else:
        _cats = get_categories()
    category_filter = st.selectbox(
        "Category",
        options=["All"] + _cats,
        key="mod_category",
    )
with f4:
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
if category_filter != "All":
    filtered = [m for m in filtered if m.category == category_filter]
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
        or q in m.key.lower()
        or any(q in t for t in m.tags)
    ]

# Product color map
_COLORS = {
    Product.ARS: "#3B82F6",
    Product.TXN: "#10B981",
    Product.TXN_V4: "#8B5CF6",
    Product.ICS: "#F59E0B",
}

# Status config
_STATUS_STYLE = {
    ModuleStatus.STABLE: ("BUILT", "#166534", "#DCFCE7"),
    ModuleStatus.BETA: ("BETA", "#1E40AF", "#DBEAFE"),
    ModuleStatus.DRAFT: ("PLANNED", "#991B1B", "#FEE2E2"),
}

# Filter stats
stable_count = sum(1 for m in filtered if m.status == ModuleStatus.STABLE)
beta_count = sum(1 for m in filtered if m.status == ModuleStatus.BETA)
draft_count = sum(1 for m in filtered if m.status == ModuleStatus.DRAFT)

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Showing", f"{len(filtered)} / {len(registry)}")
sc2.metric("Built", stable_count)
sc3.metric("Beta", beta_count)
sc4.metric("Planned", draft_count)

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
# Module grid -- visible cards, no hidden expanders
# ---------------------------------------------------------------------------
if "uap_selected_modules" not in st.session_state:
    st.session_state["uap_selected_modules"] = set()

selected: set[str] = st.session_state["uap_selected_modules"]

# Group by product then category
groups: dict[str, list[ModuleInfo]] = {}
for m in filtered:
    cat = f"{m.product.value.upper()} / {m.category}"
    groups.setdefault(cat, []).append(m)

if not filtered:
    st.warning("No modules match your filters. Try broadening your search.")
    st.stop()


def _render_module_row(m: ModuleInfo, sel: set[str]) -> None:
    """Render one module as a visible row with checkbox + info."""
    status_label, status_fg, status_bg = _STATUS_STYLE.get(m.status, ("?", "#64748B", "#F1F5F9"))
    color = _COLORS.get(m.product, "#94A3B8")

    c_check, c_info = st.columns([0.4, 5])
    with c_check:
        checked = st.checkbox(
            m.name,
            value=m.key in sel,
            key=f"mod_{m.key}",
            label_visibility="collapsed",
        )
        if checked:
            sel.add(m.key)
        else:
            sel.discard(m.key)
    with c_info:
        desc_html = (
            f' <span style="font-size:0.78rem;color:#64748B;"> -- {m.description}</span>'
            if m.description
            else ""
        )
        output_badges = " ".join(
            f'<span style="font-family:var(--uap-mono);font-size:0.6rem;'
            f"background:#F1F5F9;color:#64748B;padding:1px 5px;border-radius:2px;"
            f'margin-left:4px;">{o}</span>'
            for o in m.output_types
        )

        # Dependency badge
        dep_html = ""
        if m.depends_on:
            dep_count = len(m.depends_on)
            dep_html = (
                f'<span style="font-family:var(--uap-mono);font-size:0.6rem;'
                f"background:#FEF3C7;color:#92400E;padding:1px 5px;border-radius:2px;"
                f'margin-left:4px;">needs {dep_count}</span>'
            )

        # Run order badge
        order_html = ""
        if m.run_order == 99:
            order_html = (
                '<span style="font-family:var(--uap-mono);font-size:0.6rem;'
                "background:#E0E7FF;color:#3730A3;padding:1px 5px;border-radius:2px;"
                'margin-left:4px;">runs last</span>'
            )

        st.markdown(
            f'<div style="display:flex;align-items:center;padding:0.1rem 0;flex-wrap:wrap;">'
            f'<span style="font-family:var(--uap-sans);font-weight:500;font-size:0.88rem;'
            f'color:#0F172A;">{m.name}</span>'
            f'<span style="display:inline-block;padding:1px 6px;border-radius:2px;'
            f"font-family:var(--uap-mono);font-size:0.62rem;font-weight:600;"
            f"background:{status_bg};color:{status_fg};"
            f'margin-left:8px;letter-spacing:0.04em;">{status_label}</span>'
            f"{dep_html}{order_html}{output_badges}"
            f"{desc_html}"
            f"</div>",
            unsafe_allow_html=True,
        )


for cat_name, modules in sorted(groups.items()):
    product = modules[0].product
    color = _COLORS.get(product, "#94A3B8")
    count_selected = sum(1 for m in modules if m.key in selected)
    total_in_cat = len(modules)

    # Category header with select-all
    st.markdown(
        f'<div style="display:flex;align-items:center;margin-top:1rem;margin-bottom:0.25rem;">'
        f'<span style="display:inline-block;width:4px;height:16px;background:{color};'
        f'border-radius:2px;margin-right:8px;"></span>'
        f'<span style="font-family:var(--uap-mono);font-size:0.7rem;font-weight:600;'
        f'letter-spacing:0.06em;color:#475569;">{cat_name}</span>'
        f'<span style="font-family:var(--uap-mono);font-size:0.65rem;color:#94A3B8;'
        f'margin-left:8px;">{count_selected}/{total_in_cat} selected</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    # Select all toggle
    cat_keys = [m.key for m in modules]
    all_in_cat = all(k in selected for k in cat_keys)
    select_all = st.checkbox(
        f"Select all {cat_name}",
        value=all_in_cat,
        key=f"cat_all_{cat_name}",
    )
    if select_all and not all_in_cat:
        selected.update(cat_keys)
    elif not select_all and all_in_cat:
        selected.difference_update(cat_keys)

    # Module rows
    for m in modules:
        _render_module_row(m, selected)

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

    # Note about pipeline execution
    st.info(
        "Pipelines run all modules for the selected product. "
        "Individual module selection will be available in a future release."
    )

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
