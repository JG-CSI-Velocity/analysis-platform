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

    # Auto-compute date range from data (enables L12M everywhere)
    if "Date Opened" in df.columns and ctx.end_date is None:
        date_col = df["Date Opened"].dropna()
        if not date_col.empty:
            from dateutil.relativedelta import relativedelta

            ctx.end_date = date_col.max().date()
            ctx.start_date = ctx.end_date - relativedelta(months=12)
            logger.info(
                "Auto-computed date range: {start} to {end}",
                start=ctx.start_date,
                end=ctx.end_date,
            )

    # Open accounts (Stat Code == "O" or starts with "O")
    _stat_col = "Stat Code" if "Stat Code" in df.columns else None
    if not _stat_col:
        # Auto-detect common alternatives
        for _alt in ("Status Code", "StatCode", "Stat_Code", "Account Status"):
            if _alt in df.columns:
                _stat_col = _alt
                logger.info("Auto-detected stat column: {col}", col=_stat_col)
                break

    if _stat_col:
        _stat_values = df[_stat_col].astype(str).str.strip()
        _stat_upper = _stat_values.str.upper()
        _unique_stats = _stat_values.value_counts().head(10)
        logger.info(
            "Stat Code column '{col}' -- top values: {vals}",
            col=_stat_col,
            vals=dict(_unique_stats),
        )

        subs.open_accounts = df[_stat_upper.str.startswith("O", na=False)]
        logger.info("Open accounts (via Stat Code): {n:,} rows", n=len(subs.open_accounts))

    # Fallback: if Stat Code detection yielded 0 rows, use Date Closed (NaT = open)
    if (subs.open_accounts is None or subs.open_accounts.empty) and "Date Closed" in df.columns:
        _dc_col = pd.to_datetime(df["Date Closed"], errors="coerce")
        subs.open_accounts = df[_dc_col.isna()]
        logger.info(
            "Open accounts (via Date Closed NaT fallback): {n:,} rows",
            n=len(subs.open_accounts),
        )

    if subs.open_accounts is None:
        logger.warning("No 'Stat Code' column found. Columns: {cols}", cols=list(df.columns)[:20])

    # Eligible accounts based on client config
    eligible_stats = ctx.client.eligible_stat_codes
    eligible_prods = ctx.client.eligible_prod_codes

    if not eligible_stats and _stat_col:
        logger.warning(
            "No EligibleStatusCodes configured -- eligible_data will be None. "
            "Check client config."
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
                subs.eligible_data[dc_col].astype(str).str.strip().str.upper().isin(
                    ("D", "DC", "DEBIT", "YES", "Y")
                )
            ]
            logger.info(
                "Eligible with debit: {n:,} rows",
                n=len(subs.eligible_with_debit),
            )

    # Last 12 months filter
    if "Date Opened" in df.columns and ctx.end_date is not None:
        from dateutil.relativedelta import relativedelta

        cutoff = ctx.end_date - relativedelta(months=12)
        subs.last_12_months = df[df["Date Opened"] >= str(cutoff)]
        logger.info("Last 12 months: {n:,} rows (cutoff={cutoff})", n=len(subs.last_12_months), cutoff=cutoff)

    ctx.subsets = subs
    logger.info("Subsets created for {client}", client=ctx.client.client_id)
