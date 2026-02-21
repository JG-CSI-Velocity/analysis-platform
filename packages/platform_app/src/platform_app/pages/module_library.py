"""UAP Module Library -- browse, search, and select analysis modules."""

from __future__ import annotations

import streamlit as st

from platform_app.core.module_registry import (
    ModuleInfo,
    ModuleStatus,
    Product,
    get_registry,
)
from platform_app.core.templates import load_templates

# ---------------------------------------------------------------------------
# State init
# ---------------------------------------------------------------------------
if "uap_selected_modules" not in st.session_state:
    st.session_state["uap_selected_modules"] = set()

selected: set[str] = st.session_state["uap_selected_modules"]
registry = get_registry()
ALL_MOD_KEYS = [m.key for m in registry]


def _sync_checkboxes(keys: list[str], value: bool) -> None:
    """Sync checkbox widget keys to match bulk selection state.

    Streamlit checkboxes store their own state under their widget key.
    After first render, the `value=` param is ignored in favor of the
    stored widget state. So bulk actions must explicitly set widget keys
    before calling st.rerun().
    """
    for k in keys:
        st.session_state[f"mod_{k}"] = value


def _select_keys(keys: list[str]) -> None:
    """Bulk-select module keys and sync checkbox widgets."""
    selected.update(keys)
    st.session_state["uap_selected_modules"] = selected
    _sync_checkboxes(keys, True)
    st.rerun()


def _deselect_keys(keys: list[str]) -> None:
    """Bulk-deselect module keys and sync checkbox widgets."""
    selected.difference_update(keys)
    st.session_state["uap_selected_modules"] = selected
    _sync_checkboxes(keys, False)
    st.rerun()


