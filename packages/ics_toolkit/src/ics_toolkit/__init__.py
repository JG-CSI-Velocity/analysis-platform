"""ICS Toolkit -- append accounts and generate analytics reports."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ics_toolkit.analysis.pipeline import AnalysisPipelineResult
    from ics_toolkit.append.pipeline import PipelineResult

__version__ = "1.0.0"


def run_append(
    base_dir: str | Path,
    ars_dir: str | Path | None = None,
    match_month: str | None = None,
    dry_run: bool = False,
    on_progress: Callable[[str, str], None] | None = None,
) -> PipelineResult:
    """Convenience function for append pipeline (Jupyter/REPL)."""
    from ics_toolkit.append.pipeline import run_pipeline
    from ics_toolkit.settings import Settings

    settings = Settings.for_append(
        base_dir=Path(base_dir),
        ars_dir=Path(ars_dir) if ars_dir else None,
        match_month=match_month,
        dry_run=dry_run,
    )
    return run_pipeline(settings.append, on_progress=on_progress)


def run_analysis(
    data_file: str | Path,
    output_dir: str | Path = "output/",
    client_id: str | None = None,
    client_name: str | None = None,
    cohort_start: str | None = None,
    ics_not_in_dump: int = 0,
    on_progress: Callable | None = None,
) -> AnalysisPipelineResult:
    """Convenience function for analysis pipeline (Jupyter/REPL)."""
    from ics_toolkit.analysis.pipeline import export_outputs, run_pipeline
    from ics_toolkit.settings import Settings

    kwargs: dict = {
        "output_dir": Path(output_dir),
        "ics_not_in_dump": ics_not_in_dump,
    }
    if client_id is not None:
        kwargs["client_id"] = client_id
    if client_name is not None:
        kwargs["client_name"] = client_name
    if cohort_start is not None:
        kwargs["cohort_start"] = cohort_start

    settings = Settings.for_analysis(data_file=Path(data_file), **kwargs)
    result = run_pipeline(settings.analysis, on_progress=on_progress)
    export_outputs(result)
    return result
