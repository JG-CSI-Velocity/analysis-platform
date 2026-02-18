"""Credit union debit card transaction analysis framework."""

from __future__ import annotations

from pathlib import Path

__version__ = "1.0.0"


def run_client(
    data_file: str | Path,
    output_dir: str | Path = "output/",
    **kwargs,
):
    """Convenience entry-point for Jupyter / REPL usage.

    Usage::

        from txn_analysis import run_client
        result = run_client("data/transactions.csv")
    """
    from txn_analysis.pipeline import export_outputs, run_pipeline
    from txn_analysis.settings import Settings

    settings = Settings.from_args(data_file=Path(data_file), output_dir=Path(output_dir), **kwargs)
    result = run_pipeline(settings)
    export_outputs(result)
    return result