# ---------------------------------------------------------------------------
# Scoped CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
.prod-card {
    border: 2px solid var(--uap-border);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    background: #FFFFFF;
    transition: all 0.15s ease;
    text-align: center;
}
.prod-card.active { border-color: var(--uap-accent); background: #EFF6FF; }
.prod-card .prod-name {
    font-family: var(--uap-mono);
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin-bottom: 2px;
}
.prod-card .prod-count {
    font-family: var(--uap-sans);
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--uap-ink);
    line-height: 1.1;
}
.prod-card .prod-sub {
    font-family: var(--uap-mono);
    font-size: 0.62rem;
    color: var(--uap-muted);
    letter-spacing: 0.04em;
}
.cat-header {
    display: flex;
    align-items: center;
    padding: 0.6rem 0 0.3rem 0;
    border-bottom: 1px solid var(--uap-border);
    margin-bottom: 0.4rem;
}
.cat-bar {
    width: 4px; height: 18px; border-radius: 2px;
    margin-right: 10px; flex-shrink: 0;
}
.cat-label {
    font-family: var(--uap-mono);
    font-size: 0.72rem; font-weight: 600;
    letter-spacing: 0.06em; color: var(--uap-dim);
}
.cat-count {
    font-family: var(--uap-mono);
    font-size: 0.62rem; color: var(--uap-muted); margin-left: auto;
}
.mod-row {
    display: flex; align-items: center;
    padding: 0.25rem 0 0.25rem 14px; gap: 8px; flex-wrap: wrap;
}
.mod-name {
    font-family: var(--uap-sans); font-weight: 500;
    font-size: 0.86rem; color: var(--uap-ink);
}
.mod-desc { font-family: var(--uap-sans); font-size: 0.76rem; color: #94A3B8; }
.mod-tag {
    display: inline-block; font-family: var(--uap-mono);
    font-size: 0.58rem; font-weight: 600; letter-spacing: 0.04em;
    padding: 1px 6px; border-radius: 2px;
}
.tag-built { background: #DCFCE7; color: #166534; }
.tag-beta { background: #DBEAFE; color: #1E40AF; }
.tag-draft { background: #FEE2E2; color: #991B1B; }
.tag-dep { background: #FEF3C7; color: #92400E; }
.tag-last { background: #E0E7FF; color: #3730A3; }
.tag-out { background: #F1F5F9; color: #64748B; }
.sel-bar {
    background: var(--uap-ink); color: #CBD5E1;
    padding: 0.6rem 1.2rem; border-radius: 8px; margin-top: 1rem;
    display: flex; align-items: center; justify-content: space-between;
}
.sel-bar .sel-count {
    font-family: var(--uap-mono); font-size: 0.82rem;
    font-weight: 600; color: #FFFFFF;
}
.sel-bar .sel-detail {
    font-family: var(--uap-mono); font-size: 0.65rem; color: #94A3B8;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">ANALYSIS / MODULE LIBRARY</p>', unsafe_allow_html=True)
st.title("Module Library")

# ---------------------------------------------------------------------------
# Product config
# ---------------------------------------------------------------------------
_PROD_COLORS = {
    Product.ARS: "#3B82F6",
    Product.TXN: "#10B981",
    Product.ICS: "#F59E0B",
}
_PROD_LABELS = {
    Product.ARS: ("ARS", "Account Review Suite"),
    Product.TXN: ("TXN", "Transaction Analysis"),
    Product.ICS: ("ICS", "ICS Toolkit"),
}
_STATUS_TAG = {
    ModuleStatus.STABLE: ("BUILT", "tag-built"),
    ModuleStatus.BETA: ("BETA", "tag-beta"),
    ModuleStatus.DRAFT: ("PLANNED", "tag-draft"),
}

_prod_modules = {p: [m for m in registry if m.product == p] for p in Product}
_prod_selected = {p: sum(1 for m in mods if m.key in selected) for p, mods in _prod_modules.items()}

# ---------------------------------------------------------------------------
# Quick-select: product cards with toggle button
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">QUICK SELECT</p>', unsafe_allow_html=True)

qc1, qc2, qc3 = st.columns(3)

for col, product in zip([qc1, qc2, qc3], Product):
    label, subtitle = _PROD_LABELS[product]
    color = _PROD_COLORS[product]
    total = len(_prod_modules[product])
    sel_ct = _prod_selected[product]
    all_selected = sel_ct == total
    prod_keys = [m.key for m in _prod_modules[product]]

    with col:
        active_cls = "active" if sel_ct > 0 else ""
        st.markdown(
            f'<div class="prod-card {active_cls}" style="border-color: {color if sel_ct > 0 else ""}">'
            f'<div class="prod-name" style="color: {color}">{label}</div>'
            f'<div class="prod-count">{sel_ct}<span style="font-size:0.8rem;font-weight:400;color:#94A3B8;">/{total}</span></div>'
            f'<div class="prod-sub">{subtitle}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        # Single toggle: select all / deselect all
        if all_selected:
            if st.button(
                f"Deselect {label}",
                key=f"prod_toggle_{product.value}",
                use_container_width=True,
            ):
                _deselect_keys(prod_keys)
        elif sel_ct > 0:
            # Partial -- show "Select All" to fill remaining
            if st.button(
                f"Select All {label}",
                key=f"prod_toggle_{product.value}",
                use_container_width=True,
            ):
                _select_keys(prod_keys)
        else:
            if st.button(
                f"Select All {label}",
                key=f"prod_toggle_{product.value}",
                use_container_width=True,
            ):
                _select_keys(prod_keys)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">TEMPLATES</p>', unsafe_allow_html=True)

templates = load_templates()
template_names = list(templates.keys())

tc1, tc2, tc3 = st.columns([3, 1, 1])
with tc1:
    selected_template = st.selectbox(
        "Load template",
        options=["-- Select a template --"] + template_names,
        key="mod_template",
        label_visibility="collapsed",
    )
with tc2:
    if st.button("Load", key="mod_load_template", use_container_width=True):
        if selected_template != "-- Select a template --":
            new_keys = templates[selected_template]
            st.session_state["uap_selected_modules"] = set(new_keys)
            # Sync all checkboxes: turn on loaded, turn off the rest
            _sync_checkboxes(ALL_MOD_KEYS, False)
            _sync_checkboxes(new_keys, True)
            st.rerun()
with tc3:
    if st.button("Clear All", key="mod_clear_all", use_container_width=True):
        st.session_state["uap_selected_modules"] = set()
        _sync_checkboxes(ALL_MOD_KEYS, False)
        st.rerun()

# ---------------------------------------------------------------------------
# Search + filter
# ---------------------------------------------------------------------------
st.divider()

fc1, fc2, fc3 = st.columns([3, 1, 1])
with fc1:
    search = st.text_input(
        "Search",
        placeholder="Search modules...",
        key="mod_search",
        label_visibility="collapsed",
    )
with fc2:
    product_filter = st.selectbox(
        "Product",
        options=["All"] + [p.value.upper() for p in Product],
        key="mod_product",
    )
with fc3:
    status_filter = st.selectbox(
        "Status",
        options=["All", "stable", "beta", "draft"],
        key="mod_status",
    )

filtered = list(registry)
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
        or q in m.key.lower()
        or any(q in t for t in m.tags)
    ]

if not filtered:
    st.warning("No modules match your filters.")
    st.stop()

# ---------------------------------------------------------------------------
# Module grid -- grouped by Product > Category
# ---------------------------------------------------------------------------
groups: dict[str, list[ModuleInfo]] = {}
for m in filtered:
    key = f"{m.product.value.upper()} / {m.category}"
    groups.setdefault(key, []).append(m)


def _render_module(m: ModuleInfo) -> None:
    """Render a single module row with checkbox."""
    status_label, status_cls = _STATUS_TAG.get(m.status, ("?", "tag-draft"))

    c_chk, c_info = st.columns([0.3, 5])
    with c_chk:
        was_selected = m.key in selected
        checked = st.checkbox(
            m.name,
            value=was_selected,
            key=f"mod_{m.key}",
            label_visibility="collapsed",
        )
        if checked != was_selected:
            if checked:
                selected.add(m.key)
            else:
                selected.discard(m.key)
            st.session_state["uap_selected_modules"] = selected

    with c_info:
        badges = f'<span class="mod-tag {status_cls}">{status_label}</span>'
        if m.depends_on:
            badges += f'<span class="mod-tag tag-dep">needs {len(m.depends_on)}</span>'
        if m.run_order == 99:
            badges += '<span class="mod-tag tag-last">runs last</span>'
        for o in m.output_types:
            badges += f'<span class="mod-tag tag-out">{o}</span>'

        desc = f' <span class="mod-desc">-- {m.description}</span>' if m.description else ""

        st.markdown(
            f'<div class="mod-row"><span class="mod-name">{m.name}</span>{badges}{desc}</div>',
            unsafe_allow_html=True,
        )


for cat_name, modules in sorted(groups.items()):
    product = modules[0].product
    color = _PROD_COLORS.get(product, "#94A3B8")
    cat_sel = sum(1 for m in modules if m.key in selected)
    cat_total = len(modules)
    cat_keys = [m.key for m in modules]
    all_in = cat_sel == cat_total

    # Category header with single toggle
    hdr1, hdr2 = st.columns([5, 1])
    with hdr1:
        st.markdown(
            f'<div class="cat-header">'
            f'<div class="cat-bar" style="background:{color};"></div>'
            f'<span class="cat-label">{cat_name}</span>'
            f'<span class="cat-count">{cat_sel}/{cat_total}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with hdr2:
        if all_in:
            if st.button("Deselect", key=f"cattog_{cat_name}", use_container_width=True):
                _deselect_keys(cat_keys)
        else:
            if st.button("Select", key=f"cattog_{cat_name}", use_container_width=True):
                _select_keys(cat_keys)

    for m in modules:
        _render_module(m)

# ---------------------------------------------------------------------------
# Selection summary
# ---------------------------------------------------------------------------
st.divider()

if selected:
    by_prod: dict[str, int] = {}
    for m in registry:
        if m.key in selected:
            by_prod[m.product.value.upper()] = by_prod.get(m.product.value.upper(), 0) + 1

    detail_parts = [f"{prod}: {ct}" for prod, ct in sorted(by_prod.items())]
    detail_str = " | ".join(detail_parts)

    st.markdown(
        f'<div class="sel-bar">'
        f"<div>"
        f'<span class="sel-count">{len(selected)} modules selected</span><br>'
        f'<span class="sel-detail">{detail_str}</span>'
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.info(
        "Pipelines run all modules for the selected product. "
        "Individual module selection will be available in a future release."
    )

    with st.expander("Save selection as template", expanded=False):
        new_name = st.text_input("Template name", key="save_template_name")
        if st.button("Save", key="save_template_btn") and new_name.strip():
            from platform_app.core.templates import save_template

            save_template(new_name.strip(), sorted(selected))
            st.success(f"Saved template: **{new_name.strip()}**")
            st.rerun()
else:
    st.markdown(
        '<div class="sel-bar">'
        '<span class="sel-count" style="color:#94A3B8;">No modules selected</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Use the quick-select buttons above, load a template, or check individual modules.")
