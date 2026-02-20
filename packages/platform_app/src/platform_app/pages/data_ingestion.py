"""UAP Data Ingestion -- upload, validate, and profile data files."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">DATA / INGESTION</p>', unsafe_allow_html=True)
st.title("Data Ingestion")
st.caption("Upload or point to data files. Validate schema before analysis.")

# ---------------------------------------------------------------------------
# File upload section
# ---------------------------------------------------------------------------
st.markdown('<p class="uap-label">UPLOAD FILES</p>', unsafe_allow_html=True)

tab_oddd, tab_tran, tab_ics = st.tabs(["ODDD (ARS)", "Transaction (TXN)", "ICS Data"])

with tab_oddd:
    oddd_mode = st.radio("Input", ["Upload", "Server path"], key="oddd_mode", horizontal=True)
    if oddd_mode == "Upload":
        oddd_upload = st.file_uploader("ODDD Excel file", type=["xlsx", "xls"], key="oddd_upload")
        if oddd_upload:
            tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False, prefix="oddd_")
            tmp.write(oddd_upload.getvalue())
            tmp.flush()
            st.session_state["uap_file_oddd"] = tmp.name
            st.success(f"Uploaded: {oddd_upload.name}")
    else:
        oddd_path = st.text_input(
            "ODDD file path",
            value=st.session_state.get("uap_file_oddd", ""),
            key="oddd_path_input",
            placeholder="/path/to/9999-ODD.xlsx",
        )
        if oddd_path.strip():
            if Path(oddd_path.strip()).exists():
                st.session_state["uap_file_oddd"] = oddd_path.strip()
                st.success(f"Found: `{Path(oddd_path.strip()).name}`")
            else:
                st.error(f"Not found: `{oddd_path.strip()}`")

with tab_tran:
    tran_mode = st.radio(
        "Input", ["Upload", "Server path", "Directory scan"], key="tran_mode", horizontal=True
    )
    if tran_mode == "Upload":
        tran_upload = st.file_uploader("Transaction CSV", type=["csv", "txt"], key="tran_upload")
        if tran_upload:
            tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, prefix="tran_")
            tmp.write(tran_upload.getvalue())
            tmp.flush()
            st.session_state["uap_file_tran"] = tmp.name
            st.success(f"Uploaded: {tran_upload.name}")
    elif tran_mode == "Server path":
        tran_path = st.text_input(
            "Transaction file path",
            value=st.session_state.get("uap_file_tran", ""),
            key="tran_path_input",
            placeholder="/path/to/transactions.csv",
        )
        if tran_path.strip():
            if Path(tran_path.strip()).exists():
                st.session_state["uap_file_tran"] = tran_path.strip()
                st.success(f"Found: `{Path(tran_path.strip()).name}`")
            else:
                st.error(f"Not found: `{tran_path.strip()}`")
    else:
        st.caption(
            "Scan a directory for transaction files across year folders "
            "(e.g. `2023/`, `2024/`, `2025/`). All matching files are merged into one."
        )
        tran_dir = st.text_input(
            "Transaction root directory",
            value=st.session_state.get("uap_tran_dir", ""),
            key="tran_dir_input",
            placeholder="/path/to/client/transactions/",
        )
        file_ext = st.selectbox("File type", ["csv", "txt"], key="tran_dir_ext")
        if tran_dir.strip() and Path(tran_dir.strip()).is_dir():
            d = Path(tran_dir.strip())
            files = sorted(d.rglob(f"*.{file_ext}"))
            if files:
                # Group by parent folder for display
                by_folder: dict[str, list[Path]] = {}
                for f in files:
                    rel = f.parent.relative_to(d) if f.parent != d else Path(".")
                    by_folder.setdefault(str(rel), []).append(f)

                total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
                fc1, fc2, fc3 = st.columns(3)
                fc1.metric("Files Found", len(files))
                fc2.metric("Folders", len(by_folder))
                fc3.metric("Total Size", f"{total_size_mb:.1f} MB")

                # Show folder breakdown
                with st.expander(f"File breakdown ({len(by_folder)} folders)", expanded=False):
                    for folder, folder_files in sorted(by_folder.items()):
                        folder_label = folder if folder != "." else "(root)"
                        st.markdown(
                            f'<div style="padding:0.15rem 0;">'
                            f'<span style="font-family:var(--uap-mono);font-size:0.75rem;'
                            f'font-weight:600;color:#475569;">{folder_label}/</span>'
                            f'<span style="font-family:var(--uap-mono);font-size:0.72rem;'
                            f'color:#94A3B8;margin-left:8px;">'
                            f"{len(folder_files)} file{'s' if len(folder_files) != 1 else ''}"
                            f"</span></div>",
                            unsafe_allow_html=True,
                        )
                        for ff in folder_files:
                            sz = ff.stat().st_size / (1024 * 1024)
                            st.markdown(
                                f'<div style="padding-left:1.5rem;font-family:var(--uap-mono);'
                                f'font-size:0.7rem;color:#64748B;">'
                                f"{ff.name}"
                                f'<span style="color:#94A3B8;margin-left:8px;">{sz:.1f} MB</span>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                if st.button(
                    f"Merge all {len(files)} files", key="tran_merge", use_container_width=True
                ):
                    merge_progress = st.progress(0, text="Merging...")
                    frames = []
                    for idx, f in enumerate(files):
                        merge_progress.progress(idx / len(files), text=f"Reading {f.name}...")
                        try:
                            df = pd.read_csv(f) if file_ext == "csv" else pd.read_csv(f, sep="\t")
                            frames.append(df)
                        except Exception as e:
                            st.warning(f"Skipped `{f.name}`: {e}")
                    merge_progress.progress(1.0, text="Writing merged file...")
                    if frames:
                        merged = pd.concat(frames, ignore_index=True)
                        tmp = tempfile.NamedTemporaryFile(
                            suffix=".csv", delete=False, prefix="tran_merged_"
                        )
                        merged.to_csv(tmp.name, index=False)
                        st.session_state["uap_file_tran"] = tmp.name
                        st.session_state["uap_tran_dir"] = tran_dir.strip()
                        merge_progress.empty()
                        st.success(
                            f"Merged **{len(merged):,}** rows from **{len(frames)}** files "
                            f"across **{len(by_folder)}** folders"
                        )
            else:
                st.warning(f"No `.{file_ext}` files found in `{d.name}` or subdirectories")

    # ODD file (optional -- enables M11-M14: demographics, campaigns, payroll, lifecycle)
    st.divider()
    st.caption(
        "Optional: ODD file enables Demographics, Campaigns, Payroll, "
        "and Lifecycle analyses (M11-M14)."
    )
    odd_mode = st.radio("ODD Input", ["Upload", "Server path"], key="txn_odd_mode", horizontal=True)
    if odd_mode == "Upload":
        odd_upload = st.file_uploader("ODD Excel file", type=["xlsx", "xls"], key="txn_odd_upload")
        if odd_upload:
            tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False, prefix="txn_odd_")
            tmp.write(odd_upload.getvalue())
            tmp.flush()
            st.session_state["uap_file_odd"] = tmp.name
            st.success(f"Uploaded: {odd_upload.name}")
    else:
        odd_path = st.text_input(
            "ODD file path",
            value=st.session_state.get("uap_file_odd", ""),
            key="txn_odd_path_input",
            placeholder="/path/to/ODD.xlsx (optional)",
        )
        if odd_path.strip():
            if Path(odd_path.strip()).exists():
                st.session_state["uap_file_odd"] = odd_path.strip()
                st.success(f"Found: `{Path(odd_path.strip()).name}`")
            else:
                st.error(f"Not found: `{odd_path.strip()}`")

with tab_ics:
    ics_mode = st.radio("Input", ["Upload", "Server path"], key="ics_mode", horizontal=True)
    if ics_mode == "Upload":
        ics_upload = st.file_uploader(
            "ICS data file", type=["xlsx", "xls", "csv"], key="ics_upload"
        )
        if ics_upload:
            suffix = f".{ics_upload.name.rsplit('.', 1)[-1]}" if "." in ics_upload.name else ".xlsx"
            tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix="ics_")
            tmp.write(ics_upload.getvalue())
            tmp.flush()
            st.session_state["uap_file_ics"] = tmp.name
            st.success(f"Uploaded: {ics_upload.name}")
    else:
        ics_path = st.text_input(
            "ICS file path",
            value=st.session_state.get("uap_file_ics", ""),
            key="ics_path_input",
            placeholder="/path/to/ics_data.xlsx",
        )
        if ics_path.strip():
            if Path(ics_path.strip()).exists():
                st.session_state["uap_file_ics"] = ics_path.strip()
                st.success(f"Found: `{Path(ics_path.strip()).name}`")
            else:
                st.error(f"Not found: `{ics_path.strip()}`")

# ---------------------------------------------------------------------------
# Data profile
# ---------------------------------------------------------------------------
st.divider()
st.markdown('<p class="uap-label">DATA PROFILE</p>', unsafe_allow_html=True)


def _profile_file(path_str: str, label: str) -> None:
    """Show basic profile of a data file."""
    if not path_str:
        return
    p = Path(path_str)
    if not p.exists():
        return

    try:
        if p.suffix in (".xlsx", ".xls"):
            df = pd.read_excel(p, nrows=500)
        else:
            df = pd.read_csv(p, nrows=500)
    except Exception as e:
        st.warning(f"Could not profile {label}: {e}")
        return

    with st.expander(f"{label} -- {p.name}", expanded=False):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows", f"{len(df):,}")
        m2.metric("Columns", len(df.columns))

        # Null rate
        null_pct = df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100
        m3.metric("Null %", f"{null_pct:.1f}%")

        # Size
        size_mb = p.stat().st_size / (1024 * 1024)
        m4.metric("Size", f"{size_mb:.1f} MB")

        # Column list
        st.markdown('<p class="uap-label">COLUMNS</p>', unsafe_allow_html=True)
        col_info = pd.DataFrame(
            {
                "Column": df.columns,
                "Type": [str(dt) for dt in df.dtypes],
                "Non-Null": [f"{df[c].notna().sum()}" for c in df.columns],
                "Null %": [f"{df[c].isnull().mean() * 100:.1f}%" for c in df.columns],
            }
        )
        st.dataframe(col_info, use_container_width=True, hide_index=True)

        # Preview
        st.markdown('<p class="uap-label">PREVIEW (FIRST 10 ROWS)</p>', unsafe_allow_html=True)
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)


_profile_file(st.session_state.get("uap_file_oddd", ""), "ODDD")
_profile_file(st.session_state.get("uap_file_tran", ""), "Transaction")
_profile_file(st.session_state.get("uap_file_odd", ""), "ODD (TXN)")
_profile_file(st.session_state.get("uap_file_ics", ""), "ICS")

if not any(st.session_state.get(f"uap_file_{k}") for k in ["oddd", "tran", "odd", "ics"]):
    st.info("Upload or select data files above to see profiling results.")
