"""Merge REF and DM account hashes into a combined ICS list."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ics_toolkit.append.column_detect import detect_file_by_keywords, extract_accounts
from ics_toolkit.append.normalizer import normalize_hash
from ics_toolkit.settings import AppendSettings as Settings

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of merging REF and DM files for a single client."""

    client_id: str
    merged_df: pd.DataFrame
    ref_count: int = 0
    dm_count: int = 0
    ref_file: str = ""
    dm_file: str = ""
    ref_status: str = "Missing"
    dm_status: str = "Missing"

    @property
    def total(self) -> int:
        return len(self.merged_df)


def merge_sources(
    ref_series: pd.Series | None,
    dm_series: pd.Series | None,
) -> pd.DataFrame:
    """Merge REF and DM account hashes into a combined DataFrame.

    Returns DataFrame with columns: ["Acct Hash", "Source"].
    Deduplicates by normalized hash, tagging accounts in both as "Both".
    """
    parts: list[pd.DataFrame] = []
    if ref_series is not None and len(ref_series) > 0:
        parts.append(pd.DataFrame({"Acct Hash": ref_series.astype(str), "Source": "REF"}))
    if dm_series is not None and len(dm_series) > 0:
        parts.append(pd.DataFrame({"Acct Hash": dm_series.astype(str), "Source": "DM"}))

    if not parts:
        return pd.DataFrame(columns=["Acct Hash", "Source"])

    df = pd.concat(parts, ignore_index=True)
    df["_norm"] = df["Acct Hash"].apply(normalize_hash)

    # Drop empty normalized hashes, then deduplicate
    df = df[df["_norm"].astype(bool)]

    # Determine source per normalized hash: "Both" if seen in multiple sources
    source_counts = df.groupby("_norm")["Source"].nunique()
    both_norms = set(source_counts[source_counts > 1].index)

    # Keep first occurrence per normalized hash
    deduped = df.drop_duplicates(subset="_norm", keep="first").copy()
    deduped.loc[deduped["_norm"].isin(both_norms), "Source"] = "Both"

    return deduped[["Acct Hash", "Source"]].reset_index(drop=True)


def merge_client_files(
    client_dir: Path,
    client_id: str,
    settings: Settings,
) -> MergeResult:
    """Detect, read, and merge REF+DM files from a client directory."""
    client_config = settings.get_client(client_id)
    files = [f for f in client_dir.iterdir() if f.is_file()]

    # Detect REF file
    ref_file = detect_file_by_keywords(files, settings.default_ref_keywords)
    ref_series = None
    ref_status = "Missing"
    ref_count = 0

    if ref_file is not None:
        ref_status = "Present"
        ref_series = extract_accounts(
            ref_file,
            column=client_config.ref_column,
            header_row=client_config.ref_header_row,
            hash_min_length=settings.hash_min_length,
        )
        ref_count = len(ref_series)
        if ref_count == 0:
            logger.warning("%s: REF file %s produced no accounts", client_id, ref_file.name)
    else:
        logger.info("%s: No REF file found", client_id)

    # Detect DM file
    dm_file = detect_file_by_keywords(files, settings.default_dm_keywords)
    dm_series = None
    dm_status = "Missing"
    dm_count = 0

    if dm_file is not None:
        dm_status = "Present"
        dm_series = extract_accounts(
            dm_file,
            column=client_config.dm_column,
            header_row=client_config.dm_header_row,
            hash_min_length=settings.hash_min_length,
        )
        dm_count = len(dm_series)
        if dm_count == 0:
            logger.warning("%s: DM file %s produced no accounts", client_id, dm_file.name)
    else:
        logger.info("%s: No DM file found", client_id)

    merged_df = merge_sources(ref_series, dm_series)

    logger.info(
        "%s: REF=%d, DM=%d, Total merged=%d",
        client_id,
        ref_count,
        dm_count,
        len(merged_df),
    )

    return MergeResult(
        client_id=client_id,
        merged_df=merged_df,
        ref_count=ref_count,
        dm_count=dm_count,
        ref_file=ref_file.name if ref_file else "",
        dm_file=dm_file.name if dm_file else "",
        ref_status=ref_status,
        dm_status=dm_status,
    )
