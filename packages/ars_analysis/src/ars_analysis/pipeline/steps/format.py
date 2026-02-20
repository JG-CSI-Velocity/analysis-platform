"""Format ODD files: apply the 6-step ARS formatting pipeline.

Steps:
  2. Delete PYTD and YTD columns
  3. Calculate totals, monthly averages, swipe categories
  4. Sum PIN+Sig into combined Spend/Swipes columns
  5. Age calculations
  6. Mail & Response grouping
  7. Control segmentation
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from rich.console import Console

from ars_analysis.config import ARSSettings
from ars_analysis.pipeline.utils import resolve_target_month

logger = logging.getLogger(__name__)
console = Console()

# Swipe category thresholds
SWIPE_THRESHOLDS = [
    (1, "Non-user"),
    (6, "1-5 Swipes"),
    (11, "6-10 Swipes"),
    (16, "11-15 Swipes"),
    (21, "16-20 Swipes"),
    (26, "21-25 Swipes"),
    (41, "26-40 Swipes"),
]
SWIPE_TOP = "41+ Swipes"


def _swipe_category(monthly_swipes: float) -> str:
    """Categorize monthly swipe count into a labeled bucket."""
    for threshold, label in SWIPE_THRESHOLDS:
        if monthly_swipes < threshold:
            return label
    return SWIPE_TOP


@dataclass
class FormatResult:
    """Structured result from a format operation."""

    formatted: list[tuple[str, str, str]] = field(default_factory=list)
    errors: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.formatted) + len(self.errors)


def format_odd(df: pd.DataFrame) -> pd.DataFrame:
    """Apply 6-step formatting to an ODD DataFrame. Returns a new DataFrame."""
    df = df.copy()

    # Step 2: Delete PYTD and YTD columns
    drop_cols = [c for c in df.columns if "PYTD" in c or "YTD" in c]
    df.drop(columns=drop_cols, errors="ignore", inplace=True)
    logger.debug("Step 2: dropped %d PYTD/YTD columns", len(drop_cols))

    # Step 3: Totals, averages, categories
    pin_spend = [c for c in df.columns if "PIN $" in c]
    sig_spend = [c for c in df.columns if "Sig $" in c]
    pin_swipe = [c for c in df.columns if "PIN #" in c]
    sig_swipe = [c for c in df.columns if "Sig #" in c]
    mtd_cols = [c for c in df.columns if "MTD" in c]

    new_data: dict[str, pd.Series] = {}
    if pin_spend or sig_spend:
        new_data["Total Spend"] = df[sig_spend + pin_spend].sum(axis=1)
    if pin_swipe or sig_swipe:
        new_data["Total Swipes"] = df[sig_swipe + pin_swipe].sum(axis=1)
    if pin_spend or sig_spend:
        new_data["last 3-mon spend"] = df[pin_spend[-3:] + sig_spend[-3:]].sum(axis=1)
        new_data["last 12-mon spend"] = df[pin_spend[-12:] + sig_spend[-12:]].sum(axis=1)
    if pin_swipe or sig_swipe:
        new_data["last 3-mon swipes"] = df[pin_swipe[-3:] + sig_swipe[-3:]].sum(axis=1)
        new_data["last 12-mon swipes"] = df[pin_swipe[-12:] + sig_swipe[-12:]].sum(axis=1)
    if mtd_cols:
        new_data["Total Items"] = df[mtd_cols].sum(axis=1)
        new_data["Last 12-mon Items"] = df[mtd_cols[-12:]].sum(axis=1)
        new_data["Last 3-mon Items"] = df[mtd_cols[-3:]].sum(axis=1)

    if new_data:
        df = pd.concat([df, pd.DataFrame(new_data)], axis=1)

    # Monthly averages
    if "last 12-mon swipes" in df.columns:
        df["MonthlySwipes12"] = df["last 12-mon swipes"] / 12
        df["MonthlySwipes3"] = df["last 3-mon swipes"] / 3
    if "last 12-mon spend" in df.columns:
        df["MonthlySpend12"] = df["last 12-mon spend"] / 12
        df["MonthlySpend3"] = df["last 3-mon spend"] / 3
    if "Last 12-mon Items" in df.columns:
        df["MonthlyItems12"] = df["Last 12-mon Items"] / 12
        df["MonthlyItems3"] = df["Last 3-mon Items"] / 3

    # Swipe categories
    if "MonthlySwipes12" in df.columns:
        df["SwipeCat12"] = df["MonthlySwipes12"].apply(_swipe_category)
        df["SwipeCat3"] = df["MonthlySwipes3"].apply(_swipe_category)

    # Reorder: base columns, then detail, then calculated
    calc_col_names = list(new_data.keys()) + [
        c
        for c in [
            "MonthlySwipes12",
            "MonthlySwipes3",
            "MonthlySpend12",
            "MonthlySpend3",
            "MonthlyItems12",
            "MonthlyItems3",
            "SwipeCat12",
            "SwipeCat3",
        ]
        if c in df.columns
    ]
    detail_cols = pin_spend + sig_spend + pin_swipe + sig_swipe + mtd_cols
    other = [c for c in df.columns if c not in detail_cols + calc_col_names]
    df = df[other + detail_cols + calc_col_names]
    logger.debug("Step 3: totals + averages + categories done")

    # Step 4: Combined Spend/Swipes per month
    added = 0
    for col in pin_spend:
        my = col[:5]
        sig_col = my + " Sig $"
        if sig_col in df.columns:
            df[my + " Spend"] = df[col] + df[sig_col]
            added += 1
    for col in pin_swipe:
        my = col[:5]
        sig_col = my + " Sig #"
        if sig_col in df.columns:
            df[my + " Swipes"] = df[col] + df[sig_col]
            added += 1
    logger.debug("Step 4: added %d combined Spend/Swipes columns", added)

    # Step 5: Age calculations
    now = datetime.now()
    if "DOB" in df.columns:
        df["DOB"] = pd.to_datetime(df["DOB"], errors="coerce")
        df["Account Holder Age"] = now.year - df["DOB"].dt.year
    if "Date Opened" in df.columns:
        df["Date Opened"] = pd.to_datetime(df["Date Opened"], errors="coerce")
        if "Date Closed" in df.columns:
            date_closed = pd.to_datetime(df["Date Closed"], errors="coerce")
        else:
            date_closed = pd.Series(pd.NaT, index=df.index)
        df["Account Age"] = (date_closed.fillna(now) - df["Date Opened"]).dt.days / 365
    logger.debug("Step 5: age calculations done")

    # Step 6: Mail & Response grouping
    if "# of Offers" not in df.columns:
        mail_cols = df.filter(like=" Mail")
        if not mail_cols.empty:
            df["# of Offers"] = mail_cols.notnull().sum(axis=1)
    if "# of Responses" not in df.columns:
        resp_cols = df.filter(like=" Resp")
        if not resp_cols.empty:
            df["# of Responses"] = resp_cols.replace("NU 1-4", pd.NA).count(axis=1)

    if "# of Offers" in df.columns and "# of Responses" in df.columns:
        rg = pd.Series("check", index=df.index)
        rg[df["# of Responses"] >= 2] = "MR"
        rg[(df["# of Responses"] == 1) & (df["# of Offers"] >= 2)] = "MO-SR"
        rg[(df["# of Offers"] == 1) & (df["# of Responses"] == 1)] = "SO-SR"
        rg[(df["# of Offers"] > 0) & (df["# of Responses"] == 0)] = "Non-Responder"
        rg[df["# of Offers"] == 0] = "No Offer"
        df["Response Grouping"] = rg
    logger.debug("Step 6: response grouping done")

    # Step 7: Control segmentation
    seg_updates: dict[str, pd.Series] = {}
    resp_col_names = [
        c for c in df.columns if "Resp" in c and c not in ("# of Responses", "Response Grouping")
    ]
    for col in resp_col_names:
        mail_col = col.replace("Resp", "Mail")
        seg_col = col.replace("Resp", "Segmentation")
        if mail_col in df.columns:
            seg_updates[seg_col] = df.apply(
                lambda x, m=mail_col, r=col: (
                    "Control"
                    if pd.isna(x[m])
                    else "Non-Responder"
                    if pd.notna(x[m]) and (pd.isna(x[r]) or x[r] == "NU 1-4")
                    else "Responder"
                ),
                axis=1,
            )
    if seg_updates:
        df = pd.concat([df, pd.DataFrame(seg_updates)], axis=1)
    logger.debug("Step 7: control segmentation done (%d columns)", len(seg_updates))

    return df


def _read_odd(file_path: Path) -> pd.DataFrame | None:
    """Read an ODD file (csv or xlsx) into a DataFrame."""
    suffix = file_path.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(file_path, skiprows=4, low_memory=False)
            if df.empty:
                return None
            if df.columns[0].startswith("Unnamed") or df.iloc[:, 0].dtype == "int64":
                df = df.drop(columns=[df.columns[0]])
            return df
        if suffix == ".xlsx":
            df = pd.read_excel(file_path)
            return df if not df.empty else None
    except Exception:
        logger.exception("Error reading %s", file_path.name)
        return None
    return None


def format_all(
    settings: ARSSettings,
    target_month: str | None = None,
    max_per_csm: int = 0,
) -> FormatResult:
    """Read raw ODD files from retrieve_dir, format, write to watch_root.

    Raw files: Incoming/ODDD Files/CSM/YYYY.MM/ClientID/
    Formatted: Ready for Analysis/CSM/YYYY.MM/ClientID/

    Parameters
    ----------
    settings : ARSSettings
        Pipeline settings with paths.retrieve_dir and paths.watch_root.
    target_month : str or None
        'YYYY.MM' format. Defaults to current month.
    max_per_csm : int
        Max files to format per CSM. 0 = no limit.
    """
    full_month, _, _ = resolve_target_month(target_month)
    root = settings.paths.retrieve_dir
    out_root = settings.paths.watch_root
    result = FormatResult()

    if not root.exists():
        logger.warning("Retrieve dir not found: %s", root)
        return result

    logger.info(
        "Formatting ODD files for %s (source: %s -> dest: %s, limit: %s)",
        full_month,
        root,
        out_root,
        max_per_csm or "all",
    )

    csm_dirs = sorted(d for d in root.iterdir() if d.is_dir())
    total_csm = len(csm_dirs)

    for i, csm_dir in enumerate(csm_dirs, 1):
        csm_name = csm_dir.name
        month_dir = csm_dir / full_month
        if not month_dir.exists():
            console.print(
                f"  [{i}/{total_csm}] [cyan]{csm_name}[/cyan] [dim]-- no {full_month} folder[/dim]",
            )
            continue

        client_dirs = sorted(d for d in month_dir.iterdir() if d.is_dir())
        console.print(
            f"  [{i}/{total_csm}] [cyan]{csm_name}[/cyan] -- {len(client_dirs)} client(s)",
        )

        count = 0
        for client_dir in client_dirs:
            if max_per_csm and count >= max_per_csm:
                break

            # Find ODD file (skip formatted, skip lock files)
            odd_files = [
                f
                for f in client_dir.iterdir()
                if f.is_file()
                and f.suffix.lower() in (".csv", ".xlsx")
                and not f.name.startswith("~$")
                and "formatted" not in f.name.lower()
            ]
            if not odd_files:
                continue

            odd_file = odd_files[0]
            logger.info("%s/%s: %s", csm_name, client_dir.name, odd_file.name)

            # Copy to local temp, format locally, copy result back
            tmp_dir = None
            try:
                tmp_dir = Path(tempfile.mkdtemp(prefix="ars_fmt_"))
                local_src = tmp_dir / odd_file.name
                shutil.copy2(odd_file, local_src)

                df = _read_odd(local_src)
                if df is None:
                    result.errors.append((csm_name, odd_file.name, "empty or unreadable"))
                    console.print(
                        f"      [red]x[/red] {client_dir.name} -- empty or unreadable",
                    )
                    continue

                df = format_odd(df)
                out_name = odd_file.stem + "-formatted.xlsx"
                local_out = tmp_dir / out_name
                df.to_excel(local_out, index=False, engine="xlsxwriter")

                # Copy result to network destination
                dest_dir = out_root / csm_name / full_month / client_dir.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_out, dest_dir / out_name)

                result.formatted.append((csm_name, client_dir.name, out_name))
                count += 1
                console.print(
                    f"      [green]+[/green] {client_dir.name} "
                    f"({df.shape[0]} rows, {df.shape[1]} cols)",
                )
                logger.info("Saved %s (%d rows x %d cols)", out_name, *df.shape)
            except Exception:
                logger.exception("Error formatting %s", odd_file.name)
                result.errors.append((csm_name, odd_file.name, "formatting failed"))
                console.print(
                    f"      [red]x[/red] {client_dir.name} -- formatting failed",
                )
            finally:
                if tmp_dir and tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)

    console.print()
    logger.info(
        "Format done: %d formatted, %d errors",
        len(result.formatted),
        len(result.errors),
    )
    return result
