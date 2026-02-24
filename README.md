# RPE Analysis Platform

Analysis platform by CSI | Velocity. Combines three pipelines into one tool: **ARS** (account reviews), **Transaction** (debit card analytics), and **ICS** (Instant Card Services).

Used by CSMs to generate consultant-grade PowerPoint decks, detailed Excel reports, and charts for 300+ credit union clients.

---

## Table of Contents

- [Getting Started](#getting-started)
- [How It Works: The ARS Pipeline](#how-it-works-the-ars-pipeline)
- [PowerPoint Deck Structure](#powerpoint-deck-structure)
- [How to Use](#how-to-use)
- [The Three Pipelines](#the-three-pipelines)
- [File Formatting](#file-formatting)
- [Folder Structure (M: Drive)](#folder-structure-m-drive)
- [Codebase Structure](#codebase-structure)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Requirements

- **Python 3.11+**
- **uv** package manager ([install guide](https://docs.astral.sh/uv/))
- **Windows** recommended for production (M: drive access). macOS/Linux for development.

### Installation

```
git clone https://github.com/JG-CSI-Velocity/analysis-platform.git
cd analysis-platform
pip install uv
uv python install 3.11
uv sync --all-packages
```

Verify:

```
uv run pytest tests/ -q
```

You should see 2,600+ tests pass in about 2.5 minutes.

---

## How It Works: The ARS Pipeline

The ARS pipeline transforms a raw ODD (Overdraft/Debit Data Dump) Excel file into a complete PowerPoint presentation with 70+ slides, a detailed Excel workbook, and individual chart images.

### Step-by-Step Process

```
ODD Excel File (from M:\ARS\Incoming\ODDD Files\)
    |
    v
[1] LOAD DATA
    - Read Excel file into pandas DataFrame
    - Pre-parse Date Opened and Date Closed columns (once, not 14+ times)
    - Normalize column names (e.g. "Prod Code" -> "Product Code")
    - Validate required columns exist (Stat Code, Product Code, Date Opened, Avg Bal)
    |
    v
[2] CREATE SUBSETS
    - Auto-compute date range from data: end_date = max(Date Opened), start_date = end_date - 12 months
    - Filter open accounts: Stat Code starts with "O" (case-insensitive, whitespace-stripped)
    - Filter eligible accounts: match Stat Code + Product Code against client config values
    - Split eligible into personal vs business (Business? column)
    - Identify debit card holders: auto-detect column (Debit?, DC Indicator, etc.)
    - Create Last 12 Months subset using computed date range
    |
    v
[3] RUN ANALYSES (20 modules in fixed order)
    - Overview (3): stat code distribution, product code distribution, eligibility breakdown
    - DCTR (5): penetration rates, trends, branch heatmaps, eligibility funnels, demographic overlays
    - Reg E (3): opt-in status, branch breakdown, age/product/tenure dimensions
    - Attrition (3): closure rates, closure dimensions, revenue impact
    - Value (1): debit card value (A11.1) and Reg E opt-in value (A11.2)
    - Mailer (3): campaign insights, per-month response rates, market impact
    - Insights (2): synthesis of findings (S1-S5), conclusions and recommendations (S6-S8)

    Each module:
    1. Validates its required columns exist
    2. Runs analysis on the data subsets
    3. Generates matplotlib charts (saved as PNG to charts/ directory)
    4. Returns AnalysisResult objects with chart path, Excel data, slide metadata, and notes
    |
    v
[4] GENERATE OUTPUT
    - Run Report: JSON diagnostic file listing every slide's status (success/fail, has chart, has Excel data)
    - Excel Workbook: One tab per analysis, formatted headers/borders/auto-width, Summary sheet with KPIs
    - PowerPoint Deck: Full presentation built from Template12.25.pptx (see deck structure below)
```

### Where the Data Comes From

| Data | Source | Path |
|------|--------|------|
| ODD Excel files | CSMs upload to M: drive | `M:\ARS\Incoming\ODDD Files\{CSM}\{ClientID}\` |
| Transaction CSVs | CSMs upload to M: drive | `M:\ARS\Incoming\Transaction Files\` |
| Client config | Manually maintained JSON | `M:\ARS\Config\clients_config.json` |
| PPTX template | Shared template file | `M:\ARS\Presentations\Template12.25.pptx` |

### Client Configuration (clients_config.json)

Each credit union has an entry in `clients_config.json` keyed by client ID:

```json
{
  "1200": {
    "ClientName": "Guardians Credit Union",
    "EligibleStatusCodes": ["O"],
    "EligibleProductCodes": ["DDA", "CHK", "SAV"],
    "RegEColumn": "Reg E Status",
    "RegEOptInCode": ["Y", "Yes"],
    "DCIndicator": "Debit?",
    "NSF_OD_Fee": 29.00,
    "ICRate": 0.0045,
    "EligibleMailCode": ["A"],
    "BranchMapping": {}
  }
}
```

Key fields:
- **EligibleStatusCodes**: Which Stat Code values count as "eligible" (typically `["O"]` for Open)
- **EligibleProductCodes**: Which Product Codes to include (e.g. `["DDA"]`)
- **NSF_OD_Fee** and **ICRate**: Used in revenue calculations (Value module, Attrition impact)
- **RegEColumn** and **RegEOptInCode**: Column name and opt-in values for Reg E analysis
- **DCIndicator**: Column name for debit card indicator (auto-detected if not set)

### Data Accuracy Safeguards

| Issue | Safeguard | Where |
|-------|-----------|-------|
| Date range wrong | Auto-computed from max(Date Opened) minus 12 months | `subsets.py` |
| Stat Code whitespace | `.str.strip()` before matching | `subsets.py` |
| Stat Code case mismatch | `.str.upper()` on both config values and data | `subsets.py` |
| Debit column name varies | Auto-detect: tries Debit?, Debit, DC Indicator, DC_Indicator | `subsets.py` |
| Debit values vary (Yes/Y/D/DC) | Normalized to boolean via `.isin(("D", "DC", "DEBIT", "YES", "Y"))` | `subsets.py` |
| Product Code aliases | "Prod Code" auto-renamed to "Product Code" at load time | `load.py` |
| Balance column aliases | "Balance", "Current Balance", "Cur Bal" all renamed to "Avg Bal" | `load.py` |
| Date parsed repeatedly | Pre-parsed once at load; downstream modules use parsed values | `load.py` |
| Module fails on one client | Error isolation per module; one failure does not stop the batch | `runner.py` |
| Slide fails during PPTX build | Per-slide try/except; bad slide is skipped, rest of deck builds | `deck_builder.py` |

---

## PowerPoint Deck Structure

The ARS deck uses `Template12.25.pptx` which has 14 slide layouts. The deck builder assembles slides in this order:

### Preamble (13 slides)

| # | Slide | Content |
|---|-------|---------|
| P01 | Title | Client name + "Account Revenue Solution" + month |
| P02 | Agenda | Blank placeholder |
| P03 | Program Performance divider | Client name + month |
| P04 | Financial Performance | Blank (manual paste) |
| P05 | Monthly Revenue | Blank (manual paste) |
| P06 | ARS Lift Matrix | Blank (manual paste) |
| P07 | ARS Mailer Revisit divider | Client name + month |
| P08 | ARS Mailer Revisit - Swipes | Wired to most recent A12 Swipes chart |
| P09 | ARS Mailer Revisit - Spend | Wired to most recent A12 Spend chart |
| P10 | Data Check Overview | Blank |
| P11 | Mailer Summaries | Section divider |
| P12 | All Program Results | Blank |
| P13 | Response Rate Trend | Wired to A13.5 responder trend chart |

### Analysis Section Order

After preamble, analysis slides are reordered into these sections:

1. **Recent Mailer Clusters** (2 most recent months, each: A13 Summary + A12 Swipes + A12 Spend)
2. **Debit Card Take Rate** (DCTR merged pairs + A11.1 Value)
3. **Reg E Analysis** (Reg E merged pairs + A11.2 Value)
4. **Account Attrition** (Merged pair + A9.1 rate + A9.9-A9.12 impact)
5. **Summary & Key Takeaways** (blank divider)
6. **Appendix** (older mailer months, Overview A1-A5, DCTR/RegE/Attrition deep dives, aggregate mailer slides)

### Consolidation Merges

Paired slides are merged side-by-side for the main deck (individual versions go to appendix):

| Left | Right | Merged Title |
|------|-------|--------------|
| A7.6a (L12M DCTR Trend) | A7.4 (Segment Trends) | DCTR Trajectory: Recent Trend & Segments |
| A7.8 (L12M Funnel) | A7.7 (Historical Funnel) | DCTR Funnel: L12M vs Historical |
| A7.11 (Holder Age) | A7.12 (Account Age) | DCTR Opportunity: Age Analysis |
| A8.12 (Trend) | A8.3 (Monthly) | Reg E Trajectory: Trend & Monthly |
| A8.11 (L12M Funnel) | A8.10 (All-Time Funnel) | Reg E Funnel: L12M vs All-Time |
| A8.5 (Account Age) | A8.6 (Holder Age) | Reg E Opportunity: Age Analysis |
| A9.3 (Open vs Closed) | A9.6 (Personal vs Business) | Attrition Profile |

---

## How to Use

There are three ways to run analyses: **batch scripts** (recommended for production), the **web dashboard**, or the **command line**.

### Option 1: Full Pipeline (run.bat)

Double-click `run.bat` on the Windows machine. It does everything automatically:

1. Retrieves ODD files from CSM source paths on the M: drive
2. Formats them (adds calculated columns: Total Spend, SwipeCat, age buckets, etc.)
3. Runs batch analysis for the current month
4. Opens the web dashboard in your browser

```
run.bat              -- uses current month
run.bat 2026.02      -- specify a month
```

### Option 2: Headless Batch (run_batch.bat)

Same as above but without the dashboard. Good for overnight batch runs.

```
run_batch.bat              -- uses current month
run_batch.bat 2026.01      -- specify a month
```

### Option 3: Web Dashboard (dashboard.bat)

Opens the Streamlit dashboard directly. Use this when you already have formatted files and want to run analysis interactively.

```
dashboard.bat
```

The dashboard opens at `http://localhost:8501` and walks you through a 5-step workflow:

| Step | Page | What You Do |
|------|------|------------|
| 1 | **Workspace** | Pick your CSM folder and client. Files auto-detect. |
| 2 | **Data Ingestion** | Upload files or point to server paths. Format ODD files here if needed. |
| 3 | **Module Library** | Pick which analyses to run, or choose a preset template. |
| 4 | **Run Analysis** | Pre-flight check, then execute. Progress bar shows status. |
| 5 | **View Outputs** | Browse results, preview charts, download Excel/PowerPoint/ZIP. |

Additional pages:

- **Batch Run** -- run multiple clients sequentially
- **Run History** -- log of past runs with timestamps and status

### Option 4: Command Line

```
uv run python -m ars_analysis run "path/to/ODD.xlsx" --output-dir output/
uv run python -m txn_analysis "path/to/transactions.csv" -o output/
uv run python -m ics_toolkit analyze "path/to/ics_data.xlsx" -o output/
```

For help on any pipeline:

```
uv run python -m ars_analysis --help
uv run python -m txn_analysis --help
uv run python -m ics_toolkit --help
```

---

## The Three Pipelines

### ARS (Account Review Suite)

Analyzes ODDD (Overdraft/Debit Data Dump) Excel files. Produces a 70+ slide PowerPoint deck and detailed Excel workbook.

**Input**: Formatted ODDD Excel file (`.xlsx`)

**Output**: PowerPoint deck + Excel report + 70+ chart images + JSON run report

**20 analysis modules across 7 sections**:

| Section | Modules | Slide IDs | What It Analyzes |
|---------|---------|-----------|-----------------|
| Overview | stat_codes, product_codes, eligibility | A1, A1b, A3 | Portfolio composition and opening trends |
| DCTR | penetration, trends, branches, funnel, overlays | DCTR-1 to DCTR-16, A7.4-A7.15 | Debit card take rates, trends, funnels, branch heatmaps |
| Reg E | status, branches, dimensions | A8.1-A8.13 | Regulation E opt-in status and breakdowns |
| Attrition | rates, dimensions, impact | A9.1-A9.13 | Account closures, revenue impact, velocity |
| Value | analysis | A11.1, A11.2 | Revenue per account: debit card holders vs non-holders |
| Mailer | insights, response, impact | A12.x, A13.x, A14.x, A15.x | Campaign response rates, spend lift, market impact |
| Insights | synthesis, conclusions | S1-S8 | Cross-section findings and recommendations |

### Transaction (TXN)

Analyzes debit card transaction CSV files. 35 analyses covering spending patterns, merchant categories, interchange revenue, and competitive positioning.

**Input**: Transaction CSV file (columns: `merchant_name`, `amount`, `primary_account_num`, `transaction_date`, `mcc_code`). Optional ODD file for demographics.

**Output**: Excel report + Plotly charts

**Analyses**: M1-M17 (spending, merchants, MCC analysis, interchange, demographics, campaigns, lifecycle, onset tracking, spending behavior) + scorecard

### ICS (Instant Card Services)

Three sub-pipelines for ICS program analysis:

- **ICS Analysis**: 37 analyses on ICS program data (distribution, source breakdown, balance, activity)
- **ICS Append**: Matches and merges ICS account data onto ODD files (adds `ICS Account` and `ICS Source` columns)
- **ICS Referral Intelligence**: 8-step pipeline analyzing referral patterns, entity networks, and influence scoring

**Input**: ICS Excel/CSV files

**Output**: Excel report + matplotlib charts + PowerPoint deck

---

## File Formatting

ODD files must be **formatted** before ARS analysis and **ICS-appended** before ICS analysis. The platform detects this automatically:

| Badge | Meaning |
|-------|---------|
| FORMATTED | ODD has calculated columns (Total Spend, SwipeCat, etc.). Ready for ARS. |
| UNFORMATTED | Raw ODD file. Needs formatting before ARS analysis. |
| ICS READY | ODD has ICS Account + ICS Source columns. Ready for ICS analysis. |
| ICS FIELDS MISSING | ODD hasn't been through ICS append. Run append before ICS analysis. |

**To format**: Use the "Format Now" button on the Data Ingestion page, or run formatting through the batch scripts.

Transaction files do not need formatting.

---

## Folder Structure (M: Drive)

```
M:\ARS\
  Config\
    clients_config.json          Client-specific settings (300+ entries)
  Presentations\
    Template12.25.pptx           PowerPoint slide template (14 layouts)
    Presentation Excels\         Master Excel copies
  Incoming\
    ODDD Files\{CSM}\            Raw ODD files uploaded by CSMs
    Transaction Files\           Transaction CSVs
    CSM-Data\                    Additional CSM data
  Ready for Analysis\
    {CSM}\{ClientID}\            Formatted files ready for pipeline
  Analysis Outputs\              Final deliverables delivered to VP/CSMs
  Output\                        Pipeline working output (per-client subfolders)
  Logs\                          Pipeline log files
  _archive\                      Stale folders moved here by cleanup script
```

### Output Structure (Per Client Run)

```
M:\ARS\Output\{ClientID}\{YYYY.MM}\
  charts/                           Individual chart PNGs
  {ClientID}_{YYYY.MM}_deck.pptx    PowerPoint presentation
  {ClientID}_{YYYY.MM}_analysis.xlsx Excel workbook
  {ClientID}_{YYYY.MM}_run_report.json  Diagnostic report
```

---

## Codebase Structure

```
analysis-platform/
  packages/
    shared/              Foundation: unified types, context, config (87 tests)
    ars_analysis/        ARS pipeline: 20 modules, deck builder, Excel formatter (689 tests)
    txn_analysis/        Transaction pipeline: 35 analyses (711 tests)
    ics_toolkit/         ICS pipeline: 37 analyses + append + referral (1,013 tests)
    platform_app/        Orchestrator, Streamlit UI, CLI dispatcher (74 tests)
  tests/
    ars/                 ARS tests
    txn/                 Transaction tests
    ics/                 ICS tests (includes referral -- 212)
    shared/              Shared tests
    platform/            Platform tests
    integration/         End-to-end tests (31)
    e2e_data/            Synthetic data fixtures
  scripts/
    cleanup_and_organize.bat   Archive stale M: drive folders
  config/                      Default configuration files
  plans/                       Implementation plans
```

**Total: 2,605 tests across 5 packages.**

---

## Troubleshooting

**"uv not found"** -- Install uv: `pip install uv`

**"File is unformatted"** -- Click "Format Now" in Data Ingestion, or use `run.bat` which formats automatically.

**"ICS fields missing"** -- Run ICS append first to add ICS Account and ICS Source columns to the ODD file.

**Charts look blank on Windows** -- Known issue with kaleido on Windows. Charts still export correctly to PowerPoint; they just can't be previewed in tests.

**Network path errors on M: drive** -- The Excel writer creates temp files that can fail on network paths. Use the `use_local_temp` batch option to process locally and copy results back.

**Eligible accounts = 0** -- Check `clients_config.json` for the client. Ensure `EligibleStatusCodes` and `EligibleProductCodes` match the actual values in the ODD file.

**Reg E results empty** -- Verify `RegEColumn` in config matches the actual column name in the ODD file.

**PPTX build crashes** -- Check the run report JSON for which specific slide failed. Common cause: chart file was not generated (upstream module failed).

**Dashboard port stuck (localhost:8501 already in use)** -- Kill the old Streamlit process:

```cmd
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8501') do taskkill /F /PID %a
```

---

## Related Repositories

| Repo | Purpose | Status |
|------|---------|--------|
| [ars-pipeline](https://github.com/JG-CSI-Velocity/ars-pipeline) | Standalone ARS pipeline with 26 modules (10 sections), Typer CLI, batch processing | Active |
| [ars_analysis-jupyter](https://github.com/JG-CSI-Velocity/ars_analysis-jupyter) | Original Jupyter-based ARS pipeline | Deprecated -- superseded by ars-pipeline |

---

## License

Proprietary. Internal use only.
