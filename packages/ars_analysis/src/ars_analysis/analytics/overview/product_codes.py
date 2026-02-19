"""A1b: Product Code Distribution -- mirrors stat_codes.py for product codes."""

from __future__ import annotations

import pandas as pd
from loguru import logger
from matplotlib.ticker import FuncFormatter

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.charts.style import TEAL
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
    """Product code breakdown with personal/business split."""

    module_id = "overview.product_codes"
    display_name = "Product Code Distribution"
    section = "overview"
    required_columns = ("Product Code", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A1b: Product Code Distribution for {client}", client=ctx.client.client_id)
        data = ctx.data.copy()
        data["Product Code"] = data["Product Code"].fillna("Unknown")
        data["Business?"] = data["Business?"].fillna("Unknown")

        grouped = (
            data.groupby(["Product Code", "Business?"])
            .size()
            .reset_index(name="Total Count")
        )
        total = grouped["Total Count"].sum()

        output_rows: list[dict] = []
        summary_rows: list[dict] = []

        for pc in grouped["Product Code"].unique():
            rows = grouped[grouped["Product Code"] == pc]
            prod_total = rows["Total Count"].sum()
            output_rows.append({
                "Product Code": pc,
                "Account Type": "All",
                "Total Count": prod_total,
                "Percent of Product": prod_total / total if total else 0,
            })

            biz, pers = 0, 0
            for _, r in rows.iterrows():
                label = _BUSINESS_LABELS.get(str(r["Business?"]).strip(), str(r["Business?"]))
                cnt = r["Total Count"]
                if label == "Business":
                    biz = cnt
                elif label == "Personal":
                    pers = cnt
                output_rows.append({
                    "Product Code": pc,
                    "Account Type": f"  -> {label}",
                    "Total Count": cnt,
                    "Percent of Product": cnt / prod_total if prod_total else 0,
                })

            summary_rows.append({
                "Product Code": pc,
                "Total Count": prod_total,
                "Percent of Total": prod_total / total if total else 0,
                "Business Count": biz,
                "Personal Count": pers,
            })

        distribution = pd.DataFrame(output_rows).sort_values(["Product Code", "Account Type"])
        summary = (
            pd.DataFrame(summary_rows)
            .sort_values("Total Count", ascending=False)
            .reset_index(drop=True)
        )

        # Chart
        chart_path = None
        if ctx.paths.charts_dir != ctx.paths.base_dir:
            ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)
            save_to = ctx.paths.charts_dir / "a1b_product_code.png"
            try:
                top10 = summary.head(10).sort_values("Total Count", ascending=True)
                with chart_figure(save_path=save_to) as (fig, ax):
                    ax.barh(
                        top10["Product Code"].astype(str),
                        top10["Total Count"],
                        color=TEAL,
                    )
                    ax.set_xlabel("Count")
                    ax.set_title("Product Code Distribution - Top 10")
                    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{x:,.0f}"))
                    for i, (cnt, pct) in enumerate(
                        zip(top10["Total Count"], top10["Percent of Total"])
                    ):
                        ax.text(
                            cnt + top10["Total Count"].max() * 0.01,
                            i,
                            f"{cnt:,.0f} ({pct:.1%})",
                            va="center",
                            fontsize=9,
                        )
                chart_path = save_to
            except Exception as exc:
                logger.warning("A1b chart failed: {err}", err=exc)

        # Insights
        top_code = summary.iloc[0]["Product Code"] if len(summary) > 0 else "N/A"
        top_pct = summary.iloc[0]["Percent of Total"] if len(summary) > 0 else 0
        top3_pct = summary.head(3)["Percent of Total"].sum() if len(summary) >= 3 else 0
        total_personal = summary["Personal Count"].sum()
        total_business = summary["Business Count"].sum()

        notes = (
            f"Top product '{top_code}': {top_pct:.1%}. "
            f"Top 3: {top3_pct:.1%}. "
            f"Personal: {total_personal:,} | Business: {total_business:,}"
        )

        result = AnalysisResult(
            slide_id="A1b",
            title="Product Code Distribution",
            chart_path=chart_path,
            excel_data={"Distribution": distribution, "Summary": summary},
            notes=notes,
        )

        logger.info(
            "A1b complete -- {n} product codes, top: {top} ({pct:.1%})",
            n=len(summary),
            top=top_code,
            pct=top_pct,
        )
        return [result]
