"""Loguru configuration for the ARS pipeline."""

import os
import sys
from pathlib import Path

from loguru import logger

# Custom log level for audit trail -- registered at import time so
# logger.log("AUDIT", ...) works even without setup_logging().
AUDIT_LEVEL = "AUDIT"
try:
    logger.level(AUDIT_LEVEL, no=25, color="<cyan>", icon="@")
except TypeError:
    pass  # Already registered


def get_username() -> str:
    """Get the current OS username (Windows or Unix)."""
    try:
        return os.getlogin()
    except OSError:
        return os.environ.get("USERNAME", os.environ.get("USER", "unknown"))


def sanitize_path(path: str | Path, base: Path | None = None) -> str:
    """Strip base path prefix for safer logging. Returns relative portion only."""
    path_str = str(path)
    if base:
        base_str = str(base)
        if path_str.startswith(base_str):
            return path_str[len(base_str):].lstrip("/\\") or "."
    # Fallback: just return the filename
    return Path(path_str).name


def setup_logging(
    log_dir: Path, verbose: bool = False, debug: bool = False
) -> None:
    """Configure Loguru sinks for the ARS pipeline."""
    logger.remove()

    # Console: human-readable, colorized
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File: detailed, rotated (encoding for Windows client names)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "pipeline_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # Errors only: quick triage file
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        rotation="5 MB",
        retention="90 days",
        backtrace=True,
        diagnose=debug,  # NEVER True in production -- leaks local variables
        encoding="utf-8",
    )

    # Audit trail: who ran what, when (separate file, long retention)
    logger.add(
        log_dir / "audit.log",
        level=AUDIT_LEVEL,
        filter=lambda record: record["level"].name == AUDIT_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        rotation="10 MB",
        retention="365 days",
        encoding="utf-8",
    )
