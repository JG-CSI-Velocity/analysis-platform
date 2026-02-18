"""Common types and result containers used across all pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class AnalysisResult:
    """Immutable container for a single analysis output."""

    name: str
    data: dict[str, pd.DataFrame] = field(default_factory=dict)
    charts: list[Path] = field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
