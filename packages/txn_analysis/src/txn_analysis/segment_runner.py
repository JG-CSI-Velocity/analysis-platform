"""Run analyses on filtered account segments for comparative analysis.

Wraps ``run_all_analyses()`` -- runs the existing 35 analyses on
the full population and on each segment subset.  Zero changes to any
individual analysis function.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from txn_analysis.analyses import run_all_analyses
from txn_analysis.analyses.base import AnalysisResult
from txn_analysis.segments import SegmentFilter
from txn_analysis.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SegmentedResult:
    """Container for one segment's full analysis run."""

    segment: str  # "full_population" | segment.name
    label: str  # "Full Population" | segment.label
    analyses: list[AnalysisResult]
    account_count: int
    transaction_count: int


def run_segmented_analyses(
    df: pd.DataFrame,
    settings: Settings,
    odd_df: pd.DataFrame | None,
    segments: list[SegmentFilter],
) -> list[SegmentedResult]:
    """Run full population + each segment through the analysis pipeline.

    Returns a list of SegmentedResult, one per population slice.
    The first entry is always the full population (unfiltered).
    """
    results: list[SegmentedResult] = []

    # Full population (always first)
    logger.info("Running analyses on full population (%d transactions)", len(df))
    full_analyses = run_all_analyses(df, settings, odd_df=odd_df)
    results.append(
        SegmentedResult(
            segment="full_population",
            label="Full Population",
            analyses=full_analyses,
            account_count=df["primary_account_num"].nunique()
            if "primary_account_num" in df.columns
            else 0,
            transaction_count=len(df),
        )
    )

    # Each segment
    for seg in segments:
        seg_df = seg.filter_transactions(df)
        if seg_df.empty:
            logger.warning("Segment '%s' produced 0 transactions -- skipping", seg.name)
            continue

        logger.info(
            "Running analyses on segment '%s' (%d transactions, %d accounts)",
            seg.name,
            len(seg_df),
            len(seg.account_numbers),
        )
        seg_analyses = run_all_analyses(seg_df, settings, odd_df=odd_df)
        tagged = [_tag_result(a, seg.label) for a in seg_analyses]
        results.append(
            SegmentedResult(
                segment=seg.name,
                label=seg.label,
                analyses=tagged,
                account_count=len(seg.account_numbers),
                transaction_count=len(seg_df),
            )
        )

    logger.info(
        "Segmented analysis complete: %d populations (%s)",
        len(results),
        ", ".join(r.label for r in results),
    )
    return results


def _tag_result(result: AnalysisResult, segment_label: str) -> AnalysisResult:
    """Prefix an analysis result's name and title with the segment label."""
    tagged_name = f"{result.name}__{segment_label.lower().replace(' ', '_')}"
    tagged_title = f"[{segment_label}] {result.title}" if result.title else result.title
    meta = dict(result.metadata) if result.metadata else {}
    meta["segment"] = segment_label
    return AnalysisResult(
        name=tagged_name,
        title=tagged_title,
        data=result.data,
        charts=result.charts,
        error=result.error,
        summary=result.summary,
        metadata=meta,
    )
