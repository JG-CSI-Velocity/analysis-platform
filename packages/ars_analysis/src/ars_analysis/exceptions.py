"""Custom exception hierarchy for the ARS pipeline."""

from typing import Any


class ARSError(Exception):
    """Base exception for all ARS pipeline errors."""

    def __init__(self, message: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}

    def __repr__(self) -> str:
        if self.detail:
            return f"{type(self).__name__}({self!s}, detail={self.detail})"
        return f"{type(self).__name__}({self!s})"


class ConfigError(ARSError):
    """Configuration or client setup problem."""


class DataError(ARSError):
    """Data loading, parsing, or validation failure."""


class OutputError(ARSError):
    """Deck build, Excel write, or report generation failure."""


class RetrieveError(ARSError):
    """ODD file retrieval failure."""
