"""Referral intelligence pipeline orchestrator."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from ics_toolkit.analysis.analyses.base import AnalysisResult
from ics_toolkit.referral.analyses import run_all_referral_analyses
from ics_toolkit.referral.analyses.base import ReferralContext
from ics_toolkit.referral.charts import create_referral_charts
from ics_toolkit.referral.code_decoder import decode_referral_codes
from ics_toolkit.referral.data_loader import load_referral_data
from ics_toolkit.referral.network import infer_networks
from ics_toolkit.referral.normalizer import normalize_entities
from ics_toolkit.referral.scoring import (
    compute_influence_scores,
    compute_referrer_metrics,
    compute_staff_multipliers,
)
from ics_toolkit.referral.temporal import add_temporal_signals
from ics_toolkit.settings import ReferralSettings

logger = logging.getLogger(__name__)


@dataclass
class ReferralPipelineResult:
    """Result of the referral intelligence pipeline."""

    settings: ReferralSettings
    df: pd.DataFrame
    referrer_metrics: pd.DataFrame
    staff_metrics: pd.DataFrame
    analyses: list[AnalysisResult] = field(default_factory=list)
    charts: dict[str, go.Figure] = field(default_factory=dict)
    chart_pngs: dict[str, bytes] = field(default_factory=dict)


def run_pipeline(
    settings: ReferralSettings,
    on_progress: Callable[[int, int, str], None] | None = None,
    skip_charts: bool = False,
) -> ReferralPipelineResult:
    """Execute the referral intelligence pipeline.

    Steps:
    1. Load + validate data
    2. Entity normalization
    3. Code decoding
    4. Temporal signals
    5. Network inference
    6. Influence scoring + staff multipliers
    7. Run 8 analysis artifacts
    8. Build charts + render PNGs
    """
    total_steps = 7 if skip_charts else 8

    # Step 1: Load data
    logger.info("[1/%d] Loading referral data...", total_steps)
    if on_progress:
        on_progress(0, total_steps, "Loading referral data...")
    df = load_referral_data(settings)
    logger.info("Loaded %d referral records", len(df))

    # Step 2: Entity normalization
    logger.info("[2/%d] Normalizing entities...", total_steps)
    if on_progress:
        on_progress(1, total_steps, "Normalizing entities...")
    df = normalize_entities(df, settings)

    # Step 3: Code decoding
    logger.info("[3/%d] Decoding referral codes...", total_steps)
    if on_progress:
        on_progress(2, total_steps, "Decoding referral codes...")
    df = decode_referral_codes(df, settings)

    # Step 4: Temporal signals
    logger.info("[4/%d] Computing temporal signals...", total_steps)
    if on_progress:
        on_progress(3, total_steps, "Computing temporal signals...")
    df = add_temporal_signals(df, settings)

    # Step 5: Network inference
    logger.info("[5/%d] Inferring referral networks...", total_steps)
    if on_progress:
        on_progress(4, total_steps, "Inferring networks...")
    df = infer_networks(df)

    # Step 6: Scoring
    logger.info("[6/%d] Computing influence scores...", total_steps)
    if on_progress:
        on_progress(5, total_steps, "Computing influence scores...")
    referrer_metrics = compute_referrer_metrics(df)
    referrer_metrics = compute_influence_scores(referrer_metrics, settings.scoring_weights)
    staff_metrics = compute_staff_multipliers(df, referrer_metrics, settings.staff_weights)
    logger.info(
        "Scored %d referrers, %d staff members",
        len(referrer_metrics),
        len(staff_metrics),
    )

    # Step 7: Run analyses
    logger.info("[7/%d] Running 8 referral analyses...", total_steps)
    if on_progress:
        on_progress(6, total_steps, "Running analyses...")
    ctx = ReferralContext(
        df=df,
        referrer_metrics=referrer_metrics,
        staff_metrics=staff_metrics,
        settings=settings,
    )
    analyses = run_all_referral_analyses(ctx)
    successful = [a for a in analyses if a.error is None]
    failed = [a for a in analyses if a.error is not None]
    if failed:
        for a in failed:
            logger.warning("Skipped: %s (%s)", a.name, a.error)
    logger.info("%d/%d analyses completed", len(successful), len(analyses))

    # Step 8: Charts
    charts: dict[str, go.Figure] = {}
    chart_pngs: dict[str, bytes] = {}
    if skip_charts:
        logger.info("[8/%d] Skipping charts (--no-charts)", total_steps)
    else:
        logger.info("[8/%d] Building charts...", total_steps)
        if on_progress:
            on_progress(7, total_steps, "Building charts...")
        try:
            charts = create_referral_charts(analyses, settings.charts)
            logger.info("Built %d charts", len(charts))
        except Exception as e:
            logger.error("Chart generation failed: %s", e, exc_info=True)

        if charts:
            from ics_toolkit.analysis.charts.renderer import render_all_chart_pngs

            try:
                chart_pngs = render_all_chart_pngs(charts)
                logger.info("Rendered %d chart PNGs", len(chart_pngs))
            except Exception as e:
                logger.error("Chart PNG rendering failed: %s", e, exc_info=True)

    return ReferralPipelineResult(
        settings=settings,
        df=df,
        referrer_metrics=referrer_metrics,
        staff_metrics=staff_metrics,
        analyses=analyses,
        charts=charts,
        chart_pngs=chart_pngs,
    )


def export_outputs(
    result: ReferralPipelineResult,
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

    if settings.outputs.excel:
        try:
            from ics_toolkit.referral.exports.excel import write_referral_excel

            logger.info("Writing referral Excel report...")
            path = settings.output_dir / f"{client_id}_Referral_Intelligence_{date_str}.xlsx"
            write_referral_excel(
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
            from ics_toolkit.referral.exports.pptx import write_referral_pptx

            logger.info("Writing referral PowerPoint report...")
            path = settings.output_dir / f"{client_id}_Referral_Intelligence_{date_str}.pptx"
            write_referral_pptx(
                settings,
                result.analyses,
                output_path=path,
                chart_pngs=result.chart_pngs,
            )
            generated.append(path)
        except Exception as e:
            logger.error("PowerPoint report failed: %s", e, exc_info=True)

    return generated
