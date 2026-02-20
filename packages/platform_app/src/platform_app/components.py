"""Shared UI components -- KPI cards, styled containers, module selector."""

from __future__ import annotations

import streamlit as st


def kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_color: str = "normal",
) -> None:
    """Render a single KPI metric card using st.metric."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def kpi_row(metrics: list[dict]) -> None:
    """Render a row of KPI cards.

    Each dict: {"label": str, "value": str, "delta": str|None, "delta_color": str}
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
                delta_color=m.get("delta_color", "normal"),
            )


def section_header(title: str, description: str = "") -> None:
    """Render a section header with optional description."""
    st.markdown(f"### {title}")
    if description:
        st.caption(description)


def status_badge(status: str) -> str:
    """Return a colored status badge string for markdown."""
    colors = {
        "success": ":green[Success]",
        "failed": ":red[Failed]",
        "running": ":orange[Running]",
        "pending": ":blue[Pending]",
        "skipped": ":gray[Skipped]",
    }
    return colors.get(status.lower(), f":gray[{status}]")


def pipeline_selector() -> str:
    """Pipeline selection radio button. Returns pipeline key."""
    return st.radio(
        "Pipeline",
        ["ars", "txn", "txn_v4", "ics"],
        format_func={
            "ars": "ARS Analysis",
            "txn": "Transaction (Base)",
            "txn_v4": "Transaction (V4)",
            "ics": "ICS Analysis",
        }.get,
        horizontal=True,
    )


PIPELINE_FILE_ROLES: dict[str, list[dict]] = {
    "ars": [{"role": "oddd", "label": "ODD File (.xlsx)", "types": ["xlsx", "xls", "csv"]}],
    "txn": [{"role": "tran", "label": "Transaction File (.csv)", "types": ["csv", "xlsx"]}],
    "txn_v4": [
        {"role": "txn_dir", "label": "Transaction Directory", "types": ["csv"]},
        {"role": "odd", "label": "ODD File (.xlsx)", "types": ["xlsx", "xls"]},
    ],
    "ics": [{"role": "ics", "label": "ICS Data File (.xlsx)", "types": ["xlsx", "csv"]}],
}
