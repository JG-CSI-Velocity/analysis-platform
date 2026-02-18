"""V4 Transaction Analysis - Main Runner.

Usage:
    python v4_run.py                    # uses v4_config.yaml in current dir
    python v4_run.py my_client.yaml     # uses specified config file

Loads data, runs selected storylines, generates Excel + HTML reports.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path

# Storyline modules
from txn_analysis.storylines import v4_s1_portfolio_health as s1
from txn_analysis.storylines import v4_s2_merchant_intel as s2
from txn_analysis.storylines import v4_s3_competition as s3
from txn_analysis.storylines import v4_s3_segmentation as s3c
from txn_analysis.storylines import v4_s3_threat_analysis as s3b
from txn_analysis.storylines import v4_s4_finserv as s4
from txn_analysis.storylines import v4_s5_demographics as s5
from txn_analysis.storylines import v4_s6_risk as s6
from txn_analysis.storylines import v4_s7_campaigns as s7
from txn_analysis.storylines import v4_s8_payroll as s8
from txn_analysis.storylines import v4_s9_lifecycle as s9
from txn_analysis.v4_data_loader import load_all, load_config
from txn_analysis.v4_excel_report import generate_excel_report
from txn_analysis.v4_html_report import generate_html_report

ALL_STORYLINES = [
    ("s1_portfolio", s1),
    ("s2_merchant", s2),
    ("s3_competition", s3),
    ("s3b_threats", s3b),
    ("s3c_segmentation", s3c),
    ("s4_finserv", s4),
    ("s5_demographics", s5),
    ("s6_risk", s6),
    ("s7_campaigns", s7),
    ("s8_payroll", s8),
    ("s9_lifecycle", s9),
]

# Public mapping for the Streamlit app to look up labels
STORYLINE_LABELS: dict[str, str] = {
    "s1_portfolio": "S1: Portfolio Health",
    "s2_merchant": "S2: Merchant Intelligence",
    "s3_competition": "S3: Competitive Landscape",
    "s3b_threats": "S3B: Threat Intelligence",
    "s3c_segmentation": "S3C: Account Segmentation",
    "s4_finserv": "S4: Financial Services",
    "s5_demographics": "S5: Demographics & Branches",
    "s6_risk": "S6: Risk & Balance",
    "s7_campaigns": "S7: Campaign Effectiveness",
    "s8_payroll": "S8: Payroll & Circular Economy",
    "s9_lifecycle": "S9: Lifecycle Management",
}


def run_pipeline(
    config: dict,
    storylines: list[str] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> tuple[dict, Path, Path]:
    """Execute the V4 analysis pipeline.

    Parameters
    ----------
    config : dict
        Pre-built config dict (e.g. from load_config + overrides).
    storylines : list[str] | None
        Which storyline keys to run (e.g. ["s1_portfolio", "s3_competition"]).
        None means run all 8.
    progress_cb : callable | None
        Optional callback ``(step, total, label)`` called after each storyline
        finishes, so a GUI can update a progress bar.

    Returns
    -------
    (results, excel_path, html_path)
    """
    start = time.time()

    output_dir = Path(config.get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    client_name = config.get("client_name", "Client")
    client_id = config.get("client_id", "")

    # Determine which storylines to run
    if storylines is None:
        active = ALL_STORYLINES
    else:
        key_set = set(storylines)
        active = [(k, m) for k, m in ALL_STORYLINES if k in key_set]

    # Load data
    if progress_cb:
        progress_cb(0, len(active) + 2, "Loading data...")
    ctx = load_all(config)

    # Run storylines
    results: dict = {}
    for i, (key, module) in enumerate(active, start=1):
        label = module.__name__
        if progress_cb:
            progress_cb(i, len(active) + 2, f"Running {STORYLINE_LABELS.get(key, label)}...")
        try:
            result = module.run(ctx)
            results[key] = result
        except Exception as e:
            results[key] = {
                "title": STORYLINE_LABELS.get(key, label),
                "description": f"Error: {e}",
                "sections": [],
                "sheets": [],
            }

    # Generate reports
    if progress_cb:
        progress_cb(len(active) + 1, len(active) + 2, "Generating reports...")

    excel_path = output_dir / f"{client_id}_{client_name.replace(' ', '_')}_V4_Analysis.xlsx"
    html_path = output_dir / f"{client_id}_{client_name.replace(' ', '_')}_V4_Dashboard.html"

    generate_excel_report(results, config, str(excel_path))
    generate_html_report(results, config, str(html_path))

    if progress_cb:
        progress_cb(len(active) + 2, len(active) + 2, "Complete")

    elapsed = time.time() - start
    total_sections = sum(len(r.get("sections", [])) for r in results.values())
    total_sheets = sum(len(r.get("sheets", [])) for r in results.values())
    total_figures = sum(
        len(s.get("figures", [])) for r in results.values() for s in r.get("sections", [])
    )
    print(f"\n  V4 Analysis complete in {elapsed:.1f}s")
    print(
        f"  {len(results)} storylines | {total_sections} sections | "
        f"{total_figures} charts | {total_sheets} sheets"
    )
    print(f"  Excel: {excel_path}")
    print(f"  HTML:  {html_path}")

    return results, excel_path, html_path


def run_all(config_path: str = "v4_config.yaml") -> None:
    """CLI entry point -- loads config from file and runs all storylines."""
    config = load_config(config_path)
    client_name = config.get("client_name", "Client")
    client_id = config.get("client_id", "")

    print(f"\n{'=' * 80}")
    print("  V4 TRANSACTION ANALYSIS")
    print(f"  Client: {client_id} - {client_name}")
    print(f"{'=' * 80}\n")

    run_pipeline(config)


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "v4_config.yaml"
    run_all(config_file)
