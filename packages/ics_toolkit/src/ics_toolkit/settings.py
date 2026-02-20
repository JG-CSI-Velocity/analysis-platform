"""Unified configuration system using Pydantic BaseModel + yaml.safe_load."""

import logging
import re
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ics_toolkit.exceptions import ConfigError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_PPTX_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "Template12.25.pptx"

MATCH_MONTH_PATTERN = re.compile(r"^\d{4}\.(0[1-9]|1[0-2])$")

DEFAULT_BALANCE_BINS = [float("-inf"), 0, 1000, 5000, 10000, 25000, 50000, 100000, float("inf")]
DEFAULT_BALANCE_LABELS = [
    "$0 or Less",
    "$0-$1K",
    "$1K-$5K",
    "$5K-$10K",
    "$10K-$25K",
    "$25K-$50K",
    "$50K-$100K",
    "$100K+",
]

DEFAULT_AGE_BINS = [0, 30, 90, 180, 365, 730, 1825, 3650, float("inf")]
DEFAULT_AGE_LABELS = [
    "0-1 month",
    "1-3 months",
    "3-6 months",
    "6-12 months",
    "1-2 years",
    "2-5 years",
    "5-10 years",
    "10+ years",
]

BRAND_COLORS = ["#1B365D", "#4A90D9", "#7BC67E", "#F5A623", "#D0021B", "#8B572A"]


# ---------------------------------------------------------------------------
# Append sub-models
# ---------------------------------------------------------------------------


class ClientConfig(BaseModel):
    """Per-client file format overrides."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ref_column: str | None = None
    ref_header_row: Annotated[int | None, Field(ge=0, le=100)] = None
    dm_column: str | None = None
    dm_header_row: Annotated[int | None, Field(ge=0, le=100)] = None

    @field_validator("ref_column", "dm_column")
    @classmethod
    def column_name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Column name must not be blank")
        return v.strip() if v else v

    @model_validator(mode="after")
    def column_requires_header_row(self) -> "ClientConfig":
        if self.ref_column and self.ref_header_row is None:
            raise ValueError("ref_header_row required when ref_column is set")
        if self.dm_column and self.dm_header_row is None:
            raise ValueError("dm_header_row required when dm_column is set")
        return self


class AppendSettings(BaseModel):
    """Settings specific to the append pipeline."""

    base_dir: Path | None = None
    ars_dir: Path | None = None
    output_dir: Path = Path("output/")
    match_month: str | None = None
    dry_run: bool = False
    overwrite: bool = True
    csv_copy: bool = False
    clients: dict[str, ClientConfig] = Field(default_factory=dict)
    default_ref_keywords: list[str] = Field(
        default_factory=lambda: ["referral", "ref", "ics_detailed"]
    )
    default_dm_keywords: list[str] = Field(
        default_factory=lambda: ["direct mail", "directmail", "new accounts"]
    )
    hash_min_length: int = 6
    match_rate_warn_threshold: float = 0.5

    @field_validator("base_dir", "ars_dir", "output_dir", mode="before")
    @classmethod
    def expand_paths(cls, v: str | Path | None) -> Path | None:
        if v is None:
            return v
        return Path(v).expanduser().resolve()

    @field_validator("match_month")
    @classmethod
    def validate_match_month_format(cls, v: str | None) -> str | None:
        if v is not None and not MATCH_MONTH_PATTERN.match(v):
            raise ValueError(f"match_month must be YYYY.MM format, got '{v}'")
        return v

    @field_validator("clients")
    @classmethod
    def normalize_client_keys(cls, v: dict[str, ClientConfig]) -> dict[str, ClientConfig]:
        normalized: dict[str, ClientConfig] = {}
        for key, config in v.items():
            clean = key.strip()
            if not clean:
                raise ValueError("Client key must not be empty")
            if clean in normalized:
                raise ValueError(f"Duplicate client key: '{clean}'")
            normalized[clean] = config
        return normalized

    def get_client(self, client_id: str) -> ClientConfig:
        """Return client-specific config, defaulting to empty config."""
        return self.clients.get(client_id.strip(), ClientConfig())


# ---------------------------------------------------------------------------
# Analysis sub-models
# ---------------------------------------------------------------------------


class AnalysisClientConfig(BaseModel):
    """Per-client analysis overrides (stat codes, label mappings, etc.)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    open_stat_codes: list[str] | None = None
    closed_stat_codes: list[str] | None = None
    interchange_rate: float | None = None
    branch_mapping: dict[str, str] | None = None
    prod_code_mapping: dict[str, str] | None = None


class BalanceTierConfig(BaseModel):
    """Balance tier bin configuration."""

    bins: list[float] = DEFAULT_BALANCE_BINS.copy()
    labels: list[str] = DEFAULT_BALANCE_LABELS.copy()


class AgeRangeConfig(BaseModel):
    """Account age range bin configuration."""

    bins: list[float] = DEFAULT_AGE_BINS.copy()
    labels: list[str] = DEFAULT_AGE_LABELS.copy()


class ChartConfig(BaseModel):
    """Chart rendering settings."""

    theme: str = "plotly_white"
    colors: list[str] = BRAND_COLORS.copy()
    width: int = 900
    height: int = 500
    scale: int = 3


class OutputConfig(BaseModel):
    """Which output formats to generate."""

    excel: bool = True
    powerpoint: bool = True
    html_charts: bool = False


