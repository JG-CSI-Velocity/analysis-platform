"""Unified results display: data tables, charts, downloads."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from platform_app.components.download import render_downloads
from shared.types import AnalysisResult


def _find_chart_images(output_dir: Path) -> list[Path]:
    """Find all chart PNG files in the output directory tree."""
    return sorted(f for f in output_dir.rglob("*.png") if f.is_file())


def render_results(
    results: dict[str, AnalysisResult],
    output_dir: Path | None = None,
    client_id: str = "",
) -> None:
    """Display analysis results in a tabbed layout.

    Shows metrics row, Data Tables tab, optional Charts tab, and Downloads tab.
    """
    # Discover charts
    chart_images = _find_chart_images(output_dir) if output_dir else []

    # KPI metrics row
    total_rows = sum(df.shape[0] for ar in results.values() for df in ar.data.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Analyses", len(results))
    m2.metric("Total Rows", f"{total_rows:,}")
    m3.metric("Charts", len(chart_images))

    tab_names = ["Data Tables"]
    if chart_images:
        tab_names.append(f"Charts ({len(chart_images)})")
    if output_dir:
        tab_names.append("Downloads")

    tabs = st.tabs(tab_names)
    tab_idx = 0

    # Tables tab
    with tabs[tab_idx]:
        for name, ar in results.items():
            with st.expander(ar.summary or name, expanded=False):
                for sheet_name, df in ar.data.items():
                    st.dataframe(df, use_container_width=True, hide_index=True)
    tab_idx += 1

    # Charts tab
    if chart_images:
        with tabs[tab_idx]:
            for img_path in chart_images:
                st.image(str(img_path), caption=img_path.stem, use_container_width=True)
        tab_idx += 1

    # Downloads tab
    if output_dir:
        with tabs[tab_idx]:
            render_downloads(output_dir)
