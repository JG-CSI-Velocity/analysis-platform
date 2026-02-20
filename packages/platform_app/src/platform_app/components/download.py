"""Download button row for generated output files."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

MIME_MAP = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".csv": "text/csv",
    ".html": "text/html",
}


def render_downloads(output_dir: Path) -> None:
    """Render download buttons for all generated output files in *output_dir*."""
    files = sorted(f for f in output_dir.rglob("*") if f.is_file() and f.suffix in MIME_MAP)
    if not files:
        st.caption("No output files found.")
        return

    for f in files:
        mime = MIME_MAP.get(f.suffix, "application/octet-stream")
        st.download_button(
            f.name,
            f.read_bytes(),
            file_name=f.name,
            mime=mime,
            key=f"dl_{f.name}",
        )
