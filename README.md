# Analysis Platform

Unified analysis platform for CSI Velocity. Combines three pipelines into one tool: **ARS** (account reviews), **Transaction** (debit card analytics), and **ICS** (Instant Card Services).

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

## How to Use

There are three ways to run analyses: **batch scripts** (recommended for production), the **web dashboard**, or the **command line**.

### Option 1: Full Pipeline (run.bat)

Double-click `run.bat` on the Windows machine. It does everything automatically:

1. Retrieves ODD files from CSM source paths
2. Formats them (adds calculated columns needed for analysis)
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

**Output**: PowerPoint deck + Excel report + 70+ chart images

**What it covers**:

- Portfolio overview (stat codes, eligibility, opening trends, branches)
- DCTR take rates, trends, funnels, branch heatmaps, vintage analysis
- Reg E opt-in status, trends, age/branch/product breakdowns
- Attrition rates, closure profiles, revenue impact, velocity tracking
- Debit card value and Reg E opt-in value analysis
- Mailer campaign response, insights, and market impact

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
    clients_config.json       Client-specific settings
  Template\
    Template12.25.pptx        PowerPoint slide template
  Output\
    Presentation Excels\      Master Excel copies
    Archive\{Client}\{year}\  Monthly archive
  Input\                      Watch folder
```

Each CSM has their own folder structure:

```
{CSM Name}\
  {ClientID}\
    {ClientID}-{year}-{month}-{name}-ODD.xlsx
    {ClientID}_transactions.csv     (if TXN)
    {ClientID}_ICS_YYYY.MM.xlsx     (if ICS)
```

---

## Troubleshooting

**"uv not found"** -- Install uv: `pip install uv`

**"File is unformatted"** -- Click "Format Now" in Data Ingestion, or use `run.bat` which formats automatically.

**"ICS fields missing"** -- Run ICS append first to add ICS Account and ICS Source columns to the ODD file.

**Charts look blank on Windows** -- This is a known issue with kaleido on Windows. Charts still export correctly to PowerPoint; they just can't be previewed in tests.

**Network path errors on M: drive** -- Known issue (#24). The Excel writer creates temp files that can fail on network paths. Run from a local copy if needed.
