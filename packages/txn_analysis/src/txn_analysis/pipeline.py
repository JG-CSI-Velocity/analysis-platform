"""Pipeline orchestrator shared by CLI and run_client()."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from txn_analysis.analyses import run_all_analyses
from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.data_loader import load_data, load_odd
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Container for all pipeline outputs."""

    settings: Settings
    df: pd.DataFrame
    analyses: list[AnalysisResult] = field(default_factory=list)
    charts: dict[str, go.Figure] = field(default_factory=dict)
    chart_pngs: dict[str, bytes] = field(default_factory=dict)


def run_pipeline(
    settings: Settings,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> PipelineResult:
    """Execute the full analysis pipeline: load -> analyze -> chart.

    Args:
        settings: Application configuration.
        on_progress: Optional callback(step, total, message) for UI progress.
    """
    # Step 1: Load data
    if on_progress:
        on_progress(0, 3, "Loading data...")
    df = load_data(settings)
    odd_df = load_odd(settings)

    # Step 2: Run analyses
    if on_progress:
        on_progress(1, 3, "Running analyses...")
    analyses = run_all_analyses(df, settings, odd_df=odd_df)
    successful = [a for a in analyses if a.error is None]
    failed = [a for a in analyses if a.error is not None]
    if failed:
        for a in failed:
            logger.warning("Skipped: %s (%s)", a.name, a.error)
    logger.info("%d/%d analyses completed", len(successful), len(analyses))

    # Step 3: Build charts
    if on_progress:
        on_progress(2, 3, "Building charts...")
    charts: dict[str, go.Figure] = {}
    try:
        from txn_analysis.charts import create_charts

        # Derive date range from data for source footers
        date_range = ""
        if "year_month" in df.columns and not df["year_month"].isna().all():
            months = df["year_month"].dropna().unique()
            if len(months) > 0:
                date_range = f"{min(months)} to {max(months)}"

        charts = create_charts(
            analyses,
            settings.charts,
            client_name=settings.client_name or "",
            date_range=date_range,
        )
        logger.info("Built %d charts", len(charts))
    except Exception as e:
        logger.error("Chart generation failed: %s", e, exc_info=True)

    return PipelineResult(settings=settings, df=df, analyses=analyses, charts=charts)


def _render_chart_pngs(result: PipelineResult) -> dict[str, bytes]:
    """Render all charts to PNG bytes for Excel embedding (scale=1)."""
    from io import BytesIO

    pngs: dict[str, bytes] = {}
    config = result.settings.charts

    for name, fig in result.charts.items():
        try:
            buf = BytesIO()
            fig.write_image(
                buf,
                format="png",
                width=config.width,
                height=config.height,
                scale=1,
                engine="kaleido",
            )
            pngs[name] = buf.getvalue()
        except Exception as e:
            logger.warning("PNG render failed for '%s': %s", name, e)
    return pngs


def export_outputs(result: PipelineResult) -> list[Path]:
    """Export pipeline results to configured output formats.

    Returns list of generated file paths.
    """
    settings = result.settings
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    date_str = datetime.now().strftime("%Y%m%d")
    client_id = settings.client_id or "unknown"

    # Render chart PNGs if charts exist and chart_images enabled
    chart_pngs: dict[str, bytes] = {}
    if result.charts and settings.outputs.chart_images:
        chart_pngs = _render_chart_pngs(result)
        result.chart_pngs = chart_pngs
        logger.info("Rendered %d chart PNGs", len(chart_pngs))

        # Save standalone PNGs to disk (high-res scale=3)
        chart_dir = settings.output_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)
        from txn_analysis.charts import render_chart_png

        for name, fig in result.charts.items():
            try:
                png_path = chart_dir / f"{name}.png"
                render_chart_png(fig, png_path, settings.charts)
                generated.append(png_path)
            except Exception as e:
                logger.warning("Standalone PNG for '%s' failed: %s", name, e)

    if settings.outputs.excel:
        try:
            from txn_analysis.exports.excel_report import write_excel_report

            path = settings.output_dir / f"{client_id}_TXN_Analysis_{date_str}.xlsx"
            write_excel_report(result, path)
            generated.append(path)
            logger.info("Excel report: %s", path)
        except Exception as e:
            logger.error("Excel report failed: %s", e, exc_info=True)

    return generated
