"""Retrieve ODD files from CSM M: drive folders into the local directory structure.

Copies ODD files from each CSM's source folder into:
    retrieve_dir/CSM/YYYY.MM/ClientID/filename.xlsx

Handles raw .xlsx ODD files and ####_ODDD.zip archives.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from ars_analysis.config import ARSSettings
from ars_analysis.pipeline.utils import (
    parse_month_folder,
    parse_odd_filename,
    parse_oddd_zip,
    resolve_target_month,
)

logger = logging.getLogger(__name__)
console = Console()

# Timeout (seconds) for checking if a network path is accessible.
_PATH_TIMEOUT = 5.0


@dataclass
class RetrieveResult:
    """Structured result from a retrieve operation."""

    copied: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)
    errors: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.copied) + len(self.skipped) + len(self.errors)


def _path_accessible(path: Path, timeout: float = _PATH_TIMEOUT) -> bool | None:
    """Check if *path* exists, with a timeout to avoid hanging on offline shares.

    Returns True/False for accessible/missing, or None if the check timed out.
    """
    result: list[bool | None] = [None]

    def _check() -> None:
        try:
            result[0] = path.exists()
        except OSError:
            result[0] = False

    t = threading.Thread(target=_check, daemon=True)
    t.start()
    t.join(timeout)
    return result[0]


def _scan_one_csm(
    csm_name: str,
    source_dir: Path,
    dest_root: Path,
    target_year: str,
    target_mm: str,
    max_per_csm: int = 0,
) -> tuple[str, str, RetrieveResult]:
    """Scan a single CSM source in a worker thread.

    Returns (csm_name, status, per-csm RetrieveResult).
    """
    per_csm = RetrieveResult()

    accessible = _path_accessible(source_dir)
    if accessible is None:
        return csm_name, "TIMEOUT", per_csm
    if not accessible:
        return csm_name, "OFFLINE", per_csm

    _retrieve_csm(
        source_dir,
        csm_name,
        dest_root,
        target_year,
        target_mm,
        per_csm,
        max_per_csm,
    )
    return csm_name, "OK", per_csm


def retrieve_all(
    settings: ARSSettings,
    target_month: str | None = None,
    max_per_csm: int = 0,
) -> RetrieveResult:
    """Copy ODD files from CSM sources into retrieve_dir/CSM/YYYY.MM/ClientID/.

    Scans all CSM source folders in parallel to avoid sequential network waits.

    Parameters
    ----------
    settings : ARSSettings
        Pipeline settings with csm_sources and paths.
    target_month : str or None
        'YYYY.MM' to filter on. Defaults to current month.
    max_per_csm : int
        Max files to retrieve per CSM. 0 = no limit.
    """
    full_month, target_year, target_mm = resolve_target_month(target_month)
    dest_root = settings.paths.retrieve_dir
    result = RetrieveResult()

    # Verify base path exists before trying to create subdirectories
    base = settings.paths.ars_base
    if not base.exists():
        logger.error(
            "ars_base path does not exist: %s -- check ars_config.json paths.ars_base",
            base,
        )
        return result

    try:
        dest_root.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(
            "Permission denied creating %s -- check folder permissions on %s",
            dest_root,
            base,
        )
        return result

    logger.info("Retrieving ODD files for %s -> %s", full_month, dest_root)

    sources = settings.csm_sources.sources
    total_csm = len(sources)
    if total_csm == 0:
        console.print("  No CSM sources configured.")
        return result
    console.print(f"  Scanning {total_csm} CSM sources in parallel ...")

    # Launch all CSM scans at the same time -- network I/O bound, threads ideal
    with ThreadPoolExecutor(max_workers=total_csm) as pool:
        futures = {
            pool.submit(
                _scan_one_csm,
                csm_name,
                source_dir,
                dest_root,
                target_year,
                target_mm,
                max_per_csm,
            ): csm_name
            for csm_name, source_dir in sources.items()
        }

        for future in as_completed(futures):
            csm_name, status, per_csm = future.result()

            if status == "TIMEOUT":
                console.print(f"  [cyan]{csm_name}[/cyan] [yellow]TIMEOUT[/yellow]")
                continue
            if status == "OFFLINE":
                console.print(f"  [cyan]{csm_name}[/cyan] [yellow]OFFLINE[/yellow]")
                continue

            # Merge per-CSM results into the combined result
            result.copied.extend(per_csm.copied)
            result.skipped.extend(per_csm.skipped)
            result.errors.extend(per_csm.errors)

            n = len(per_csm.copied) + len(per_csm.skipped) + len(per_csm.errors)
            if n == 0:
                console.print(
                    f"  [cyan]{csm_name}[/cyan] [green]OK[/green] "
                    f"[dim]-- no files for this month[/dim]",
                )
            else:
                parts = []
                if per_csm.copied:
                    parts.append(f"[green]{len(per_csm.copied)} copied[/green]")
                if per_csm.skipped:
                    parts.append(f"[yellow]{len(per_csm.skipped)} existing[/yellow]")
                if per_csm.errors:
                    parts.append(f"[red]{len(per_csm.errors)} errors[/red]")
                console.print(
                    f"  [cyan]{csm_name}[/cyan] [green]OK[/green] -- " + ", ".join(parts),
                )

    console.print()
    logger.info(
        "Retrieve done: %d copied, %d skipped, %d errors",
        len(result.copied),
        len(result.skipped),
        len(result.errors),
    )
    return result


def _retrieve_csm(
    source_dir: Path,
    csm_name: str,
    dest_root: Path,
    target_year: str,
    target_mm: str,
    result: RetrieveResult,
    max_files: int = 0,
) -> None:
    """Retrieve ODD files from a single CSM source folder.

    Strategy: only scan month-matching subfolders instead of rglob-ing
    the entire directory tree. This avoids slow recursive network scans.
    """
    count_before = len(result.copied)

    # Find subfolders that match the target month (name-first, minimal stat)
    month_dirs = _find_month_dirs(source_dir, target_year, target_mm)

    if month_dirs:
        for month_dir in month_dirs:
            if max_files and len(result.copied) - count_before >= max_files:
                break
            console.print(f"      scanning [bold]{month_dir.name}[/bold]/ ...")
            _scan_dir_for_odds(
                month_dir,
                csm_name,
                dest_root,
                target_year,
                target_mm,
                result,
                max_files,
                count_before,
            )

            try:
                for child in month_dir.iterdir():
                    if max_files and len(result.copied) - count_before >= max_files:
                        break
                    if child.is_dir():
                        _scan_dir_for_odds(
                            child,
                            csm_name,
                            dest_root,
                            target_year,
                            target_mm,
                            result,
                            max_files,
                            count_before,
                        )
            except (PermissionError, OSError) as exc:
                logger.warning("%s: error scanning %s: %s", csm_name, month_dir.name, exc)
    else:
        console.print("      [dim]no month folder, checking root...[/dim]")
        _scan_dir_for_odds(
            source_dir,
            csm_name,
            dest_root,
            target_year,
            target_mm,
            result,
            max_files,
            count_before,
        )


def _find_month_dirs(source_dir: Path, target_year: str, target_mm: str) -> list[Path]:
    """Find subfolders matching the target month (non-recursive, one level).

    Checks folder *name* first so we only call is_dir() on entries whose name
    already matches the target month -- avoids dozens of network stat calls.
    """
    matches = []
    try:
        for child in source_dir.iterdir():
            # Parse name BEFORE stat -- fast string check, no network I/O
            month_info = parse_month_folder(child.name)
            if not month_info:
                continue
            if month_info[0] != target_year or month_info[1] != target_mm:
                continue
            # Only stat the entries whose name actually matches
            if child.is_dir():
                matches.append(child)
    except (PermissionError, OSError) as exc:
        logger.warning("Error listing %s: %s", source_dir, exc)
    return matches


def _scan_dir_for_odds(
    directory: Path,
    csm_name: str,
    dest_root: Path,
    target_year: str,
    target_mm: str,
    result: RetrieveResult,
    max_files: int = 0,
    count_base: int = 0,
) -> None:
    """Scan a single directory (non-recursive) for ODD xlsx and zip files.

    Filters by filename pattern BEFORE calling is_file() to minimize
    network stat calls on irrelevant entries.
    """
    try:
        entries = list(directory.iterdir())
    except (PermissionError, OSError):
        return

    for f in entries:
        if max_files and len(result.copied) - count_base >= max_files:
            return

        name_lower = f.name.lower()

        # Quick name-based filters first (no network I/O)
        if f.name.startswith("~$"):
            continue
        if not (name_lower.endswith(".xlsx") or name_lower.endswith(".zip")):
            continue

        # Only stat entries that pass name filters
        if not f.is_file():
            continue

        # .xlsx ODD files
        if name_lower.endswith(".xlsx"):
            parsed = parse_odd_filename(f.name)
            if parsed and parsed["year"] == target_year and parsed["month"] == target_mm:
                _place_odd(f, parsed, csm_name, dest_root, result)

        # .zip archives
        elif name_lower.endswith(".zip"):
            _process_zip(f, csm_name, target_year, target_mm, dest_root, result)


def _place_odd(
    xlsx_data: Path | bytes,
    parsed: dict[str, str],
    csm_name: str,
    dest_root: Path,
    result: RetrieveResult,
    source_label: str | None = None,
) -> None:
    """Copy a single ODD file into CSM/YYYY.MM/ClientID/ structure."""
    month_folder = f"{parsed['year']}.{parsed['month']}"
    target_dir = dest_root / csm_name / month_folder / parsed["client_id"]
    target_file = target_dir / parsed["filename"]

    if target_file.exists():
        result.skipped.append((csm_name, parsed["filename"]))
        return

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(xlsx_data, Path):
            shutil.copy2(xlsx_data, target_file)
        else:
            target_file.write_bytes(xlsx_data)
        label = source_label or parsed["filename"]
        result.copied.append((csm_name, label))
        console.print(
            f"      [green]+[/green] {parsed['client_id']} {parsed['filename']}",
        )
        logger.info("Copied %s from %s", parsed["filename"], csm_name)
    except (PermissionError, OSError) as exc:
        result.errors.append((csm_name, parsed["filename"], str(exc)))
        console.print(
            f"      [red]x[/red] {parsed['filename']}: {exc}",
        )
        logger.error("Failed to copy %s: %s", parsed["filename"], exc)


def _process_zip(
    zf_path: Path,
    csm_name: str,
    target_year: str,
    target_mm: str,
    dest_root: Path,
    result: RetrieveResult,
) -> None:
    """Process a single zip archive for ODD files.

    Copies the zip to a local temp file first so zipfile reads happen on
    local disk instead of over the network. SMB handles sequential reads
    fine but random seeks (which zipfile requires) are extremely slow.
    """
    client_id_from_zip = parse_oddd_zip(zf_path.name)
    month_info = parse_month_folder(zf_path.parent.name)

    # Skip zips in month folders that don't match target
    if month_info and (month_info[0] != target_year or month_info[1] != target_mm):
        return
    if not month_info:
        logger.debug("Skip zip (no month folder): %s/%s", zf_path.parent.name, zf_path.name)
        return

    # Fallback: extract client_id from leading digits
    if not client_id_from_zip:
        lead_digits = re.match(r"^(\d+)", zf_path.stem)
        if lead_digits:
            client_id_from_zip = lead_digits.group(1)

    try:
        # Copy zip to local temp -- one sequential read over network,
        # then all zip seeks happen on local disk.
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            local_zip = Path(tmp.name)
            shutil.copy2(zf_path, local_zip)

        try:
            _extract_zip(
                local_zip,
                zf_path.name,
                csm_name,
                client_id_from_zip,
                month_info,
                target_year,
                target_mm,
                dest_root,
                result,
            )
        finally:
            local_zip.unlink(missing_ok=True)

    except (PermissionError, OSError) as exc:
        logger.error("Zip copy error: %s -- %s", zf_path.name, exc)
        result.errors.append((csm_name, zf_path.name, str(exc)))


def _extract_zip(
    local_zip: Path,
    original_name: str,
    csm_name: str,
    client_id_from_zip: str | None,
    month_info: tuple[str, str] | None,
    target_year: str,
    target_mm: str,
    dest_root: Path,
    result: RetrieveResult,
) -> None:
    """Extract ODD files from a local copy of a zip archive."""
    try:
        with zipfile.ZipFile(local_zip, "r") as zf:
            entries = [
                n for n in zf.namelist() if Path(n).name and not Path(n).name.startswith("~$")
            ]

            for name in entries:
                basename = Path(name).name
                parsed = parse_odd_filename(basename)

                if parsed and (parsed["year"] != target_year or parsed["month"] != target_mm):
                    parsed = None

                # Use zip/folder metadata for any data file inside
                if not parsed and client_id_from_zip and month_info:
                    if basename.lower().endswith((".xlsx", ".csv")):
                        year, month = month_info
                        parsed = {
                            "client_id": client_id_from_zip,
                            "year": year,
                            "month": month,
                            "client_name": "",
                            "filename": basename,
                        }

                if not parsed:
                    continue

                data = zf.read(name)
                _place_odd(
                    data,
                    parsed,
                    csm_name,
                    dest_root,
                    result,
                    source_label=f"{original_name}/{basename}",
                )

    except zipfile.BadZipFile as exc:
        logger.error("Bad zip: %s -- %s", original_name, exc)
        result.errors.append((csm_name, original_name, str(exc)))
