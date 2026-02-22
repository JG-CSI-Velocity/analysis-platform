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
    """Sync checkbox widget keys to match bulk selection state."""
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
# Config
# ---------------------------------------------------------------------------
_PROD_COLORS = {
    Product.ARS: "#3B82F6",
    Product.TXN: "#10B981",
    Product.ICS: "#F59E0B",
}
_PROD_LABELS = {
    Product.ARS: ("ARS", "Account Review Suite", "8 modules"),
    Product.TXN: ("TXN", "Transaction Analysis", "35 modules"),
    Product.ICS: ("ICS", "ICS Toolkit", "37 modules"),
}
_STATUS_TAG = {
    ModuleStatus.STABLE: ("BUILT", "tag-built"),
    ModuleStatus.BETA: ("BETA", "tag-beta"),
    ModuleStatus.DRAFT: ("PLANNED", "tag-draft"),
}

_prod_modules = {p: [m for m in registry if m.product == p] for p in Product}

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* Template pills */
.tpl-row { display: flex; gap: 8px; flex-wrap: wrap; margin: 0.5rem 0; }

/* Tab counter badge */
.tab-badge {
    display: inline-block;
    font-family: var(--uap-mono);
    font-size: 0.6rem; font-weight: 700;
    padding: 1px 6px; border-radius: 10px;
    margin-left: 6px;
}

/* Category expander overrides */
div[data-testid="stExpander"] {
    border: 1px solid var(--uap-border) !important;
    border-radius: 6px !important;
    margin-bottom: 0.4rem !important;
}
div[data-testid="stExpander"] summary {
    font-family: var(--uap-sans) !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
}

