"""Step: Create filtered DataFrame subsets from the loaded ODD data."""

from __future__ import annotations

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
    if "Stat Code" in df.columns:
        subs.open_accounts = df[df["Stat Code"].astype(str).str.upper().str.startswith("O", na=False)]
        logger.debug("Open accounts: {n:,} rows", n=len(subs.open_accounts))

    # Eligible accounts based on client config
    eligible_stats = ctx.client.eligible_stat_codes
    eligible_prods = ctx.client.eligible_prod_codes

    if eligible_stats and "Stat Code" in df.columns:
        mask = df["Stat Code"].astype(str).str.strip().isin(eligible_stats)
        if eligible_prods and "Product Code" in df.columns:
            mask = mask & df["Product Code"].astype(str).str.strip().isin(eligible_prods)
        subs.eligible_data = df[mask]
        logger.debug("Eligible data: {n:,} rows", n=len(subs.eligible_data))

        # Personal/Business splits
        if "Business?" in df.columns and subs.eligible_data is not None:
            elig = subs.eligible_data
            biz_mask = elig["Business?"].astype(str).str.strip().str.upper().isin(("YES", "Y"))
            subs.eligible_business = elig[biz_mask]
            subs.eligible_personal = elig[~biz_mask]
            logger.debug(
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
        if dc_col in df.columns and subs.eligible_data is not None:
            subs.eligible_with_debit = subs.eligible_data[
                subs.eligible_data[dc_col].astype(str).str.strip().str.upper().isin(
                    ("D", "DC", "DEBIT", "YES", "Y")
                )
            ]
            logger.debug(
                "Eligible with debit: {n:,} rows",
                n=len(subs.eligible_with_debit),
            )

    # Last 12 months filter
    if "Date Opened" in df.columns and ctx.end_date is not None:
        from dateutil.relativedelta import relativedelta

        cutoff = ctx.end_date - relativedelta(months=12)
        subs.last_12_months = df[df["Date Opened"] >= str(cutoff)]
        logger.debug("Last 12 months: {n:,} rows", n=len(subs.last_12_months))

    ctx.subsets = subs
    logger.info("Subsets created for {client}", client=ctx.client.client_id)
