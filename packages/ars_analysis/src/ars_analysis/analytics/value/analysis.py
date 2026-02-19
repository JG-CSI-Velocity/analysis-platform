"""Value Analysis -- revenue impact of debit cards and Reg E opt-in.

Slide IDs: A11.1 (Debit Card Value), A11.2 (Reg E Value).
"""

from __future__ import annotations

import pandas as pd
from loguru import logger
from matplotlib.patches import Rectangle

from ars_analysis.analytics.base import AnalysisModule, AnalysisResult
from ars_analysis.analytics.rege._helpers import detect_reg_e_column
from ars_analysis.analytics.registry import register
from ars_analysis.charts.guards import chart_figure
from ars_analysis.pipeline.context import PipelineContext

# -- Column discovery --------------------------------------------------------


def _find_col(df: pd.DataFrame, keyword: str, period_hint: str = "12") -> str | None:
    """Find a column by keyword (e.g. 'spend', 'items') with period hint."""
    for col in df.columns:
        if keyword in col.lower() and (period_hint in col or period_hint.lower() in col.lower()):
            return col
    period_patterns = ["l12m", "12m", "12 month", "last 12", "ltm", "trailing"]
    for col in df.columns:
        cl = col.lower()
        if keyword in cl and any(p in cl for p in period_patterns):
            return col
    for col in df.columns:
        if keyword in col.lower():
            return col
    return None


# -- Comparison table chart --------------------------------------------------

COL1_COLOR = "#6B7F99"
COL2_COLOR = "#4A9B9F"
HIGHLIGHT_COLOR = "#D4A574"


def _draw_value_slide(
    fig, row_data: list[tuple], col1_header: str, col2_header: str,
    impact: dict,
) -> None:
    """Draw combined comparison table (left) + potential impact text (right).

    Draws directly into the provided figure.
    """
    # Left: comparison table
    ax_left = fig.add_axes([0.02, 0.05, 0.48, 0.90])
    ax_left.set_xlim(0, 10)
    ax_left.set_ylim(0, 10)
    ax_left.axis("off")

    ax_left.text(5, 9, col1_header, fontsize=18, fontweight="500",
                 color="#333333", ha="center")
    ax_left.text(7.5, 9, col2_header, fontsize=18, fontweight="500",
                 color="#333333", ha="center")

    n_rows = len(row_data)
    for i, (y_pos, label, with_val, without_val) in enumerate(row_data):
        ax_left.text(2.5, y_pos, label, fontsize=16, color="#333333",
                     va="center", ha="right")
        if i < n_rows - 1:
            c1, c2 = COL1_COLOR, COL2_COLOR
        else:
            c1 = c2 = HIGHLIGHT_COLOR

        rect1 = Rectangle((3.75, y_pos - 0.5), 2.25, 1, facecolor=c1, edgecolor="none")
        ax_left.add_patch(rect1)
        ax_left.text(5, y_pos, with_val, fontsize=18, color="white",
                     ha="center", va="center", fontweight="500")

        rect2 = Rectangle((6.25, y_pos - 0.5), 2.25, 1, facecolor=c2, edgecolor="none")
        ax_left.add_patch(rect2)
        ax_left.text(7.5, y_pos, without_val, fontsize=18, color="white",
                     ha="center", va="center", fontweight="500")

        if i < n_rows - 1:
            ax_left.plot([2.5, 8.5], [y_pos - 0.75, y_pos - 0.75],
                         color="#CCCCCC", linewidth=1, linestyle="--")

    # Right: potential impact
    ax_right = fig.add_axes([0.52, 0.05, 0.46, 0.90])
    ax_right.set_xlim(0, 10)
    ax_right.set_ylim(0, 10)
    ax_right.axis("off")

    awo = impact.get("awo", 0)
    delta = impact.get("delta", 0)
    hist_rate = impact.get("hist_rate", 0)
    l12m_rate = impact.get("l12m_rate", 0)
    pot_hist = impact.get("pot_hist", 0)
    pot_l12m = impact.get("pot_l12m", 0)
    pot_100 = impact.get("pot_100", awo * delta)
    rate_label = impact.get("rate_label", "DCTR")

    ax_right.text(5, 9.2, "Potential Impact", fontsize=22, fontweight="bold",
                  color="#1E3D59", ha="center")

    y = 8.0
    for label, value in [
        ("Accounts without feature", f"{awo:,}"),
        ("Revenue delta per account", f"${delta:.2f}"),
    ]:
        ax_right.text(5, y, label, fontsize=13, color="#666666", ha="center")
        y -= 0.5
        ax_right.text(5, y, value, fontsize=20, fontweight="bold",
                      color="#333333", ha="center")
        y -= 1.0

    ax_right.text(5, y, "Estimated Revenue Opportunity", fontsize=16,
                  fontweight="bold", color="#005072", ha="center")
    y -= 0.9

    for label, value in [
        (f"At {hist_rate:.0%} Historical {rate_label}", f"${pot_hist:,.0f}"),
        (f"At {l12m_rate:.0%} TTM {rate_label}", f"${pot_l12m:,.0f}"),
        ("At 100% Adoption", f"${pot_100:,.0f}"),
    ]:
        ax_right.text(5, y, label, fontsize=12, color="#666666", ha="center")
        y -= 0.5
        ax_right.text(5, y, value, fontsize=20, fontweight="bold",
                      color="#333333", ha="center")
        y -= 0.8


