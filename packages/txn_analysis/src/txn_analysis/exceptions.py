"""Exception hierarchy for txn_analysis."""


class TxnError(Exception):
    """Base exception for all txn_analysis errors."""


class ConfigError(TxnError):
    """Invalid or missing configuration."""


class DataLoadError(TxnError):
    """Failed to load or parse the data file."""


class ColumnMismatchError(DataLoadError):
    """Required columns missing from the dataset."""

    def __init__(self, missing: set[str], available: set[str]) -> None:
        self.missing = missing
        self.available = available
        super().__init__(f"Missing required columns: {sorted(missing)}")


class AnalysisError(TxnError):
    """An individual analysis failed."""

    def __init__(self, analysis_name: str, cause: Exception) -> None:
        self.analysis_name = analysis_name
        self.cause = cause
        super().__init__(f"Analysis '{analysis_name}' failed: {cause}")
