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

    # Open accounts (Stat Code == "O" or starts with "O")
    if "Stat Code" in df.columns:
        subs.open_accounts = df[df["Stat Code"].str.upper().str.startswith("O", na=False)]
        logger.debug("Open accounts: {n:,} rows", n=len(subs.open_accounts))

    # Eligible accounts based on client config
    eligible_stats = ctx.client.eligible_stat_codes
    eligible_prods = ctx.client.eligible_prod_codes

    if eligible_stats and "Stat Code" in df.columns:
        mask = df["Stat Code"].isin(eligible_stats)
        if eligible_prods and "Product Code" in df.columns:
            mask = mask & df["Product Code"].isin(eligible_prods)
        subs.eligible_data = df[mask]
        logger.debug("Eligible data: {n:,} rows", n=len(subs.eligible_data))

        # Personal/Business splits
        if "Business?" in df.columns and subs.eligible_data is not None:
            elig = subs.eligible_data
            biz_mask = elig["Business?"].str.strip().str.upper().isin(("YES", "Y"))
            subs.eligible_business = elig[biz_mask]
            subs.eligible_personal = elig[~biz_mask]
            logger.debug(
                "Eligible split: {p:,} personal, {b:,} business",
                p=len(subs.eligible_personal),
                b=len(subs.eligible_business),
            )

        # Eligible with debit indicator
        dc_col = ctx.client.dc_indicator
        if dc_col in df.columns and subs.eligible_data is not None:
            subs.eligible_with_debit = subs.eligible_data[
                subs.eligible_data[dc_col].str.strip().str.upper().isin(("D", "DC", "DEBIT"))
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