/* Module tags */
.mod-tag {
    display: inline-block; font-family: var(--uap-mono);
    font-size: 0.58rem; font-weight: 600; letter-spacing: 0.04em;
    padding: 1px 6px; border-radius: 2px; margin-left: 4px;
}
.tag-built { background: #DCFCE7; color: #166534; }
.tag-beta { background: #DBEAFE; color: #1E40AF; }
.tag-draft { background: #FEE2E2; color: #991B1B; }
.tag-dep { background: #FEF3C7; color: #92400E; }
.tag-last { background: #E0E7FF; color: #3730A3; }
.tag-out { background: #F1F5F9; color: #64748B; }

/* Module info line */
.mod-info {
    display: flex; align-items: center; gap: 6px;
    padding: 0.15rem 0; flex-wrap: wrap;
}
.mod-name {
    font-family: var(--uap-sans); font-weight: 500;
    font-size: 0.86rem; color: var(--uap-ink);
}
.mod-desc {
    font-family: var(--uap-sans); font-size: 0.76rem; color: #94A3B8;
}

/* Selection summary bar */
.sel-bar {
    background: var(--uap-ink); color: #CBD5E1;
    padding: 0.7rem 1.2rem; border-radius: 8px; margin-top: 0.5rem;
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
# Templates -- promoted to top as quick-launch
# ---------------------------------------------------------------------------
templates = load_templates()

st.markdown('<p class="uap-label">QUICK START</p>', unsafe_allow_html=True)

# Render template buttons in a row
tpl_cols = st.columns(len(templates) + 1)
for i, (tpl_name, tpl_keys) in enumerate(templates.items()):
    with tpl_cols[i]:
        if st.button(tpl_name, key=f"tpl_{i}", use_container_width=True):
            st.session_state["uap_selected_modules"] = set(tpl_keys)
            _sync_checkboxes(ALL_MOD_KEYS, False)
            _sync_checkboxes(tpl_keys, True)
            st.rerun()
with tpl_cols[-1]:
    if st.button("Clear All", key="tpl_clear", use_container_width=True):
        st.session_state["uap_selected_modules"] = set()
        _sync_checkboxes(ALL_MOD_KEYS, False)
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Tabbed product view
# ---------------------------------------------------------------------------

# Build tab labels with selection counts
tab_labels = []
for product in Product:
    label, _, _ = _PROD_LABELS[product]
    total = len(_prod_modules[product])
    sel_ct = sum(1 for m in _prod_modules[product] if m.key in selected)
    if sel_ct > 0:
        tab_labels.append(f"{label}  ({sel_ct}/{total})")
    else:
        tab_labels.append(f"{label}  (0/{total})")

tabs = st.tabs(tab_labels)

for tab, product in zip(tabs, Product):
    with tab:
        prod_label, prod_subtitle, prod_count = _PROD_LABELS[product]
        color = _PROD_COLORS[product]
        modules = _prod_modules[product]
        prod_keys = [m.key for m in modules]
        prod_sel = sum(1 for m in modules if m.key in selected)
        all_selected = prod_sel == len(modules)

        # Product header row: subtitle + select/deselect toggle
        h1, h2 = st.columns([4, 1])
        with h1:
            st.caption(f"{prod_subtitle}  --  {len(modules)} modules")
        with h2:
            if all_selected:
                if st.button(
                    "Deselect All",
                    key=f"prod_tog_{product.value}",
                    use_container_width=True,
                ):
                    _deselect_keys(prod_keys)
            else:
                if st.button(
                    "Select All",
                    key=f"prod_tog_{product.value}",
                    use_container_width=True,
                    type="primary" if prod_sel == 0 else "secondary",
                ):
                    _select_keys(prod_keys)

        # Group modules by category
        categories: dict[str, list[ModuleInfo]] = {}
        for m in modules:
            categories.setdefault(m.category, []).append(m)

        # Render each category as an expander
        for cat_name, cat_modules in categories.items():
            cat_keys = [m.key for m in cat_modules]
            cat_sel = sum(1 for m in cat_modules if m.key in selected)
            cat_total = len(cat_modules)

            # Expander label with count
            if cat_sel > 0:
                exp_label = f"{cat_name}  --  {cat_sel}/{cat_total} selected"
            else:
                exp_label = f"{cat_name}  --  {cat_total} modules"

            with st.expander(exp_label, expanded=cat_sel > 0):
                # Category-level select/deselect
                all_cat_in = cat_sel == cat_total
                sc1, sc2 = st.columns([4, 1])
                with sc2:
                    if all_cat_in:
                        if st.button(
                            "Deselect",
                            key=f"cat_{product.value}_{cat_name}",
                            use_container_width=True,
                        ):
                            _deselect_keys(cat_keys)
                    else:
                        if st.button(
                            "Select",
                            key=f"cat_{product.value}_{cat_name}",
                            use_container_width=True,
                        ):
                            _select_keys(cat_keys)

                # Individual module checkboxes
                for m in cat_modules:
                    status_label, status_cls = _STATUS_TAG.get(m.status, ("?", "tag-draft"))

                    c_chk, c_info = st.columns([0.3, 5])
                    with c_chk:
                        widget_key = f"mod_{m.key}"
                        if widget_key not in st.session_state:
                            st.session_state[widget_key] = m.key in selected

                        checked = st.checkbox(
                            m.name,
                            key=widget_key,
                            label_visibility="collapsed",
                        )
                        if checked and m.key not in selected:
                            selected.add(m.key)
                            st.session_state["uap_selected_modules"] = selected
                        elif not checked and m.key in selected:
                            selected.discard(m.key)
                            st.session_state["uap_selected_modules"] = selected

                    with c_info:
                        badges = f'<span class="mod-tag {status_cls}">{status_label}</span>'
                        if m.depends_on:
                            badges += (
                                f'<span class="mod-tag tag-dep">needs {len(m.depends_on)}</span>'
                            )
                        if m.run_order == 99:
                            badges += '<span class="mod-tag tag-last">runs last</span>'
                        for o in m.output_types:
                            badges += f'<span class="mod-tag tag-out">{o}</span>'

                        desc = (
                            f'<span class="mod-desc">-- {m.description}</span>'
                            if m.description
                            else ""
                        )

                        st.markdown(
                            f'<div class="mod-info">'
                            f'<span class="mod-name">{m.name}</span>'
                            f"{badges} {desc}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

# ---------------------------------------------------------------------------
# Selection summary bar
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
        f'<span class="sel-count">{len(selected)} modules selected</span>'
        f'<br><span class="sel-detail">{detail_str}</span>'
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
    st.caption("Pick a template above or browse the tabs to select modules.")
