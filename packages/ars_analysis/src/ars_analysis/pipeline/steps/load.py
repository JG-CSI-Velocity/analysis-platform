"""Step: Load ODD data with Copy-on-Write, date pre-parsing, column validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from ars_analysis.exceptions import DataError
from ars_analysis.pipeline.context import PipelineContext

# Required columns that must be present in every ODD file.
# Each entry is (canonical_name, *aliases). The first alias found is renamed.
REQUIRED_COLUMNS: tuple[tuple[str, ...], ...] = (
    ("Stat Code",),
    ("Product Code", "Prod Code"),
    ("Date Opened",),
    ("Avg Bal", "Balance", "Current Balance", "Cur Bal"),
)

# Columns to pre-parse as dates (avoids 14+ redundant to_datetime calls downstream).
DATE_COLUMNS: tuple[str, ...] = (
    "Date Opened",
    "Date Closed",
)


def step_load(ctx: PipelineContext) -> None:
    """Load an ODD Excel/CSV file into ctx.data with validation.

    Applies:
    - pandas Copy-on-Write (eliminates 55+ unnecessary .copy() calls)
    - Date pre-parsing on known date columns
    - Column presence validation
    """
    pd.set_option("mode.copy_on_write", True)

    file_path = ctx.paths.base_dir / _find_data_file(ctx.paths.base_dir)
    logger.info("Loading data from {name}", name=file_path.name)

    df = _read_file(file_path)

    # Pre-parse date columns once at load time
    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
            logger.debug("Pre-parsed date column: {col}", col=col)

    _normalize_columns(df, file_path)

    ctx.data = df
    ctx.data_original = df
    logger.info(
        "Loaded {rows:,} rows x {cols} columns from {name}",
        rows=len(df),
        cols=len(df.columns),
        name=file_path.name,
    )


def step_load_file(ctx: PipelineContext, file_path: Path) -> None:
    """Load a specific file (used by CLI 'ars run <file>')."""
    pd.set_option("mode.copy_on_write", True)

    logger.info("Loading data from {name}", name=file_path.name)
    df = _read_file(file_path)

    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    _normalize_columns(df, file_path)

    ctx.data = df
    ctx.data_original = df
    logger.info(
        "Loaded {rows:,} rows x {cols} columns from {name}",
        rows=len(df),
        cols=len(df.columns),
        name=file_path.name,
    )


def _normalize_columns(df: pd.DataFrame, file_path: Path) -> None:
    """Rename known aliases to canonical names and validate required columns."""
    renames: dict[str, str] = {}
    missing: list[str] = []

    for names in REQUIRED_COLUMNS:
        canonical = names[0]
        if canonical in df.columns:
            continue
        # Check aliases
        found = False
        for alias in names[1:]:
            if alias in df.columns:
                renames[alias] = canonical
                found = True
                break
        if not found:
            missing.append(canonical)

    if renames:
        df.rename(columns=renames, inplace=True)
        for old, new in renames.items():
            logger.info("Column renamed: '{old}' -> '{new}'", old=old, new=new)

    if missing:
        logger.warning(
            "Available columns: {cols}",
            cols=", ".join(sorted(df.columns[:20])),
        )
        raise DataError(
            f"ODD file missing required columns: {', '.join(sorted(missing))}",
            detail={"file": str(file_path), "missing": sorted(missing)},
        )


def _read_file(path: Path) -> pd.DataFrame:
    """Read a file based on extension."""
    suffix = path.suffix.lower()

    # Reject unsupported formats first
    if suffix not in (".xlsx", ".xls", ".csv"):
        raise DataError(
            f"Unsupported file format: {suffix}",
            detail={"file": str(path), "supported": [".xlsx", ".xls", ".csv"]},
        )

    # Check file isn't empty/corrupt
    file_size = path.stat().st_size
    if file_size < 100:
        raise DataError(
            f"File is too small ({file_size} bytes) -- likely empty or corrupt",
            detail={"file": str(path), "size": file_size},
        )

    if suffix in (".xlsx", ".xls"):
        try:
            return pd.read_excel(path)
        except ValueError as exc:
            raise DataError(
                f"Cannot read Excel file: {exc}",
                detail={"file": str(path)},
            ) from exc
    return pd.read_csv(path)


def _find_data_file(directory: Path) -> str:
    """Find the ODD data file in a directory."""
    for ext in ("*.xlsx", "*.xls", "*.csv"):
        files = sorted(directory.glob(ext))
        if files:
            return files[0].name
    raise DataError(
        f"No data file found in {directory}",
        detail={"directory": str(directory), "searched": ["*.xlsx", "*.xls", "*.csv"]},
    )