# -- Safe wrapper ------------------------------------------------------------


def _safe(fn, label: str, ctx: PipelineContext) -> list[AnalysisResult]:
    """Run analysis function, catch errors, return failed result on exception."""
    try:
        return fn(ctx)
    except Exception as exc:
        logger.warning("{label} failed: {err}", label=label, err=exc)
        return [AnalysisResult(
            slide_id=label, title=label, success=False, error=str(exc),
        )]


# -- Module ------------------------------------------------------------------


@register
class ValueAnalysis(AnalysisModule):
    """Revenue impact analysis -- debit card value and Reg E value."""

    module_id = "value.analysis"
    display_name = "Value Analysis"
    section = "value"
    required_columns = ("Date Opened", "Debit?", "Business?")

    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("Value Analysis for {client}", client=ctx.client.client_id)
        results: list[AnalysisResult] = []
        results += _safe(self._debit_card_value, "A11.1", ctx)
        results += _safe(self._reg_e_value, "A11.2", ctx)
        return results

    # -- A11.1: Value of a Debit Card ----------------------------------------

    def _debit_card_value(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A11.1: Value of a Debit Card")

        fee_amount = ctx.client.nsf_od_fee
        rate_amount = ctx.client.ic_rate

        ep = ctx.subsets.eligible_personal
        if ep is None or ep.empty:
            return [AnalysisResult(
                slide_id="A11.1", title="Value of a Debit Card",
                success=False, error="No eligible personal accounts",
            )]

        # L12M-active personal accounts
        df = ep.copy()
        if "Date Closed" in df.columns:
            df["Date Closed"] = pd.to_datetime(df["Date Closed"], errors="coerce")
            if ctx.start_date:
                active = df[df["Date Closed"].isna() | (df["Date Closed"] >= ctx.start_date)].copy()
            else:
                active = df.copy()
        else:
            active = df.copy()

        # Discover spend/items columns
        spend_col = _find_col(active, "spend")
        items_col = _find_col(active, "items")
        if not spend_col or not items_col:
            return [AnalysisResult(
                slide_id="A11.1", title="Value of a Debit Card",
                success=False, error="Missing spend/items columns",
            )]

        # Revenue calculation
        active["NSF/OD Revenue"] = active[items_col].fillna(0) * fee_amount
        active["Interchange Revenue"] = active[spend_col].fillna(0) * rate_amount
        active["Total Revenue"] = active["NSF/OD Revenue"] + active["Interchange Revenue"]

        rev = active.groupby("Debit?").agg(
            Accounts=("Debit?", "count"),
            NSF_OD=("NSF/OD Revenue", "sum"),
            IC=("Interchange Revenue", "sum"),
            Total=("Total Revenue", "sum"),
        )

        if "Yes" not in rev.index or "No" not in rev.index:
            return [AnalysisResult(
                slide_id="A11.1", title="Value of a Debit Card",
                success=False, error="Need both Yes and No debit groups",
            )]

        aw = int(rev.loc["Yes", "Accounts"])
        awo = int(rev.loc["No", "Accounts"])
        rw = rev.loc["Yes", "Total"]
        rwo = rev.loc["No", "Total"]
        rpw = rw / aw if aw else 0
        rpwo = rwo / awo if awo else 0
        nsf_w = rev.loc["Yes", "NSF_OD"]
        nsf_wo = rev.loc["No", "NSF_OD"]
        ic_w = rev.loc["Yes", "IC"]
        ic_wo = rev.loc["No", "IC"]
        delta = round(rpw - rpwo, 2)

        # DCTR rates from earlier results
        dctr_1 = ctx.results.get("dctr_1", {})
        hist_dctr = dctr_1.get("insights", {}).get("overall_dctr", None)
        if hist_dctr is None:
            t_ep = len(ep)
            w_ep = len(ep[ep["Debit?"] == "Yes"])
            hist_dctr = w_ep / t_ep if t_ep > 0 else 0.80

        dctr_3 = ctx.results.get("dctr_3", {})
        l12m_dctr = dctr_3.get("insights", {}).get("dctr", hist_dctr)

        pot_hist = awo * delta * hist_dctr
        pot_l12m = awo * delta * l12m_dctr
        pot_100 = awo * delta

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a11_1_debit_card_value.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        row_data = [
            (8, "Accounts", f"{aw:,}", f"{awo:,}"),
            (6.5, f"NSF/OD Revenue\n(${fee_amount})", f"${nsf_w:,.0f}", f"${nsf_wo:,.0f}"),
            (5, f"Interchange\nRevenue ({rate_amount:.4f})", f"${ic_w:,.0f}", f"${ic_wo:,.0f}"),
            (3.5, "Total Revenue", f"${rw:,.0f}", f"${rwo:,.0f}"),
            (2, "Revenue Per\nAccount", f"${rpw:.2f}", f"${rpwo:.2f}"),
        ]

        impact = {
            "awo": awo, "delta": delta,
            "hist_rate": hist_dctr, "l12m_rate": l12m_dctr,
            "pot_hist": pot_hist, "pot_l12m": pot_l12m, "pot_100": pot_100,
            "rate_label": "DCTR",
        }

        with chart_figure(figsize=(20, 8), save_path=save_to) as (fig, ax):
            ax.set_visible(False)
            _draw_value_slide(fig, row_data, "With\nDebit Card", "Without\nDebit Card", impact)
        chart_path = save_to

        # Excel
        comp_df = pd.DataFrame({
            "Debit Card Status": ["With Debit Card", "Without Debit Card"],
            "Accounts": [aw, awo],
            "NSF/OD Revenue": [nsf_w, nsf_wo],
            "Interchange Revenue": [ic_w, ic_wo],
            "Total Revenue": [rw, rwo],
            "Revenue Per Account": [rpw, rpwo],
        })

        notes = (
            f"${delta:.2f} more revenue per account with debit. "
            f"Potential at {l12m_dctr:.0%} TTM DCTR: ${pot_l12m:,.0f}"
        )

        ctx.results["value_1"] = {
            "delta": delta, "accts_with": aw, "accts_without": awo,
            "rev_per_with": rpw, "rev_per_without": rpwo,
            "hist_dctr": hist_dctr, "l12m_dctr": l12m_dctr,
            "pot_hist": pot_hist, "pot_l12m": pot_l12m, "pot_100": pot_100,
        }

        return [AnalysisResult(
            slide_id="A11.1", title="Value of a Debit Card",
            chart_path=chart_path,
            excel_data={"Comparison": comp_df},
            notes=notes,
        )]

    # -- A11.2: Value of Reg E Opt-In ----------------------------------------

    def _reg_e_value(self, ctx: PipelineContext) -> list[AnalysisResult]:
        logger.info("A11.2: Value of Reg E Opt-In")

        fee_amount = ctx.client.nsf_od_fee
        rate_amount = ctx.client.ic_rate

        # Get Reg E eligible base (personal + debit)
        ep = ctx.subsets.eligible_personal
        if ep is None or ep.empty or "Debit?" not in ep.columns:
            return [AnalysisResult(
                slide_id="A11.2", title="Value of Reg E Opt-In",
                success=False, error="No eligible personal accounts with debit data",
            )]

        base = ep[ep["Debit?"] == "Yes"].copy()
        if base.empty:
            return [AnalysisResult(
                slide_id="A11.2", title="Value of Reg E Opt-In",
                success=False, error="No personal accounts with debit cards",
            )]

        # Resolve Reg E column
        reg_e_col = ctx.client.reg_e_column
        if not reg_e_col:
            reg_e_col = detect_reg_e_column(base)
        if not reg_e_col or reg_e_col not in base.columns:
            return [AnalysisResult(
                slide_id="A11.2", title="Value of Reg E Opt-In",
                success=False, error="No Reg E column found",
            )]

        opt_in_vals = ctx.client.reg_e_opt_in
        if not opt_in_vals:
            return [AnalysisResult(
                slide_id="A11.2", title="Value of Reg E Opt-In",
                success=False, error="No Reg E opt-in codes configured",
            )]

        # L12M-active filter
        df = base.copy()
        if "Date Closed" in df.columns:
            df["Date Closed"] = pd.to_datetime(df["Date Closed"], errors="coerce")
            if ctx.start_date:
                active = df[df["Date Closed"].isna() | (df["Date Closed"] >= ctx.start_date)].copy()
            else:
                active = df.copy()
        else:
            active = df.copy()

        # Discover spend/items columns
        spend_col = _find_col(active, "spend")
        items_col = _find_col(active, "items")
        if not spend_col or not items_col:
            return [AnalysisResult(
                slide_id="A11.2", title="Value of Reg E Opt-In",
                success=False, error="Missing spend/items columns",
            )]

        # Flag Reg E status
        active["Has_RegE"] = active[reg_e_col].astype(str).str.strip().isin(opt_in_vals)

        # Revenue calculation
        active["NSF/OD Revenue"] = active[items_col].fillna(0) * fee_amount
        active["Interchange Revenue"] = active[spend_col].fillna(0) * rate_amount
        active["Total Revenue"] = active["NSF/OD Revenue"] + active["Interchange Revenue"]

        rev = active.groupby("Has_RegE").agg(
            Accounts=("Has_RegE", "count"),
            NSF_OD=("NSF/OD Revenue", "sum"),
            IC=("Interchange Revenue", "sum"),
            Total=("Total Revenue", "sum"),
        )

        if True not in rev.index or False not in rev.index:
            return [AnalysisResult(
                slide_id="A11.2", title="Value of Reg E Opt-In",
                success=False, error="Need both opted-in and opted-out groups",
            )]

        aw = int(rev.loc[True, "Accounts"])
        awo = int(rev.loc[False, "Accounts"])
        rw = rev.loc[True, "Total"]
        rwo = rev.loc[False, "Total"]
        rpw = rw / aw if aw else 0
        rpwo = rwo / awo if awo else 0
        nsf_w = rev.loc[True, "NSF_OD"]
        nsf_wo = rev.loc[False, "NSF_OD"]
        ic_w = rev.loc[True, "IC"]
        ic_wo = rev.loc[False, "IC"]
        delta = round(rpw - rpwo, 2)

        # Reg E rates from A8 results
        re1 = ctx.results.get("reg_e_1", {})
        hist_rege = re1.get("opt_in_rate", None)
        if hist_rege is None:
            total = aw + awo
            hist_rege = aw / total if total > 0 else 0.30
        l12m_rege = re1.get("l12m_rate", hist_rege)

        pot_hist = awo * delta * hist_rege
        pot_l12m = awo * delta * l12m_rege
        pot_100 = awo * delta

        # Chart
        chart_path = None
        save_to = ctx.paths.charts_dir / "a11_2_reg_e_value.png"
        ctx.paths.charts_dir.mkdir(parents=True, exist_ok=True)

        row_data = [
            (8, "Accounts", f"{aw:,}", f"{awo:,}"),
            (6.5, f"NSF/OD Revenue\n(${fee_amount})", f"${nsf_w:,.0f}", f"${nsf_wo:,.0f}"),
            (5, f"Interchange\nRevenue ({rate_amount:.4f})", f"${ic_w:,.0f}", f"${ic_wo:,.0f}"),
            (3.5, "Total Revenue", f"${rw:,.0f}", f"${rwo:,.0f}"),
            (2, "Revenue Per\nAccount", f"${rpw:.2f}", f"${rpwo:.2f}"),
        ]

        impact = {
            "awo": awo, "delta": delta,
            "hist_rate": hist_rege, "l12m_rate": l12m_rege,
            "pot_hist": pot_hist, "pot_l12m": pot_l12m, "pot_100": pot_100,
            "rate_label": "Reg E",
        }

        with chart_figure(figsize=(20, 8), save_path=save_to) as (fig, ax):
            ax.set_visible(False)
            _draw_value_slide(fig, row_data, "With\nReg E Opt-In", "Without\nReg E Opt-In", impact)
        chart_path = save_to

        # Excel
        comp_df = pd.DataFrame({
            "Reg E Status": ["With Reg E Opt-In", "Without Reg E Opt-In"],
            "Accounts": [aw, awo],
            "NSF/OD Revenue": [nsf_w, nsf_wo],
            "Interchange Revenue": [ic_w, ic_wo],
            "Total Revenue": [rw, rwo],
            "Revenue Per Account": [rpw, rpwo],
        })

        notes = (
            f"${delta:.2f} more revenue per account with Reg E. "
            f"Potential at {l12m_rege:.0%} TTM Reg E: ${pot_l12m:,.0f}"
        )

        ctx.results["value_2"] = {
            "delta": delta, "accts_with": aw, "accts_without": awo,
            "rev_per_with": rpw, "rev_per_without": rpwo,
            "hist_rege": hist_rege, "l12m_rege": l12m_rege,
            "pot_hist": pot_hist, "pot_l12m": pot_l12m, "pot_100": pot_100,
        }

        return [AnalysisResult(
            slide_id="A11.2", title="Value of Reg E Opt-In",
            chart_path=chart_path,
            excel_data={"Comparison": comp_df},
            notes=notes,
        )]
