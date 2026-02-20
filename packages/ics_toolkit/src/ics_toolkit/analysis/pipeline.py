"""Pipeline orchestrator shared by CLI and Jupyter/REPL."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.analyses import run_all_analyses
from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.analysis.charts import create_charts, render_all_chart_pngs, save_charts_html
from ics_toolkit.analysis.data_loader import load_data
from ics_toolkit.analysis.utils import get_ics_accounts, get_ics_stat_o, get_ics_stat_o_debit
from ics_toolkit.settings import AnalysisSettings as Settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisPipelineResult:
    """Container for all analysis pipeline outputs."""

    settings: Settings
    df: pd.DataFrame
    analyses: list[AnalysisResult] = field(default_factory=list)
    charts: dict[str, go.Figure] = field(default_factory=dict)
    chart_pngs: dict[str, bytes] = field(default_factory=dict)


def run_pipeline(
    settings: Settings,
    on_progress: Callable[[int, int, str], None] | None = None,
    skip_charts: bool = False,
) -> AnalysisPipelineResult:
    """Execute the full analysis pipeline: load -> filter -> analyze -> chart.

    Args:
        settings: Application configuration.
        on_progress: Optional callback(step, total, message) for UI progress.
        skip_charts: If True, skip Plotly chart creation entirely.
    """
    # Step 1: Load data
    logger.info("[1/5] Loading data...")
    if on_progress:
        on_progress(0, 5, "Loading data...")
    df = load_data(settings)

    # Filter out records before data_start_date (e.g. test data)
    if settings.data_start_date:
        cutoff = pd.to_datetime(settings.data_start_date)

        # Filter rows by Date Opened
        if "Date Opened" in df.columns:
            before = len(df)
            opened = pd.to_datetime(df["Date Opened"], errors="coerce")
            df = df[opened.isna() | (opened >= cutoff)].copy()
            dropped = before - len(df)
            if dropped > 0:
                logger.info(
                    "Filtered %d records opened before %s", dropped, settings.data_start_date
                )

        # Prune L12M month tags before cutoff (e.g. drop Feb24 when cutoff is 2025-01-01)
        if settings.last_12_months:
            filtered_tags = []
            for tag in settings.last_12_months:
                tag_dt = datetime.strptime(tag, "%b%y")
                if tag_dt >= cutoff:
                    filtered_tags.append(tag)
            pruned = len(settings.last_12_months) - len(filtered_tags)
            if pruned > 0:
                logger.info(
                    "Pruned %d L12M month tags before %s (kept %d)",
                    pruned,
                    settings.data_start_date,
                    len(filtered_tags),
                )
            settings.last_12_months = filtered_tags

    # Auto-detect cohort_start from L12M month tags if not set
    if settings.cohort_start is None and settings.last_12_months:
        first_tag = settings.last_12_months[0]
        dt = datetime.strptime(first_tag, "%b%y")
        settings.cohort_start = dt.strftime("%Y-%m")
        logger.info("Auto-detected cohort_start: %s", settings.cohort_start)
    elif settings.cohort_start is None and "Date Opened" in df.columns:
        earliest = pd.to_datetime(df["Date Opened"], errors="coerce").min()
        if pd.notna(earliest):
            settings.cohort_start = earliest.strftime("%Y-%m")
            logger.info("Derived cohort_start from data: %s", settings.cohort_start)

    # Step 2: Build pre-filtered DataFrames
    logger.info("[2/5] Filtering data...")
    if on_progress:
        on_progress(1, 5, "Filtering data...")
    ics_all = get_ics_accounts(df)
    open_codes = settings.open_stat_codes
    ics_stat_o = get_ics_stat_o(df, open_codes=open_codes)
    ics_stat_o_debit = get_ics_stat_o_debit(df, open_codes=open_codes)
    logger.info(
        "Filters: %d ICS total, %d stat O, %d stat O + debit",
        len(ics_all),
        len(ics_stat_o),
        len(ics_stat_o_debit),
    )

    # Step 3: Run analyses
    from ics_toolkit.analysis.analyses import ANALYSIS_REGISTRY

    logger.info("[3/5] Running %d analyses...", len(ANALYSIS_REGISTRY) + 1)
    if on_progress:
        on_progress(2, 5, "Running analyses...")
    analyses = run_all_analyses(
        df,
        ics_all,
        ics_stat_o,
        ics_stat_o_debit,
        settings,
        on_progress=None,
    )
    successful = [a for a in analyses if a.error is None]
    failed = [a for a in analyses if a.error is not None]
    if failed:
        for a in failed:
            logger.warning("Skipped: %s (%s)", a.name, a.error)
    logger.info("%d/%d analyses completed", len(successful), len(analyses))

    # Step 4: Build charts
    charts: dict[str, go.Figure] = {}
    if skip_charts:
        logger.info("[4/5] Skipping charts (--no-charts)")
    else:
        logger.info("[4/5] Building charts...")
        if on_progress:
            on_progress(3, 5, "Building charts...")
        try:
            charts = create_charts(analyses, settings)
            logger.info("Built %d charts", len(charts))
        except Exception as e:
            logger.error("Chart generation failed: %s", e, exc_info=True)

    # Step 4b: Render chart PNGs via matplotlib
    chart_pngs: dict[str, bytes] = {}
    if not skip_charts and charts:
        logger.info("[4b/5] Rendering %d chart PNGs...", len(charts))
        if on_progress:
            on_progress(3, 5, "Rendering chart PNGs...")
        try:
            chart_pngs = render_all_chart_pngs(charts)
            logger.info("Rendered %d chart PNGs", len(chart_pngs))
        except Exception as e:
            logger.error("Chart PNG rendering failed: %s", e, exc_info=True)

    return AnalysisPipelineResult(
        settings=settings,
        df=df,
        analyses=analyses,
        charts=charts,
        chart_pngs=chart_pngs,
    )


def export_outputs(
    result: AnalysisPipelineResult,
    skip_charts: bool = False,
) -> list[Path]:
    """Export pipeline results to configured output formats.

    Returns list of generated file paths.
    """
    settings = result.settings
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    date_str = datetime.now().strftime("%Y%m%d")
    client_id = settings.client_id or "unknown"

    logger.info("[5/5] Exporting reports...")

    # Save charts as interactive HTML files
    if not skip_charts and result.charts:
        logger.info("Saving %d charts as HTML...", len(result.charts))
        html_paths = save_charts_html(result.charts, settings.output_dir)
        logger.info("Saved %d chart HTML files to charts/", len(html_paths))

    if settings.outputs.excel:
        try:
            from ics_toolkit.analysis.exports.excel import write_excel_report

            logger.info("Writing Excel report...")
            path = settings.output_dir / f"{client_id}_ICS_Report_{date_str}.xlsx"
            write_excel_report(
                settings,
                result.df,
                result.analyses,
                output_path=path,
                chart_pngs=result.chart_pngs,
            )
            generated.append(path)
        except Exception as e:
            logger.error("Excel report failed: %s", e, exc_info=True)

    if settings.outputs.powerpoint:
        try:
            from ics_toolkit.analysis.exports.pptx import write_pptx_report

            logger.info("Writing PowerPoint report...")
            path = settings.output_dir / f"{client_id}_ICS_Presentation_{date_str}.pptx"
            write_pptx_report(
                settings,
                result.analyses,
                output_path=path,
                chart_pngs=result.chart_pngs,
            )
            generated.append(path)
        except Exception as e:
            logger.error("PowerPoint report failed: %s", e, exc_info=True)

    return generated
