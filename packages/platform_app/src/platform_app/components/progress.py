"""Pipeline progress wrapper using st.progress + st.status."""

from __future__ import annotations

import time
from collections.abc import Callable

import streamlit as st

from shared.types import AnalysisResult


def run_with_progress(
    pipeline_name: str,
    run_fn: Callable[..., dict[str, AnalysisResult]],
    **kwargs,
) -> dict[str, AnalysisResult]:
    """Wrap any pipeline run with st.progress + st.status.

    Injects a ``progress_callback`` into *kwargs* so the pipeline
    can report step-by-step progress to the UI.
    """
    progress_bar = st.progress(0, text=f"Initializing {pipeline_name}...")
    messages: list[str] = []

    def on_progress(msg: str) -> None:
        messages.append(msg)
        progress_bar.progress(min(len(messages) / 20, 0.95), text=msg)

    kwargs["progress_callback"] = on_progress

    with st.status(f"Running {pipeline_name}...", expanded=True) as status:
        t0 = time.time()
        results = run_fn(**kwargs)
        elapsed = time.time() - t0
        status.update(label=f"Complete in {elapsed:.1f}s", state="complete", expanded=False)

    progress_bar.progress(1.0, text="Complete!")
    st.toast(f"{pipeline_name} complete in {elapsed:.1f}s", icon=":material/check_circle:")
    return results
