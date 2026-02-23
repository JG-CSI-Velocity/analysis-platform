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

# Known ODD data roots (checked in order; first existing one is the default)
_RAW_DATA_ROOTS = [
    Path(r"M:\ARS\Incoming\ODDD Files"),
    Path("M:/ARS/Incoming/ODDD Files"),
    Path("data"),
]


def _dedupe_roots(roots: list[Path]) -> list[Path]:
    """Deduplicate paths that resolve to the same location (e.g. M:\\ vs M:/)."""
    seen: set[str] = set()
    result: list[Path] = []
    for p in roots:
        key = str(p).replace("\\", "/").rstrip("/")
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


KNOWN_DATA_ROOTS = _dedupe_roots(_RAW_DATA_ROOTS)


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


def auto_detect_files(
    client_dir: Path,
    client_id: str = "",
    incoming_root: Path | None = None,
) -> dict:
    """Scan a client directory for known data file patterns.

    Parameters
    ----------
    client_dir : Path
        The ODD client folder (root/CSM/YYYY.MM/ClientID/).
    client_id : str
        Client ID used to locate transaction files in the sibling
        ``Transaction Files`` directory.
    incoming_root : Path or None
        The ``Incoming`` root (parent of "ODDD Files" and "Transaction Files").
        If None, auto-resolved from client_dir.

    Returns dict with keys:
        oddd, tran, ics, config -- each Path or None
        tran_files -- list[Path] of ALL transaction files found (all months)
    """
    oddd = _find_by_patterns(client_dir, ["*ODD*.xlsx", "*ODDD*.xlsx", "*odd*.xlsx"])
    ics = _find_by_patterns(client_dir, ["*ICS*.xlsx", "*ics*.xlsx", "*ICS*.csv"])
    config = _find_by_patterns(client_dir, ["*config*.json", "*config*.yaml"])

    # Transaction files: first check inside the ODD client folder
    # Note: avoid broad "*.csv" pattern -- it catches non-transaction files.
    tran = _find_by_patterns(
        client_dir,
        [
            "*tran*.csv",
            "*Tran*.csv",
            "*TRAN*.csv",
            "*txn*.csv",
            "*TXN*.csv",
            "*transaction*.csv",
            "*Transaction*.csv",
        ],
    )
    tran_files: list[Path] = [tran] if tran else []

    # If not found locally, look in Incoming/Transaction Files/{ClientID}*/
    if tran is None and client_id:
        tran_files = _find_all_tran_files(client_dir, client_id, incoming_root)
        tran = tran_files[0] if tran_files else None

    return {"oddd": oddd, "tran": tran, "tran_files": tran_files, "ics": ics, "config": config}


def _find_all_tran_files(
    client_dir: Path,
    client_id: str,
    incoming_root: Path | None = None,
) -> list[Path]:
    """Locate ALL transaction files in Incoming/Transaction Files/{ClientID}*/.

    Supports two layouts:
      - Flat:   Transaction Files/1759/file.txt
      - Nested: Transaction Files/1759/2025/*.txt + 1759/2026/*.txt

    Returns all files sorted by name (most recent last) so the caller can
    combine them. The pipeline will handle L12M filtering from the data.
    """
    if incoming_root is None:
        incoming_root = _resolve_incoming_root(client_dir)
    if incoming_root is None:
        return []

    tran_root = incoming_root / "Transaction Files"
    if not tran_root.is_dir():
        return []

    tran_dir = _find_client_tran_dir(tran_root, client_id)
    if tran_dir is None:
        return []

    all_files: list[Path] = []

    # Collect files directly in the client folder (flat layout)
    all_files.extend(_find_all_by_patterns(tran_dir, ["*.csv", "*.txt"]))

    # Collect files from year subfolders (nested layout)
    _year_re = re.compile(r"^\d{4}$")
    try:
        year_dirs = sorted(d for d in tran_dir.iterdir() if d.is_dir() and _year_re.match(d.name))
    except PermissionError:
        year_dirs = []

    for yd in year_dirs:
        all_files.extend(_find_all_by_patterns(yd, ["*.csv", "*.txt"]))

    if all_files:
        logger.info(
            "Found %d transaction files for client %s across %s",
            len(all_files),
            client_id,
            tran_dir,
        )

    return all_files


def _find_client_tran_dir(tran_root: Path, client_id: str) -> Path | None:
    """Find a transaction folder matching the client ID prefix."""
    if not tran_root.is_dir():
        return None
    try:
        for d in tran_root.iterdir():
            if d.is_dir() and (
                d.name == client_id
                or d.name.startswith(f"{client_id} ")
                or d.name.startswith(f"{client_id}-")
                or d.name.startswith(f"{client_id}_")
            ):
                return d
    except PermissionError:
        logger.warning("Permission denied scanning %s", tran_root)
    return None


def _resolve_incoming_root(client_dir: Path) -> Path | None:
    """Walk up from a client dir to find the Incoming parent.

    Expected structure: .../Incoming/ODDD Files/CSM/YYYY.MM/ClientID
    We look for a parent named "Incoming" or whose child is "ODDD Files".
    """
    for parent in client_dir.parents:
        if parent.name.lower() == "incoming":
            return parent
        if (parent / "Transaction Files").is_dir():
            return parent
    return None


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

    detected = auto_detect_files(client_dir, client_id=client_id) if client_dir.is_dir() else {}

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
        try:
            matches = sorted(directory.glob(pattern))
        except PermissionError:
            logger.warning("Permission denied scanning %s for %s", directory, pattern)
            continue
        if matches:
            return matches[-1]  # most recent
    return None


def _find_all_by_patterns(directory: Path, patterns: list[str]) -> list[Path]:
    """Return ALL files matching any of the glob patterns."""
    found: list[Path] = []
    for pattern in patterns:
        try:
            found.extend(sorted(directory.glob(pattern)))
        except PermissionError:
            logger.warning("Permission denied scanning %s for %s", directory, pattern)
    return found
