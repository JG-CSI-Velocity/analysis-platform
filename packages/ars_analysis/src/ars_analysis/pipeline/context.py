"""Typed pipeline context -- replaces the raw ctx dict (~40 keys)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd


@dataclass
class ClientInfo:
    """Client identity and configuration."""

    client_id: str
    client_name: str
    month: str  # "YYYY.MM"
    eligible_stat_codes: list[str] = field(default_factory=list)
    eligible_prod_codes: list[str] = field(default_factory=list)
    eligible_mailable: list[str] = field(default_factory=list)
    nsf_od_fee: float = 0.0
    ic_rate: float = 0.0
    dc_indicator: str = "DC Indicator"
    reg_e_opt_in: list[str] = field(default_factory=list)
    reg_e_column: str = ""
    assigned_csm: str = ""


@dataclass
class OutputPaths:
    """Resolved output directories for one pipeline run."""

    base_dir: Path = Path(".")
    charts_dir: Path = Path(".")
    excel_dir: Path = Path(".")
    pptx_dir: Path = Path(".")

    @classmethod
    def from_base(cls, base: Path, client_id: str, month: str) -> OutputPaths:
        run_dir = base / client_id / month
        return cls(
            base_dir=run_dir,
            charts_dir=run_dir / "charts",
            excel_dir=run_dir,
            pptx_dir=run_dir,
        )


@dataclass
class DataSubsets:
    """Pre-computed filtered views of the ODD data."""

    open_accounts: pd.DataFrame | None = None
    eligible_data: pd.DataFrame | None = None
    eligible_personal: pd.DataFrame | None = None
    eligible_business: pd.DataFrame | None = None
    eligible_with_debit: pd.DataFrame | None = None
    last_12_months: pd.DataFrame | None = None


@dataclass
class PipelineContext:
    """Typed container replacing the raw ctx dict.

    Two-layer structure:
    - client: who (identity + config)
    - paths: where (output directories)
    - data/subsets: what (DataFrames)
    - results: output (per-module analysis results)
    """

    client: ClientInfo
    paths: OutputPaths
    settings: object = None  # ARSSettings -- set at runtime to avoid circular import
    data: pd.DataFrame | None = None
    data_original: pd.DataFrame | None = None
    subsets: DataSubsets = field(default_factory=DataSubsets)
    results: dict[str, list] = field(default_factory=dict)  # module_id -> [AnalysisResult]
    all_slides: list = field(default_factory=list)
    export_log: list[str] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
    txn_file_path: Path | None = None  # Transaction CSV for TXN module
    ics_dir: Path | None = None  # ICS data directory for ICS module
