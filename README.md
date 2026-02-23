# RPE Analysis Platform

Analysis platform by CSI | Velocity. Combines three pipelines into one tool: **ARS** (account reviews), **Transaction** (debit card analytics), and **ICS** (Instant Card Services).

Used by CSMs to generate consultant-grade PowerPoint decks, detailed Excel reports, and charts for 300+ credit union clients.

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

You should see 2,400+ tests pass in about 2.5 minutes.

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

These are the specific mechanisms that prevent incorrect analysis:

| Issue | Safeguard | Where |
|-------|-----------|-------|
| Date range wrong | Auto-computed from max(Date Opened) minus 12 months | `subsets.py:24-35` |
| Stat Code whitespace | `.str.strip()` before matching | `subsets.py:48` |
| Stat Code case mismatch | `.str.upper()` on both config values and data | `subsets.py:74-75` |
| Debit column name varies | Auto-detect: tries Debit?, Debit, DC Indicator, DC_Indicator | `subsets.py:110-116` |
| Debit values vary (Yes/Y/D/DC) | Normalized to boolean via `.isin(("D", "DC", "DEBIT", "YES", "Y"))` | `subsets.py:119-121` |
| Product Code aliases | "Prod Code" auto-renamed to "Product Code" at load time | `load.py:91-107` |
| Balance column aliases | "Balance", "Current Balance", "Cur Bal" all renamed to "Avg Bal" | `load.py:19` |
| Date parsed repeatedly | Pre-parsed once at load; downstream modules use parsed values | `load.py:46-48` |
| Module fails on one client | Error isolation per module; one failure does not stop the batch | `runner.py:131-138` |
| Slide fails during PPTX build | Per-slide try/except; bad slide is skipped, rest of deck builds | `deck_builder.py:131-138` |
| L12M never computed | `end_date` auto-set from data; L12M subset computed from that | `subsets.py:24-35` |
| Mailer age bucket drift | Mail date computed relative to mail month, not current date | `mailer/response.py` |

---

## PowerPoint Deck Structure

The ARS deck uses `Template12.25.pptx` which has 14 slide layouts. The deck builder assembles slides in this order:

### Preamble (13 slides)

| # | Slide | Layout | Content |
|---|-------|--------|---------|
| P01 | Title | Client name + "Account Revenue Solution" + month | Auto-generated |
| P02 | Agenda | Blank placeholder | Manual |
| P03 | Program Performance divider | Client name + month | Auto-generated |
| P04 | Financial Performance | Blank | Manual (paste table) |
| P05 | Monthly Revenue | Blank | Manual (paste table) |
| P06 | ARS Lift Matrix | Blank | Manual (paste table) |
| P07 | ARS Mailer Revisit divider | Client name + month | Auto-generated |
| P08 | Mailer Swipes | Wired to most recent A12 Swipes chart | Auto if mailer data exists |
| P09 | Mailer Spend | Wired to most recent A12 Spend chart | Auto if mailer data exists |
| P10 | Data Check Overview | Blank | Manual |
| P11 | Mailer Summaries divider | Client name + month | Auto-generated |
| P12 | All Program Results | Blank | Manual |
| P13 | Program Responses to Date | Wired to A13.5 count trend chart | Auto if mailer data exists |

### Analysis Sections (auto-generated)

Slides are grouped by section with divider slides between each:

**Mailer Section** (comes first after preamble)
- A13.{month} -- Monthly summary slides (3-column layout: donut chart, bar chart, "Inside the Numbers" bullets)
- A13.Agg -- Aggregate summary (same 3-column layout)
- A13.5 -- Response count trend over time
- A13.6 -- Response rate by age
- A14.2 -- Mailer market impact
- A12.{month}.Swipes -- Swipe comparison charts
- A12.{month}.Spend -- Spend comparison charts
- A15.1-A15.4 -- Mailer insights charts

**Debit Card Take Rate Section**
- DCTR-1 through DCTR-8 -- Core penetration rates and comparisons
- DCTR-9 -- Branch breakdown
- A7.6a + A7.4 -- Merged: trajectory trend and segments (side-by-side)
- A7.7 + A7.8 -- Merged: historical vs TTM funnel (side-by-side)
- A7.11 + A7.12 -- Merged: age analysis (side-by-side)
- A7.10a -- Branch heatmap
- A11.1 -- Value of debit card (revenue per account with vs without)

