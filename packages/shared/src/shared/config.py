"""Layered configuration: platform.yaml -> pipeline.yaml -> env vars."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class PipelineConfig(BaseModel):
    """Per-pipeline configuration (ars, txn, ics)."""

    enabled: bool = True
    input_dir: Path | None = None
    settings: dict[str, Any] = {}


class PlatformConfig(BaseModel):
    """Root platform configuration loaded from YAML."""

    base_output_dir: Path = Path("output")
    m_drive_path: Path | None = None
    chart_theme: str = "consultant"
    template_pptx: Path | None = None
    pipelines: dict[str, PipelineConfig] = {}

    @classmethod
    def load(cls, path: Path) -> PlatformConfig:
        """Load config from YAML file with defaults for missing keys."""
        if not path.exists():
            return cls()
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return cls(**raw)

    @classmethod
    def load_layered(cls, *paths: Path) -> PlatformConfig:
        """Load and merge multiple YAML files (later files override earlier)."""
        merged: dict[str, Any] = {}
        for path in paths:
            if path.exists():
                with open(path) as f:
                    raw = yaml.safe_load(f) or {}
                merged = _deep_merge(merged, raw)
        return cls(**merged)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
