"""Shared UI components for pipeline pages."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from platform_app.core.module_registry import ModuleInfo, Product, get_modules_by_product
from platform_app.core.templates import BUILTIN_TEMPLATES


def render_file_input(
    label: str,
    session_key: str,
    filetypes: str = ".xlsx",
    help_text: str = "",
) -> str:
    """Render a file path input with validation. Returns the path string."""
    val = st.text_input(
        label,
        value=st.session_state.get(session_key, ""),
        key=f"_input_{session_key}",
        help=help_text,
        placeholder=f"Path to {filetypes} file...",
    )
    st.session_state[session_key] = val

    if val:
        p = Path(val)
        if not p.exists():
            st.error(f"File not found: {val}")
        elif p.suffix.lower() not in filetypes.split(","):
            st.warning(f"Expected {filetypes}, got {p.suffix}")
    return val


def render_module_picker(
    product: Product,
    session_key: str,
) -> set[str]:
    """Render grouped module checkboxes. Returns set of selected module keys."""
    modules = get_modules_by_product(product)
    by_cat: dict[str, list[ModuleInfo]] = {}
    for m in sorted(modules, key=lambda x: x.run_order):
        by_cat.setdefault(m.category, []).append(m)

    selected: set[str] = st.session_state.get(session_key, set())

    # Select all / none
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if st.button("Select All", key=f"_selall_{session_key}", type="secondary"):
            selected = {m.key for m in modules}
            st.session_state[session_key] = selected
            st.rerun()
    with cols[1]:
        if st.button("Clear", key=f"_clr_{session_key}", type="secondary"):
            selected = set()
            st.session_state[session_key] = selected
            st.rerun()

    # Grouped checkboxes in two columns
    cat_names = list(by_cat.keys())
    left_cats = cat_names[: len(cat_names) // 2 + 1]
    right_cats = cat_names[len(cat_names) // 2 + 1 :]

    col_l, col_r = st.columns(2)
    for col, cats in [(col_l, left_cats), (col_r, right_cats)]:
        with col:
            for cat_name in cats:
                st.markdown(
                    f'<p style="font-size:0.82rem;font-weight:700;color:#475569;'
                    f'text-transform:uppercase;letter-spacing:0.03em;margin:0.8rem 0 0.2rem 0;">'
                    f"{cat_name}</p>",
                    unsafe_allow_html=True,
                )
                for m in by_cat[cat_name]:
                    checked = st.checkbox(
                        m.name,
                        value=m.key in selected,
                        key=f"_cb_{session_key}_{m.key}",
                        help=m.description or None,
                    )
                    if checked:
                        selected.add(m.key)
                    else:
                        selected.discard(m.key)

    st.session_state[session_key] = selected
    return selected


def render_preset_picker(
    product: Product,
    session_key: str,
) -> None:
    """Render preset template buttons that populate the module picker."""
    prefix = product.value.upper()
    matching = {
        name: keys
        for name, keys in BUILTIN_TEMPLATES.items()
        if name.startswith(prefix) or name.startswith(product.value.upper())
    }

    if not matching:
        return

    st.caption("Quick presets:")
    cols = st.columns(min(len(matching), 4))
    for col, (name, keys) in zip(cols, matching.items()):
        with col:
            if st.button(name, key=f"_preset_{session_key}_{name}", type="secondary"):
                st.session_state[session_key] = set(keys)
                st.rerun()


def render_run_button(
    label: str,
    session_key: str,
    selected_count: int,
) -> bool:
    """Render the run button. Returns True when clicked."""
    is_running = st.session_state.get(f"{session_key}_running", False)

    def _on_click():
        st.session_state[f"{session_key}_running"] = True
        st.session_state[f"{session_key}_start"] = time.time()

    clicked = st.button(
        "Running..." if is_running else f"{label} ({selected_count} modules)",
        type="primary",
        key=f"_run_{session_key}",
        disabled=is_running or selected_count == 0,
        on_click=_on_click,
        use_container_width=True,
    )
    return clicked or is_running


def render_progress(session_key: str, pipeline_name: str):
    """Render a progress bar + status text. Returns (bar, text) placeholders."""
    bar = st.progress(0, text=f"{pipeline_name.upper()} -- Initializing...")
    text = st.empty()
    return bar, text


def make_progress_callback(bar, text, pipeline_name: str, session_key: str):
    """Create a progress callback that updates the bar and text."""

    def _cb(msg: str) -> None:
        fraction = _extract_progress(msg)
        short = msg.split("] ", 1)[-1] if "] " in msg else msg
        if fraction is not None:
            bar.progress(min(fraction, 0.99), text=short)
        text.markdown(f"**{pipeline_name.upper()}** -- {short}")

    return _cb


def render_results(
    results: dict,
    output_dir: Path,
    elapsed: float,
    pipeline_name: str,
    errors: str | None = None,
) -> None:
    """Render the results section: KPI cards, deliverables, errors."""
    st.divider()
    st.markdown(
        '<p style="font-size:0.82rem;font-weight:700;color:#475569;'
        'text-transform:uppercase;letter-spacing:0.03em;">RESULTS</p>',
        unsafe_allow_html=True,
    )

    if errors:
        st.error(f"{pipeline_name.upper()} failed")
        with st.expander("Error Details", expanded=True):
            st.code(errors, language="python")
        return

    # KPI row
    n_results = len(results)
    cols = st.columns(3)
    cols[0].metric("Analyses", n_results)
    cols[1].metric("Runtime", f"{elapsed:.1f}s")
    cols[2].metric("Status", "Complete")

    st.success(f"{pipeline_name.upper()} -- {n_results} analyses in {elapsed:.1f}s")

    # Deliverables
    _DELIVERABLE_EXTS = {".pptx", ".xlsx"}
    _MIME = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    deliverables: list[Path] = []
    if output_dir.is_dir():
        deliverables = [
            f
            for f in output_dir.rglob("*")
            if f.is_file() and f.suffix in _DELIVERABLE_EXTS
        ]

    if deliverables:
        st.markdown(
            '<p style="font-size:0.82rem;font-weight:700;color:#475569;'
            'text-transform:uppercase;margin-top:1rem;">DELIVERABLES</p>',
            unsafe_allow_html=True,
        )
        for f in sorted(deliverables, key=lambda p: p.name):
            ext = f.suffix.lstrip(".")
            size_kb = f.stat().st_size / 1024
            dl_cols = st.columns([5, 1])
            dl_cols[0].markdown(f"**{f.name}** ({size_kb:.0f} KB)")
            dl_cols[1].download_button(
                "Download",
                f.read_bytes(),
                file_name=f.name,
                mime=_MIME.get(f.suffix, "application/octet-stream"),
                key=f"_dl_{pipeline_name}_{f.name}",
            )


def _extract_progress(msg: str) -> float | None:
    """Extract a fractional progress from a message like '[3/10] ...'."""
    if "[" in msg and "/" in msg and "]" in msg:
        try:
            inside = msg.split("[", 1)[1].split("]", 1)[0]
            cur, total = inside.split("/")
            return int(cur) / int(total)
        except (ValueError, ZeroDivisionError):
            pass
    return None
