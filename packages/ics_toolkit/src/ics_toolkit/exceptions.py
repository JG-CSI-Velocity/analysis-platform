"""Unified exception hierarchy for ICS Toolkit."""


class ICSToolkitError(Exception):
    """Base exception for all ICS toolkit errors."""


class ConfigError(ICSToolkitError):
    """Configuration loading or validation error."""


class DataError(ICSToolkitError):
    """Data loading, validation, or processing error."""


class DetectionError(ICSToolkitError):
    """File or column detection error."""


class MergeError(ICSToolkitError):
    """Error during REF/DM merge."""


class MatchError(ICSToolkitError):
    """Error during ODD matching."""


class AnalysisError(ICSToolkitError):
    """Error during analysis execution."""


class ExportError(ICSToolkitError):
    """Error during report export."""
