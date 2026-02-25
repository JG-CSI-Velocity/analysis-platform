"""Format ODD files: apply the 7-step ARS formatting pipeline.

Uses the canonical ``shared.format_odd.format_odd`` implementation for the
per-DataFrame transformation.  This module adds ``format_all`` (batch
orchestration across CSM directories) and ``_read_odd`` (file I/O).
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from rich.console import Console

from ars_analysis.config import ARSSettings
from ars_analysis.pipeline.utils import resolve_target_month
from shared.format_odd import format_odd  # canonical implementation

logger = logging.getLogger(__name__)
console = Console()

# Re-export so existing callers (`from ars_analysis.pipeline.steps.format import format_odd`) work.
__all__ = ["format_odd", "format_all", "FormatResult"]


@dataclass
class FormatResult:
    """Structured result from a format operation."""

    formatted: list[tuple[str, str, str]] = field(default_factory=list)
    errors: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.formatted) + len(self.errors)


def _read_odd(file_path: Path) -> pd.DataFrame | None:
    """Read an ODD file (csv or xlsx) into a DataFrame."""
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(file_path, skiprows=4, low_memory=False)
            if df.empty:
                return None
            if df.columns[0].startswith("Unnamed") or df.iloc[:, 0].dtype == "int64":
                df = df.drop(columns=[df.columns[0]])
            return df
        if suffix == ".xlsx":
            df = pd.read_excel(file_path)
            return df if not df.empty else None
    except Exception:
        logger.exception("Error reading %s", file_path.name)
        return None
    return None


def format_all(
    settings: ARSSettings,
    target_month: str | None = None,
    max_per_csm: int = 0,
) -> FormatResult:
    """Read raw ODD files from retrieve_dir, format, write to watch_root.

    Raw files: Incoming/ODDD Files/CSM/YYYY.MM/ClientID/
    Formatted: Ready for Analysis/CSM/YYYY.MM/ClientID/

    Parameters
    ----------
    settings : ARSSettings
        Pipeline settings with paths.retrieve_dir and paths.watch_root.
    target_month : str or None
        'YYYY.MM' format. Defaults to current month.
    max_per_csm : int
        Max files to format per CSM. 0 = no limit.
    """
    full_month, _, _ = resolve_target_month(target_month)
    root = settings.paths.retrieve_dir
    out_root = settings.paths.watch_root
    result = FormatResult()

    if not root.exists():
        logger.warning("Retrieve dir not found: %s", root)
        return result

    logger.info(
        "Formatting ODD files for %s (source: %s -> dest: %s, limit: %s)",
        full_month,
        root,
        out_root,
        max_per_csm or "all",
    )

    csm_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    total_csm = len(csm_dirs)

    for i, csm_dir in enumerate(csm_dirs, 1):
        csm_name = csm_dir.name
        month_dir = csm_dir / full_month
        if not month_dir.exists():
            console.print(
                f"  [{i}/{total_csm}] [cyan]{csm_name}[/cyan] [dim]-- no {full_month} folder[/dim]",
            )
            continue

        client_dirs = sorted(d for d in month_dir.iterdir() if d.is_dir())
        console.print(
            f"  [{i}/{total_csm}] [cyan]{csm_name}[/cyan] -- {len(client_dirs)} client(s)",
        )

        count = 0
        for client_dir in client_dirs:
            if max_per_csm and count >= max_per_csm:
                break

            # Find ODD file (skip formatted, skip lock files)
            odd_files = [
                f
                for f in client_dir.iterdir()
                if f.is_file()
                and f.suffix.lower() in (".csv", ".xlsx")
                and not f.name.startswith("~$")
                and "formatted" not in f.name.lower()
            ]
            if not odd_files:
                continue

            odd_file = odd_files[0]
            logger.info("%s/%s: %s", csm_name, client_dir.name, odd_file.name)

            # Copy to local temp, format locally, copy result back
            tmp_dir = None
            try:
                tmp_dir = Path(tempfile.mkdtemp(prefix="ars_fmt_"))
                local_src = tmp_dir / odd_file.name
                shutil.copy2(odd_file, local_src)

                df = _read_odd(local_src)
                if df is None:
                    result.errors.append((csm_name, odd_file.name, "empty or unreadable"))
                    console.print(
                        f"      [red]x[/red] {client_dir.name} -- empty or unreadable",
                    )
                    continue

                df = format_odd(df)
                out_name = odd_file.stem + "-formatted.xlsx"
                local_out = tmp_dir / out_name
                df.to_excel(local_out, index=False, engine="openpyxl")

                # Copy result to network destination
                dest_dir = out_root / csm_name / full_month / client_dir.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_out, dest_dir / out_name)

                result.formatted.append((csm_name, client_dir.name, out_name))
                count += 1
                console.print(
                    f"      [green]+[/green] {client_dir.name} "
                    f"({df.shape[0]} rows, {df.shape[1]} cols)",
                )
                logger.info("Saved %s (%d rows x %d cols)", out_name, *df.shape)
            except Exception:
                logger.exception("Error formatting %s", odd_file.name)
                result.errors.append((csm_name, odd_file.name, "formatting failed"))
                console.print(
                    f"      [red]x[/red] {client_dir.name} -- formatting failed",
                )
            finally:
                if tmp_dir and tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)

    console.print()
    logger.info(
        "Format done: %d formatted, %d errors",
        len(result.formatted),
        len(result.errors),
    )
    return result
