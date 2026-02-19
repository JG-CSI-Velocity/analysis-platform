"""
mailer_common.py -- Shared constants and helpers for mailer modules
===================================================================
Eliminates 3x duplication across mailer_impact.py, mailer_insights.py,
and mailer_response.py.

Usage:
    from mailer_common import (
        RESPONSE_SEGMENTS, MAILED_SEGMENTS, TH_SEGMENTS,
        SPEND_PATTERN, SWIPE_PATTERN,
        report, save_chart, slide, parse_month, discover_pairs, save_to_excel,
        build_responder_mask, build_mailed_mask,
    )
"""

import re
import traceback

import matplotlib.pyplot as plt
import pandas as pd

# =============================================================================
# CONSTANTS
# =============================================================================

RESPONSE_SEGMENTS = ["NU 5+", "TH-10", "TH-15", "TH-20", "TH-25"]
MAILED_SEGMENTS = ["NU", "TH-10", "TH-15", "TH-20", "TH-25"]
TH_SEGMENTS = ["TH-10", "TH-15", "TH-20", "TH-25"]

SPEND_PATTERN = re.compile(r"^[A-Z][a-z]{2}\d{2} Spend$")
SWIPE_PATTERN = re.compile(r"^[A-Z][a-z]{2}\d{2} Swipes$")


# =============================================================================
# HELPERS
# =============================================================================


def report(ctx, msg):
    """Print a progress message and notify the Streamlit callback if set."""
    print(msg)
    cb = ctx.get("_progress_callback")
    if cb:
        cb(msg)


def save_chart(fig, path):
    """Save a matplotlib figure to disk and close it."""
    for ax in fig.get_axes():
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(False)
    fig.savefig(str(path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def slide(ctx, slide_id, data, category="Mailer"):
    """Append a slide entry to the pipeline's all_slides list."""
    ctx["all_slides"].append(
        {
            "id": slide_id,
            "category": category,
            "data": data,
            "include": True,
        }
    )


def save_to_excel(ctx, df, sheet, title, metrics=None):
    """Export a DataFrame to the pipeline Excel workbook."""
    fn = ctx.get("_save_to_excel")
    if fn:
        try:
            fn(ctx, df=df, sheet_name=sheet, analysis_title=title, key_metrics=metrics)
        except Exception as e:
            report(ctx, f"   Export {sheet}: {e}")


def parse_month(col_name):
    """Parse MmmYY from a column name like 'Aug25 Mail' -> datetime."""
    try:
        return pd.to_datetime(col_name.split(" ")[0], format="%b%y")
    except Exception:
        return pd.NaT


def discover_pairs(ctx):
    """
    Return sorted list of (month, resp_col, mail_col) tuples.
    Caches result in ctx['mailer_pairs'].
    """
    pairs = ctx.get("mailer_pairs")
    if pairs:
        return pairs

    data = ctx["data"]
    cols = list(data.columns)
    client_id = ctx.get("client_id", "")

    mail_cols = sorted(
        [c for c in cols if re.match(r"^[A-Z][a-z]{2}\d{2} Mail$", c)], key=parse_month
    )

    pairs = []
    for mc in mail_cols:
        month = mc.replace(" Mail", "")
        rc = f"{month} Resp"
        if rc in cols and data[rc].notna().any():
            pairs.append((month, rc, mc))

    if client_id == "1200" and pairs:
        cutoff = pd.to_datetime("Apr24", format="%b%y")
        pairs = [(m, r, ml) for m, r, ml in pairs if parse_month(m) >= cutoff]

    ctx["mailer_pairs"] = pairs
    return pairs


# =============================================================================
# RESPONDER / MAILED MASK BUILDERS
# =============================================================================


def build_responder_mask(data, pairs):
    """Build a boolean Series: True for any account that responded in any month."""
    mask = pd.Series(False, index=data.index)
    for _, resp_col, _ in pairs:
        mask |= data[resp_col].isin(RESPONSE_SEGMENTS)
    return mask


def build_mailed_mask(data, pairs):
    """Build a boolean Series: True for any account mailed in any month."""
    mask = pd.Series(False, index=data.index)
    for _, _, mail_col in pairs:
        mask |= data[mail_col].isin(MAILED_SEGMENTS)
    return mask


# =============================================================================
# SAFE WRAPPER
# =============================================================================


def safe(fn, ctx, label):
    """Run fn(ctx) with error isolation; log and continue on failure."""
    try:
        return fn(ctx)
    except Exception as e:
        report(ctx, f"   {label} failed: {e}")
        traceback.print_exc()
        return ctx
