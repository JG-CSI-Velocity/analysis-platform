"""Scan watch_root (Ready for Analysis) for ready ODD files.

Supports CLI `ars scan` and wizard Step 1 auto-detection.
Prefers *-formatted.xlsx over raw files when both exist.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ars_analysis.config import ARSSettings
from ars_analysis.pipeline.utils import resolve_target_month

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScannedFile:
    """A single ODD file found in the retrieve directory."""

    client_id: str
    csm_name: str
    filename: str
    file_path: Path
    month: str
    file_size_mb: float
    is_formatted: bool
    modified_time: datetime


def scan_ready_files(
    settings: ARSSettings,
    target_month: str | None = None,
    csm_filter: str | None = None,
    client_filter: str | None = None,
) -> list[ScannedFile]:
    """Scan watch_root (Ready for Analysis)/CSM/YYYY.MM/ClientID/ for files.

    Parameters
    ----------
    settings : ARSSettings
        Pipeline settings with paths.watch_root.
    target_month : str or None
        'YYYY.MM' format. Defaults to current month.
    csm_filter : str or None
        Only scan this CSM folder.
    client_filter : str or None
        Only scan this client ID folder.

    Returns
    -------
    list[ScannedFile]
        Found files, preferring formatted over raw.
    """
    full_month, _, _ = resolve_target_month(target_month)
    root = settings.paths.watch_root

    try:
        if not root.exists():
            return []
    except OSError:
        return []

    found: list[ScannedFile] = []

    if csm_filter:
        csm_dirs = [root / csm_filter]
    else:
        csm_dirs = sorted(d for d in root.iterdir() if d.is_dir())

    for csm_dir in csm_dirs:
        if not csm_dir.is_dir():
            continue
        csm_name = csm_dir.name
        month_path = csm_dir / full_month
        if not month_path.exists():
            continue

        for client_dir in sorted(month_path.iterdir()):
            if not client_dir.is_dir():
                continue
            if client_filter and client_dir.name != client_filter:
                continue

            best = _pick_best_file(client_dir)
            if best is None:
                continue

            file_path, is_formatted = best
            stat = file_path.stat()
            found.append(
                ScannedFile(
                    client_id=client_dir.name,
                    csm_name=csm_name,
                    filename=file_path.name,
                    file_path=file_path,
                    month=full_month,
                    file_size_mb=round(stat.st_size / (1024 * 1024), 2),
                    is_formatted=is_formatted,
                    modified_time=datetime.fromtimestamp(stat.st_mtime),
                )
            )

    return found


def _pick_best_file(client_dir: Path) -> tuple[Path, bool] | None:
    """Pick the best ODD file from a client directory.

    Prefers *-formatted.xlsx, then falls back to any xlsx/csv.
    Skips lock files (~$) and output files (ars-analysis, presentation).
    """
    formatted = None
    raw = None

    for f in client_dir.iterdir():
        if not f.is_file() or f.name.startswith("~$"):
            continue
        if f.suffix.lower() not in (".xlsx", ".csv"):
            continue
        name_lower = f.name.lower()
        if "ars-analysis" in name_lower or "presentation" in name_lower:
            continue

        if "formatted" in name_lower:
            formatted = f
        elif raw is None:
            raw = f

    if formatted:
        return formatted, True
    if raw:
        return raw, False
    return None


def available_months(settings: ARSSettings) -> list[str]:
    """List all month folders across all CSMs, newest first."""
    root = settings.paths.watch_root
    try:
        if not root.exists():
            return []
    except OSError:
        return []

    months: set[str] = set()
    for csm_dir in root.iterdir():
        if not csm_dir.is_dir():
            continue
        for month_dir in csm_dir.iterdir():
            if not month_dir.is_dir():
                continue
            name = month_dir.name
            parts = name.split(".")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                months.add(name)

    return sorted(months, reverse=True)


def available_csms(settings: ARSSettings) -> list[str]:
    """Return sorted list of CSM folder names in watch_root."""
    root = settings.paths.watch_root
    try:
        if not root.exists():
            return []
    except OSError:
        return []
    return sorted(d.name for d in root.iterdir() if d.is_dir())
