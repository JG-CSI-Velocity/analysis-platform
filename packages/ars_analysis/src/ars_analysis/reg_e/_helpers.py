"""Reg E helper functions -- shared across all A8 analyses."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _report(ctx, msg):
    print(msg)
    cb = ctx.get("_progress_callback")
    if cb:
        cb(msg)


def _fig(ctx, size="single"):
    mf = ctx.get("_make_figure")
    if mf:
        return mf(size)
    sizes = {
        "single": (14, 7),
        "half": (10, 6),
        "wide": (16, 7),
        "square": (12, 12),
        "large": (28, 14),
        "tall": (14, 10),
    }
    return plt.subplots(figsize=sizes.get(size, (14, 7)))


def _save_chart(fig, path):
    for ax in fig.get_axes():
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _slide(ctx, slide_id, data, category="Reg E"):
    ctx["all_slides"].append({"id": slide_id, "category": category, "data": data, "include": True})


def _save(ctx, df, sheet, title, metrics=None):
    fn = ctx.get("_save_to_excel")
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   ⚠️ Export {sheet}: {e}")


def _rege(df, col, opt_list):
    """Calculate Reg E opt-in stats. Returns (total, opted_in, rate)."""
    t = len(df)
    if t == 0:
        return 0, 0, 0
    oi = len(df[df[col].isin(opt_list)])
    return t, oi, oi / t


def _opt_list(ctx):
    """Return normalised opt-in values list."""
    raw = ctx.get("reg_e_opt_in", [])
    if isinstance(raw, str):
        return [raw]
    return [str(v).strip() for v in raw] if raw else []


def _reg_col(ctx):
    """Return the latest Reg E column name."""
    return ctx.get("latest_reg_e_column")


def _total_row(df, label_col, label="TOTAL"):
    """Add a total row to a Reg E breakdown DataFrame."""
    if df.empty:
        return df
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    totals = {label_col: label}
    for c in num_cols:
        if "Rate" in c or "%" in c:
            oi = df["Opted In"].sum() if "Opted In" in df.columns else 0
            ta = df["Total Accounts"].sum() if "Total Accounts" in df.columns else 0
            totals[c] = oi / ta if ta > 0 else 0
        else:
            totals[c] = df[c].sum()
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