**Reg E Section**
- A8.3 -- Reg E status overview
- A8.4a -- Opt-in distribution
- A8.10 + A8.11 -- Merged: all-time vs TTM funnel
- A8.5 + A8.6 -- Merged: age analysis
- A8.13 -- Trend analysis
- A11.2 -- Value of Reg E opt-in

**Attrition Section**
- A9.1 -- Overall attrition rate (with KPI callouts)
- A9.3 + A9.6 -- Merged: open vs closed and personal vs business
- A9.9-A9.12 -- Revenue impact slides (with KPI callouts)

**Summary and Key Takeaways** (blank divider for manual content)

**Appendix**
- Overview slides (A1, A1b, A3)
- DCTR appendix (A7.5, A7.6b, A7.9, A7.10b, A7.10c, A7.13-A7.15)
- Reg E appendix (A8.1, A8.2, A8.4b, A8.4c, A8.7, A8.12)
- Attrition appendix (A9.2, A9.4, A9.5, A9.7, A9.8, A9.13)
- Insight slides (S1-S8)

### Slide Types

| Type | Description | Example |
|------|-------------|---------|
| `screenshot` | Single chart image, nearly full width | Most analysis slides |
| `screenshot_kpi` | Chart on left, KPI callout values on right | A9.1 (attrition rate), A9.9-A9.12 (impact) |
| `multi_screenshot` | Two charts side by side | Merged pairs (A7.6a+A7.4, A8.10+A8.11, etc.) |
| `mailer_summary` | 3-column: donut chart, bar chart, text bullets | A13 monthly and aggregate summaries |
| `title` | Title slide with centered text | P01, P03, P07 |
| `section` | Section divider | Between DCTR, Reg E, Attrition |
| `summary` | 3x3 bullet grid | Not currently used in standard deck |
| `blank` | Empty slide for manual content | P04, P05, P06, P10, P12 |

### Consolidation Logic

Some slides are merged side-by-side for the main deck, with the individual versions moved to the appendix:

| Merged Slide | Left | Right | Title |
|-------------|------|-------|-------|
| DCTR trajectory | A7.6a | A7.4 | DCTR Trajectory: Recent Trend & Segments |
| DCTR funnel | A7.7 | A7.8 | DCTR Funnel: Historical vs TTM |
| DCTR age | A7.11 | A7.12 | DCTR Opportunity: Age Analysis |
| Reg E funnel | A8.10 | A8.11 | Reg E Funnel: All-Time vs TTM |
| Reg E age | A8.5 | A8.6 | Reg E Opportunity: Age Analysis |
| Attrition profile | A9.3 | A9.6 | Attrition Profile: Open vs Closed & Personal vs Business |

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

**20 analysis modules**:

| Section | Modules | Slide IDs | What It Analyzes |
|---------|---------|-----------|-----------------|
| Overview | stat_codes, product_codes, eligibility | A1, A1b, A3 | Portfolio composition and opening trends |
| DCTR | penetration, trends, branches, funnel, overlays | DCTR-1 to DCTR-16, A7.4-A7.15 | Debit card take rates, trends, funnels, branch heatmaps |
| Reg E | status, branches, dimensions | A8.1-A8.13 | Regulation E opt-in status and breakdowns |
| Attrition | rates, dimensions, impact | A9.1-A9.13 | Account closures, revenue impact, velocity |
| Value | analysis | A11.1, A11.2 | Revenue per account: debit card holders vs non-holders, Reg E opt-in vs not |
| Mailer | insights, response, impact | A12.x, A13.x, A14.x, A15.x | Campaign response rates, spend lift, market impact |
| Insights | synthesis, conclusions | S1-S8 | Cross-section findings and recommendations |

### Transaction (TXN)

Analyzes debit card transaction CSV files. 35 analyses covering spending patterns, merchant categories, interchange revenue, and competitive positioning.

**Input**: Transaction CSV file (columns: `merchant_name`, `amount`, `primary_account_num`, `transaction_date`, `mcc_code`). Optional ODD file for demographics.

**Output**: Excel report + Plotly charts

**What it covers**: M1-M14 (spending, merchants, MCC analysis, interchange, demographics, campaigns, lifecycle) + scorecard

### ICS (Instant Card Services)

Three sub-pipelines for ICS program analysis:

- **ICS Analysis**: 37 analyses on ICS program data (distribution, source breakdown, balance, activity)
- **ICS Append**: Matches and merges ICS account data onto ODD files (adds `ICS Account` and `ICS Source` columns)
- **ICS Referral Intelligence**: 8-step pipeline analyzing referral patterns, entity networks, and influence scoring

**Input**: ICS Excel/CSV files

