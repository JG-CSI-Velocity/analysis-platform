"""Dual-mode file input: upload or server path."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st


def render_file_input(
    page_key: str,
    accepted_types: list[str],
    label: str = "Upload client data",
) -> Path | None:
    """File uploader + fallback path input. Returns Path or None."""
    mode = st.radio(
        "Input method",
        ["Upload file", "Server path"],
        key=f"{page_key}_input_mode",
        horizontal=True,
    )

    if mode == "Upload file":
        uploaded = st.file_uploader(label, type=accepted_types, key=f"{page_key}_upload")
        if uploaded is None:
            return None
        # Write to temp file so pipelines can use Path-based APIs
        suffix = f".{uploaded.name.rsplit('.', 1)[-1]}" if "." in uploaded.name else ""
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix=f"{page_key}_")
        tmp.write(uploaded.getvalue())
        tmp.flush()
        return Path(tmp.name)
    else:
        path_str = st.text_input(
            "File path",
            key=f"{page_key}_path",
            value=st.session_state.get(f"{page_key}_last_path", ""),
        )
        if not path_str.strip():
            return None
        p = Path(path_str.strip())
        if not p.exists():
            st.error(f"File not found: `{p}`")
            return None
        st.session_state[f"{page_key}_last_path"] = path_str.strip()
        return p
