"""Pipeline execution context — typed replacement for raw ctx dict."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from shared.config import PlatformConfig
from shared.types import AnalysisResult


@dataclass
class PipelineContext:
    """Carries all state through a pipeline run.

    Replaces the 45+ key raw dict from ars_analysis-jupyter.
    Mutable during execution; populated incrementally by pipeline steps.
    """

    # --- Client identity ---
    client_name: str = ""
    client_id: str = ""
    fi_name: str = ""
    csm: str = ""
    analysis_date: date = field(default_factory=date.today)

    # --- Input files ---
    input_files: dict[str, Path] = field(default_factory=dict)

    # --- Output paths ---
    output_dir: Path = Path("output")
    chart_dir: Path = Path("output/charts")
    excel_path: Path | None = None
    pptx_path: Path | None = None

    # --- Config ---
    config: PlatformConfig | None = None
    client_config: dict[str, Any] = field(default_factory=dict)

    # --- Data ---
    data: pd.DataFrame | None = None
    data_original: pd.DataFrame | None = None
    subsets: dict[str, pd.DataFrame] = field(default_factory=dict)

    # --- Time range ---
    start_date: pd.Timestamp | None = None
    end_date: pd.Timestamp | None = None
    last_12_months: list[str] = field(default_factory=list)

    # --- Results ---
    results: dict[str, AnalysisResult] = field(default_factory=dict)
    all_slides: list[dict[str, Any]] = field(default_factory=list)
    export_log: list[dict[str, str]] = field(default_factory=list)

    # --- Progress ---
    progress_callback: Callable[[str], None] | None = None
