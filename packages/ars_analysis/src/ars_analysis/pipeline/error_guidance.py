"""User-friendly error guidance for non-technical CSMs."""

from __future__ import annotations

from ars_analysis.exceptions import ConfigError, DataError, OutputError, RetrieveError

ERROR_GUIDANCE: list[tuple[type[Exception], str, str]] = [
    (FileNotFoundError, "File Not Found", "Check the file path and ensure M: drive is connected"),
    (PermissionError, "File Locked", "Close the file in Excel and try again"),
    (RetrieveError, "Retrieve Error", "Check M: drive connection and CSM source folder paths in config"),
    (DataError, "Data Problem", "The ODD file format may have changed -- check column names"),
    (ConfigError, "Setup Issue", "Run 'ars init' or check ars_config.json"),
    (OutputError, "Output Error", "Ensure Template12.25.pptx is in the templates/ folder"),
]


def get_error_guidance(exc: Exception) -> tuple[str, str]:
    """Return (title, user_message) for a given exception.

    Uses isinstance() so subclass exceptions are caught by their parent.
    """
    for exc_type, title, message in ERROR_GUIDANCE:
        if isinstance(exc, exc_type):
            return title, message
    return "Unexpected Error", "An unexpected error occurred. Check the log file for details."
