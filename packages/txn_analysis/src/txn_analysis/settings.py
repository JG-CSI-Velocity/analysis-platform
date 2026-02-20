"""Pydantic configuration for txn_analysis."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from txn_analysis.exceptions import ConfigError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.yaml")

BRAND_COLORS = [
    "#005EB8",
    "#E4573D",
    "#4ABFBF",
    "#F3C13A",
    "#0090D4",
    "#A2AAAD",
]


class ChartConfig(BaseModel):
    """Chart rendering settings."""

    theme: str = "consultant"
    colors: list[str] = Field(default_factory=lambda: BRAND_COLORS.copy())
    width: int = 900
    height: int = 500
    scale: int = 3


class OutputConfig(BaseModel):
    """Output format toggles."""

    excel: bool = True
    chart_images: bool = True
    powerpoint: bool = False
    html_charts: bool = False


class Settings(BaseModel):
    """Application configuration -- immutable after creation."""

    model_config = {"frozen": True, "extra": "forbid"}

    data_file: Path | None = None
    odd_file: Path | None = None
    transaction_dir: Path | None = None
    client_id: str | None = None
    client_name: str | None = None
    output_dir: Path = Path("output/")
    outputs: OutputConfig = OutputConfig()
    charts: ChartConfig = ChartConfig()
    top_n: int = 50
    growth_min_threshold: float = 1000.0
    consistency_min_spend: float = 10000.0
    consistency_min_months: int = 3
    threat_min_accounts: int = 100
    threat_min_spend: float = 50000.0
    ic_rate: float = 0.0
    # Segmentation thresholds
    seg_balanced_pct: float = 25.0
    seg_competitor_heavy_pct: float = 50.0
    seg_at_risk_pct: float = 80.0
    seg_at_risk_min_spend: float = 500.0
    # Lifecycle & demographics
    onboarding_window_days: int = 90
    high_value_threshold: float = 10000.0
    medium_value_threshold: float = 1000.0
    active_days: int = 30
    recent_days: int = 90

    @field_validator("data_file", mode="before")
    @classmethod
    def expand_and_validate_data_file(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v).expanduser().resolve()
        if not p.exists():
            raise ValueError(f"Data file not found: {p}")
        if p.suffix.lower() not in (".csv", ".xlsx", ".xls"):
            raise ValueError(f"Unsupported file type: {p.suffix}")
        return p

    @field_validator("odd_file", mode="before")
    @classmethod
    def expand_and_validate_odd_file(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v).expanduser().resolve()
        if not p.exists():
            raise ValueError(f"ODD file not found: {p}")
        if p.suffix.lower() not in (".xlsx", ".xls"):
            raise ValueError(f"ODD file must be Excel (.xlsx/.xls): {p.suffix}")
        return p

    @field_validator("transaction_dir", mode="before")
    @classmethod
    def expand_and_validate_transaction_dir(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return None
        p = Path(v).expanduser().resolve()
        if not p.exists():
            raise ValueError(f"Transaction directory not found: {p}")
        if not p.is_dir():
            raise ValueError(f"transaction_dir is not a directory: {p}")
        return p

    @field_validator("ic_rate", mode="before")
    @classmethod
    def validate_ic_rate(cls, v: float) -> float:
        v = float(v)
        if v != 0.0 and not (0.001 <= v <= 0.025):
            raise ValueError(
                f"ic_rate={v} outside valid range (0.1%-2.5%). "
                "Use decimal form, e.g. 0.0145 for 1.45%"
            )
        return v

    @field_validator("output_dir", mode="before")
    @classmethod
    def expand_output_dir(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    @model_validator(mode="after")
    def derive_client_fields(self) -> Settings:
        if self.client_id is None:
            source = self.data_file or self.transaction_dir
            if source is not None:
                stem = source.stem if self.data_file else source.name
                match = re.match(r"^(\d+)", stem)
                if match:
                    object.__setattr__(self, "client_id", match.group(1))
        if self.client_name is None and self.client_id:
            object.__setattr__(self, "client_name", f"Client {self.client_id}")
        return self

    @classmethod
    def from_yaml(cls, config_path: Path = DEFAULT_CONFIG_PATH, **cli_overrides) -> Settings:
        """Load from YAML, merge CLI overrides (highest priority)."""
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            data = {}
        data.update({k: v for k, v in cli_overrides.items() if v is not None})
        try:
            return cls(**data)
        except Exception as e:
            raise ConfigError(f"Configuration error: {e}") from e

    @classmethod
    def from_args(cls, data_file: Path, **kwargs) -> Settings:
        """Create settings directly from arguments (no YAML needed)."""
        try:
            return cls(data_file=data_file, **kwargs)
        except Exception as e:
            raise ConfigError(f"Configuration error: {e}") from e
