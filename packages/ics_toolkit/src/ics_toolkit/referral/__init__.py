"""Referral Intelligence Engine.

Influence scoring, network inference, and staff multiplier reports.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ics_toolkit.referral.pipeline import ReferralPipelineResult

__all__ = ["run_referral"]


def run_referral(
    data_file: str | Path,
    output_dir: str | Path = "output/referral/",
    client_id: str | None = None,
    client_name: str | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> ReferralPipelineResult:
    """Convenience function for referral pipeline (Jupyter/REPL)."""
    from ics_toolkit.referral.pipeline import export_outputs, run_pipeline
    from ics_toolkit.settings import Settings

    kwargs: dict = {"output_dir": Path(output_dir)}
    if client_id is not None:
        kwargs["client_id"] = client_id
    if client_name is not None:
        kwargs["client_name"] = client_name

    settings = Settings.for_referral(data_file=Path(data_file), **kwargs)
    result = run_pipeline(settings.referral, on_progress=on_progress)
    export_outputs(result)
    return result