class AnalysisSettings(BaseModel):
    """Settings specific to the analysis pipeline."""

    data_file: Path | None = None
    client_id: str | None = None
    client_name: str | None = None
    output_dir: Path = Path("output/")
    data_start_date: str | None = None
    cohort_start: str | None = None
    ics_not_in_dump: int = 0
    interchange_rate: float = 0.0182
    open_stat_codes: list[str] = Field(default_factory=lambda: ["O"])
    closed_stat_codes: list[str] = Field(default_factory=lambda: ["C"])
    client_config_path: Path | None = None
    clients: dict[str, AnalysisClientConfig] = Field(default_factory=dict)
    branch_mapping: dict[str, str] | None = None
    prod_code_mapping: dict[str, str] | None = None
    balance_tiers: BalanceTierConfig = BalanceTierConfig()
    age_ranges: AgeRangeConfig = AgeRangeConfig()
    outputs: OutputConfig = OutputConfig()
    charts: ChartConfig = ChartConfig()
    pptx_template: Path | None = DEFAULT_PPTX_TEMPLATE
    last_12_months: list[str] = []

    @field_validator("data_file", mode="before")
    @classmethod
    def validate_data_file(cls, v: Path | str | None) -> Path | None:
        if v is None:
            return v
        v = Path(v)
        if not v.exists():
            raise ValueError(
                f"Data file not found: {v}\n"
                "Please check the path in config.yaml or pass the correct path."
            )
        suffix = v.suffix.lower()
        if suffix not in (".csv", ".xlsx", ".xls"):
            raise ValueError(
                f"Unsupported file type: {suffix}\nSupported formats: .csv, .xlsx, .xls"
            )
        return v

    @field_validator("client_config_path", mode="before")
    @classmethod
    def expand_client_config_path(cls, v: Path | str | None) -> Path | None:
        if v is None:
            return v
        return Path(v).expanduser().resolve()

    @model_validator(mode="after")
    def derive_client_fields(self):
        if self.data_file and self.client_id is None:
            match = re.match(r"^(\d+)", self.data_file.stem)
            if match:
                self.client_id = match.group(1)
            else:
                self.client_id = "unknown"
                logger.warning(
                    "Could not extract client ID from filename '%s'. Set client_id in config.yaml.",
                    self.data_file.name,
                )
        if self.data_file and self.client_name is None:
            self.client_name = f"Client {self.client_id}"

        # Layer 1: Master config file (base layer)
        if self.client_id and self.client_id != "unknown":
            self._apply_master_config()

        # Layer 2: config.yaml clients dict (overrides master)
        if self.client_id and self.client_id in self.clients:
            client_cfg = self.clients[self.client_id]
            if client_cfg.open_stat_codes is not None:
                self.open_stat_codes = client_cfg.open_stat_codes
            if client_cfg.closed_stat_codes is not None:
                self.closed_stat_codes = client_cfg.closed_stat_codes
            if client_cfg.interchange_rate is not None:
                self.interchange_rate = client_cfg.interchange_rate
            if client_cfg.branch_mapping is not None:
                self.branch_mapping = client_cfg.branch_mapping
            if client_cfg.prod_code_mapping is not None:
                self.prod_code_mapping = client_cfg.prod_code_mapping

        return self

    def _apply_master_config(self) -> None:
        """Load and apply master config file values (lowest priority layer)."""
        from ics_toolkit.client_registry import (
            get_client_config,
            load_master_config,
            resolve_master_config_path,
        )

        path = resolve_master_config_path(self.client_config_path)
        if path is None:
            return
        registry = load_master_config(path)
        cfg = get_client_config(self.client_id, registry)
        if cfg is None:
            return

        for field_name in (
            "open_stat_codes",
            "closed_stat_codes",
            "interchange_rate",
            "client_name",
            "branch_mapping",
            "prod_code_mapping",
        ):
            val = getattr(cfg, field_name)
            if val is not None:
                setattr(self, field_name, val)


# ---------------------------------------------------------------------------
# Unified Settings
# ---------------------------------------------------------------------------


class Settings(BaseModel):
    """Unified application configuration."""

    model_config = ConfigDict(extra="forbid")

    append: AppendSettings = AppendSettings()
    analysis: AnalysisSettings = AnalysisSettings()

    @classmethod
    def from_yaml(cls, config_path: Path = DEFAULT_CONFIG_PATH, **cli_overrides) -> "Settings":
        """Load settings from YAML file with CLI overrides.

        Priority: CLI args > config.yaml > defaults.
        """
        raw: dict = {}
        if config_path.exists():
            with open(config_path) as f:
                raw = yaml.safe_load(f) or {}
            logger.info("Loaded config from %s", config_path)

        for key, value in cli_overrides.items():
            if value is not None:
                raw[key] = str(value) if isinstance(value, Path) else value

        try:
            return cls(**raw)
        except Exception as e:
            raise ConfigError(
                f"Configuration error: {e}\n\n"
                "Fix your config.yaml or pass the correct options on the command line.\n"
                "Example: python -m ics_toolkit analyze data/your_file.xlsx"
            ) from e

    @classmethod
    def for_append(cls, base_dir: Path, **kwargs) -> "Settings":
        """Create settings for append-only usage."""
        try:
            return cls(append=AppendSettings(base_dir=base_dir, **kwargs))
        except Exception as e:
            raise ConfigError(f"Configuration error: {e}") from e

    @classmethod
    def for_analysis(cls, data_file: Path, **kwargs) -> "Settings":
        """Create settings for analysis-only usage."""
        try:
            return cls(analysis=AnalysisSettings(data_file=data_file, **kwargs))
        except Exception as e:
            raise ConfigError(f"Configuration error: {e}") from e
