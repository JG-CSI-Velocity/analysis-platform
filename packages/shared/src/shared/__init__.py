"""Shared infrastructure for the unified analysis platform."""

from shared.config import PipelineConfig, PlatformConfig
from shared.context import PipelineContext
from shared.types import AnalysisResult

__all__ = [
    "PlatformConfig",
    "PipelineConfig",
    "PipelineContext",
    "AnalysisResult",
]