**Output**: Excel report + Plotly charts + PowerPoint deck

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
  Output\                        Pipeline working output (per-client subfolders with charts, Excel, PPTX)
  Logs\                          Pipeline log files

  _archive\                      Stale folders moved here by cleanup_and_organize.bat
```

Each CSM has their own folder structure:

```
{CSM Name}\
  {ClientID}\
    {ClientID}-{year}-{month}-{name}-ODD.xlsx
    {ClientID}_transactions.csv     (if TXN)
    {ClientID}_ICS_YYYY.MM.xlsx     (if ICS)
```

### The Two Output Folders

There are two output folders on the M: drive that serve different purposes:

| Folder | Purpose | Who Uses It |
|--------|---------|------------|
| `M:\ARS\Output\` | **Working output** -- where the pipeline writes results during processing. Contains per-client subfolders with charts, Excel, PPTX, and run reports. | Pipeline (automatic) |
| `M:\ARS\Analysis Outputs\` | **Final deliverables** -- curated results for VP review and CSM distribution. Files are copied or moved here after QA. | CSMs / VP (manual or archive step) |

The pipeline writes to `Output\` by default. The `Analysis Outputs\` folder is the "clean" destination where reviewed, approved deliverables go.

### Output Structure (Per Client Run)

```
M:\ARS\Output\{ClientID}\{YYYY.MM}\
  charts/                           Individual chart PNGs (one per analysis)
  {ClientID}_{YYYY.MM}_deck.pptx    PowerPoint presentation
  {ClientID}_{YYYY.MM}_analysis.xlsx Excel workbook (one tab per analysis + Summary)
  {ClientID}_{YYYY.MM}_run_report.json  Diagnostic report (slide status, success/fail)
```

---

## Codebase Structure

```
analysis-platform/
  packages/
    shared/              Foundation: unified types, context, config (81 tests)
    ars_analysis/        ARS pipeline: 20 modules, deck builder, Excel formatter (545 tests)
    txn_analysis/        Transaction pipeline: 35 analyses (597 tests)
    ics_toolkit/         ICS pipeline: 37 analyses + append + referral (1,049 tests)
    platform_app/        Orchestrator, Streamlit UI, CLI dispatcher (60 tests)
  tests/
    ars/                 ARS tests
    txn/                 Transaction tests
    ics/                 ICS tests
    shared/              Shared tests
    platform/            Platform tests
    integration/         End-to-end tests (26)
    e2e_data/            Synthetic data fixtures
  scripts/
    cleanup_and_organize.bat   Archive stale M: drive folders
  config/                      Default configuration files
  plans/                       Implementation plans and specifications
```

---

## Troubleshooting

**"uv not found"** -- Install uv: `pip install uv`

**"File is unformatted"** -- Click "Format Now" in Data Ingestion, or use `run.bat` which formats automatically.

**"ICS fields missing"** -- Run ICS append first to add ICS Account and ICS Source columns to the ODD file.

**Charts look blank on Windows** -- Known issue with kaleido on Windows. Charts still export correctly to PowerPoint; they just can't be previewed in tests.

**Network path errors on M: drive** -- Known issue (#24). The Excel writer creates temp files that can fail on network paths. Use the `use_local_temp` batch option to process locally and copy results back.

**Eligible accounts = 0** -- Check `clients_config.json` for the client. Ensure `EligibleStatusCodes` and `EligibleProductCodes` match the actual values in the ODD file. The pipeline logs the top 10 Stat Code values at startup for comparison.

**Reg E results empty** -- Verify `RegEColumn` in config matches the actual column name in the ODD file. Check that `RegEOptInCode` contains the correct opt-in values.

**Value slides (A11.1/A11.2) not generating** -- The pipeline auto-detects the debit card column. Check that the ODD file has one of: `Debit?`, `Debit`, `DC Indicator`, or `DC_Indicator`.

**PPTX build crashes** -- The deck builder now has per-slide error handling. Check the run report JSON for which specific slide failed and why. Common cause: chart file was not generated (upstream module failed).

**Runtime is slow** -- Make sure you are selecting specific modules in the Module Library, not running all 20. The module selection is wired through to the runner; only selected modules execute.

**Dashboard port stuck (localhost:8501 already in use)** -- Kill the old Streamlit process:

```cmd
REM Find the process using port 8501
netstat -ano | findstr :8501

REM Kill it (replace 12345 with the PID from the last column)
taskkill /F /PID 12345

REM Or kill all in one shot:
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8501') do taskkill /F /PID %a
```
