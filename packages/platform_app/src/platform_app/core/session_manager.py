"""Workspace session manager: CSM + client folder resolution.

CSMs operate in: /data/{csm_name}/{YYYY.MM}/{client_id}/
The session manager resolves paths, auto-detects data files,
and persists workspace state across Streamlit reruns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Default root directories to scan for CSM folders
DEFAULT_DATA_ROOTS = [
    Path("data"),
    Path("/data"),
    Path("M:/ARS"),
]


@dataclass(frozen=True)
class ClientWorkspace:
    """Resolved workspace for a specific CSM + client."""

    csm: str
    client_id: str
    client_name: str
    month: str
    root: Path
    oddd_file: Path | None = None
    tran_file: Path | None = None
    ics_file: Path | None = None
    config_file: Path | None = None
    output_dir: Path = field(default_factory=lambda: Path("output"))

    @property
    def has_ars_data(self) -> bool:
        return self.oddd_file is not None

    @property
    def has_txn_data(self) -> bool:
        return self.tran_file is not None

    @property
    def has_ics_data(self) -> bool:
        return self.ics_file is not None

    @property
    def available_pipelines(self) -> list[str]:
        pipelines = []
        if self.has_ars_data:
            pipelines.append("ars")
        if self.has_txn_data:
            pipelines.append("txn")
        if self.has_ics_data:
            pipelines.append("ics")
        return pipelines


_MONTH_RE = re.compile(r"^\d{4}\.\d{2}$")


def discover_csm_folders(data_root: Path) -> list[str]:
    """Return sorted list of CSM folder names under data_root."""
    if not data_root.is_dir():
        return []
    return sorted(d.name for d in data_root.iterdir() if d.is_dir() and not d.name.startswith("."))


def discover_months(csm_dir: Path) -> list[str]:
    """Return sorted list of YYYY.MM month folders under a CSM directory."""
    if not csm_dir.is_dir():
        return []
    return sorted(
        (d.name for d in csm_dir.iterdir() if d.is_dir() and _MONTH_RE.match(d.name)),
        reverse=True,
    )


def discover_clients(month_dir: Path) -> list[str]:
    """Return sorted list of client folder names under a month directory."""
    if not month_dir.is_dir():
        return []
    return sorted(d.name for d in month_dir.iterdir() if d.is_dir() and not d.name.startswith("."))


def auto_detect_files(client_dir: Path) -> dict[str, Path | None]:
    """Scan a client directory for known data file patterns.

    Returns dict with keys: oddd, tran, ics, config -- each Path or None.
    """
    oddd = _find_by_patterns(client_dir, ["*ODD*.xlsx", "*ODDD*.xlsx", "*odd*.xlsx"])
    tran = _find_by_patterns(client_dir, ["*tran*.csv", "*Tran*.csv", "*TRAN*.csv", "*.csv"])
    ics = _find_by_patterns(client_dir, ["*ICS*.xlsx", "*ics*.xlsx", "*ICS*.csv"])
    config = _find_by_patterns(client_dir, ["*config*.json", "*config*.yaml"])

    return {"oddd": oddd, "tran": tran, "ics": ics, "config": config}


def resolve_workspace(
    csm: str,
    client_id: str,
    client_name: str,
    data_root: Path,
    month: str = "",
) -> ClientWorkspace:
    """Build a ClientWorkspace from CSM + month + client selection."""
    client_dir = data_root / csm / month / client_id if month else data_root / csm / client_id
    output_dir = client_dir / "output"

    detected = auto_detect_files(client_dir) if client_dir.is_dir() else {}

    return ClientWorkspace(
        csm=csm,
        client_id=client_id,
        client_name=client_name,
        month=month,
        root=client_dir,
        oddd_file=detected.get("oddd"),
        tran_file=detected.get("tran"),
        ics_file=detected.get("ics"),
        config_file=detected.get("config"),
        output_dir=output_dir,
    )


def _find_by_patterns(directory: Path, patterns: list[str]) -> Path | None:
    """Return the first file matching any of the glob patterns."""
    for pattern in patterns:
        matches = sorted(directory.glob(pattern))
        if matches:
            return matches[-1]  # most recent
    return None
