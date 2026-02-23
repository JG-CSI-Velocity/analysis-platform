"""A1b: Product Code Distribution -- Excel-only detail supplement to A1.

The combined chart is rendered by stat_codes.py (A1).  This module provides
the detailed distribution breakdown (with personal/business split) as Excel
data and stores the summary for downstream modules.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.pipeline.context import PipelineContext

_BUSINESS_LABELS = {
    "Yes": "Business",
    "No": "Personal",
    "Y": "Business",
    "N": "Personal",
    "": "Unknown",
    "Unknown": "Unknown",
}


@register
class ProductCodeDistribution(AnalysisModule):
    """Product code breakdown -- Excel detail only (chart is in A1)."""

    module_id = "overview.product_codes"
    display_name = "Product Code Distribution"
    section = "overview"
    required_columns = ("Product Code", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A1b: Product Code Distribution for {client}", client=ctx.client.client_id)
        data = ctx.data.copy()
        data["Product Code"] = data["Product Code"].fillna("Unknown")
        data["Business?"] = data["Business?"].fillna("Unknown")

        grouped = data.groupby(["Product Code", "Business?"]).size().reset_index(name="Total Count")
        total = grouped["Total Count"].sum()

        output_rows: list[dict] = []
        summary_rows: list[dict] = []

        for pc in grouped["Product Code"].unique():
            rows = grouped[grouped["Product Code"] == pc]
            prod_total = rows["Total Count"].sum()
            output_rows.append(
                {
                    "Product Code": pc,
                    "Account Type": "All",
                    "Total Count": prod_total,
                    "Percent of Product": prod_total / total if total else 0,
                }
            )

            biz, pers = 0, 0
            for _, r in rows.iterrows():
                label = _BUSINESS_LABELS.get(str(r["Business?"]).strip(), str(r["Business?"]))
                cnt = r["Total Count"]
                if label == "Business":
                    biz = cnt
                elif label == "Personal":
                    pers = cnt
                output_rows.append(
                    {
                        "Product Code": pc,
                        "Account Type": f"  -> {label}",
                        "Total Count": cnt,
                        "Percent of Product": cnt / prod_total if prod_total else 0,
                    }
                )

            summary_rows.append(
                {
                    "Product Code": pc,
                    "Total Count": prod_total,
                    "Percent of Total": prod_total / total if total else 0,
                    "Business Count": biz,
                    "Personal Count": pers,
                }
            )

        distribution = pd.DataFrame(output_rows).sort_values(["Product Code", "Account Type"])
        summary = (
            pd.DataFrame(summary_rows)
            .sort_values("Total Count", ascending=False)
            .reset_index(drop=True)
        )

        top_code = summary.iloc[0]["Product Code"] if len(summary) > 0 else "N/A"
        top_pct = summary.iloc[0]["Percent of Total"] if len(summary) > 0 else 0

        notes = (
            f"Top product '{top_code}': {top_pct:.1%}. "
            f"{len(summary)} product codes. "
            f"Total: {total:,}"
        )

        logger.info(
            "A1b complete -- {n} product codes, top: {top} ({pct:.1%})",
            n=len(summary),
            top=top_code,
            pct=top_pct,
        )
        return [
            AnalysisResult(
                slide_id="A1b",
                title="Product Code Distribution",
                # No chart_path -- visual is in A1 combined slide
                excel_data={"Distribution": distribution, "Summary": summary},
                notes=notes,
            )
        ]
