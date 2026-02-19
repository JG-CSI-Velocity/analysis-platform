"""DCTR helper functions shared across all analysis sub-modules."""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt


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
    }
    return plt.subplots(figsize=sizes.get(size, (14, 7)))


def _save_chart(fig, path):
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _slide(ctx, slide_id, data, category="DCTR"):
    ctx["all_slides"].append({"id": slide_id, "category": category, "data": data, "include": True})


def _dctr(df, debit_col="Debit?", yes="Yes"):
    t = len(df)
    w = len(df[df[debit_col] == yes])
    return t, w, (w / t if t > 0 else 0)


def _save(ctx, df, sheet, title, metrics=None):
    fn = ctx.get("_save_to_excel")
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            _report(ctx, f"   ⚠️ Export {sheet}: {e}")


def _total_row(df, label_col, label="TOTAL"):
    """Add a total row to a DCTR breakdown DataFrame."""
    if df.empty:
        return df
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    totals = {label_col: label}
    for c in num_cols:
        if "DCTR" in c or "%" in c:
            # Recalculate rate from With Debit / Total
            wd = df["With Debit"].sum() if "With Debit" in df.columns else 0
            ta = df["Total Accounts"].sum() if "Total Accounts" in df.columns else 0
            totals[c] = wd / ta if ta > 0 else 0
        else:
            totals[c] = df[c].sum()
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)
