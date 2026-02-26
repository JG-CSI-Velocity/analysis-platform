"""Step: Create filtered DataFrame subsets from the loaded ODD data."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.exceptions import DataError
from ars_analysis.pipeline.context import DataSubsets, PipelineContext


def step_subsets(ctx: PipelineContext) -> None:
    """Build common filtered views and store in ctx.subsets.

    With Copy-on-Write enabled, these are zero-copy views until mutated.
    No .copy() calls needed.
    """
    if ctx.data is None:
        raise DataError("Cannot create subsets: no data loaded")

    df = ctx.data
    subs = DataSubsets()

    # Auto-compute date range using TODAY as reference (enables L12M everywhere).
    # Snap to LAST 12 COMPLETED calendar months relative to the current date.
    # e.g. if today is Feb 23, 2026 -> L12M = Feb 1, 2025 - Jan 31, 2026.
    # Store as pd.Timestamp so downstream comparisons against datetime64 columns work.
    if "Date Opened" in df.columns and ctx.end_date is None:
        from dateutil.relativedelta import relativedelta

        today = pd.Timestamp.now().normalize()
        _first_of_current = today.replace(day=1)
        # End of previous complete month
        ctx.end_date = _first_of_current - pd.Timedelta(days=1)
        # Start = first of month, 12 months before end_date's month
        ctx.start_date = pd.Timestamp(ctx.end_date.replace(day=1) - relativedelta(months=11))
        logger.info(
            "Auto-computed date range: {start} to {end} (last 12 completed months from today)",
            start=ctx.start_date,
            end=ctx.end_date,
        )

    # Open accounts: Date Closed is blank OR Stat Code starts with "O"
    _stat_col = "Stat Code" if "Stat Code" in df.columns else None
    if not _stat_col:
        for _alt in ("Status Code", "StatCode", "Stat_Code", "Account Status"):
            if _alt in df.columns:
                _stat_col = _alt
                logger.info("Auto-detected stat column: {col}", col=_stat_col)
                break

    _open_mask = pd.Series(False, index=df.index)

    if _stat_col:
        _stat_values = df[_stat_col].astype(str).str.strip()
        _stat_upper = _stat_values.str.upper()
        _unique_stats = _stat_values.value_counts().head(10)
        logger.info(
            "Stat Code column '{col}' -- top values: {vals}",
            col=_stat_col,
            vals=dict(_unique_stats),
        )
        _open_mask = _open_mask | _stat_upper.str.startswith("O", na=False)

    if "Date Closed" in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df["Date Closed"]):
            _dc_parsed = df["Date Closed"]
        else:
            _dc_parsed = pd.to_datetime(df["Date Closed"], errors="coerce", format="mixed")
        _open_mask = _open_mask | _dc_parsed.isna()

    subs.open_accounts = df[_open_mask]
    logger.info("Open accounts: {n:,} rows", n=len(subs.open_accounts))

    if not _stat_col and "Date Closed" not in df.columns:
        logger.warning(
            "No 'Stat Code' or 'Date Closed' column found. Columns: {cols}",
            cols=list(df.columns)[:20],
        )

    # Eligible accounts based on client config
    eligible_stats = ctx.client.eligible_stat_codes
    eligible_prods = ctx.client.eligible_prod_codes

    if not eligible_stats and _stat_col:
        logger.warning(
            "No EligibleStatusCodes configured -- eligible_data will be None. Check client config."
        )

    if eligible_stats and _stat_col:
        # Case-insensitive matching: uppercase both config values and data
        _cfg_upper = [s.strip().upper() for s in eligible_stats]
        mask = _stat_upper.isin(_cfg_upper)
        _match_count = mask.sum()
        logger.info(
            "Eligible stat filter: config={cfg} -> {n:,} matches out of {total:,}",
            cfg=eligible_stats,
            n=_match_count,
            total=len(df),
        )

        if eligible_prods and "Product Code" in df.columns:
            _prod_upper = [s.strip().upper() for s in eligible_prods]
            _prod_mask = df["Product Code"].astype(str).str.strip().str.upper().isin(_prod_upper)
            mask = mask & _prod_mask
            logger.info(
                "Eligible prod filter: config={cfg} -> {n:,} matches after both filters",
                cfg=eligible_prods,
                n=mask.sum(),
            )

        subs.eligible_data = df[mask]
        logger.info("Eligible data: {n:,} rows", n=len(subs.eligible_data))

        # Personal/Business splits
        if "Business?" in df.columns and subs.eligible_data is not None:
            elig = subs.eligible_data
            biz_mask = elig["Business?"].astype(str).str.strip().str.upper().isin(("YES", "Y"))
            subs.eligible_business = elig[biz_mask]
            subs.eligible_personal = elig[~biz_mask]
            logger.info(
                "Eligible split: {p:,} personal, {b:,} business",
                p=len(subs.eligible_personal),
                b=len(subs.eligible_business),
            )

        # Eligible with debit indicator -- auto-detect column
        dc_col = ctx.client.dc_indicator
        if dc_col not in df.columns:
            for candidate in ("Debit?", "Debit", "DC Indicator", "DC_Indicator"):
                if candidate in df.columns:
                    dc_col = candidate
                    logger.info("Auto-detected debit column: {col}", col=dc_col)
                    break
        if dc_col in df.columns:
            ctx.debit_column = dc_col
        if dc_col in df.columns and subs.eligible_data is not None:
            subs.eligible_with_debit = subs.eligible_data[
                subs.eligible_data[dc_col]
                .astype(str)
                .str.strip()
                .str.upper()
                .isin(("D", "DC", "DEBIT", "YES", "Y"))
            ]
            logger.info(
                "Eligible with debit: {n:,} rows",
                n=len(subs.eligible_with_debit),
            )

    # Last 12 months filter
    if "Date Opened" in df.columns and ctx.end_date is not None:
        cutoff = (
            pd.Timestamp(ctx.start_date)
            if ctx.start_date is not None
            else ctx.end_date - pd.DateOffset(months=12)
        )
        if pd.api.types.is_datetime64_any_dtype(df["Date Opened"]):
            _do_parsed = df["Date Opened"]
        else:
            _do_parsed = pd.to_datetime(df["Date Opened"], errors="coerce", format="mixed")
        subs.last_12_months = df[_do_parsed >= cutoff]
        logger.info(
            "Last 12 months: {n:,} rows (cutoff={cutoff})",
            n=len(subs.last_12_months),
            cutoff=cutoff,
        )

    ctx.subsets = subs
    logger.info("Subsets created for {client}", client=ctx.client.client_id)
