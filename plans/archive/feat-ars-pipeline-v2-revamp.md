# feat: ARS Pipeline v2 -- Production-Ready Team Deployment

**Type:** Enhancement (Major Rewrite)
**Date:** 2026-02-13
**Status:** Draft (Enhanced)
**Repositories:**
- https://github.com/JG-CSI-Velocity/ars_analysis-jupyter.git (main pipeline)
- https://github.com/JG-CSI-Velocity/ics_append.git (ICS append process)
- https://github.com/JG-CSI-Velocity/txn-analysis.git (transaction analysis — original Jupyter scripts)

---

## Enhancement Summary

> This plan has been deepened with findings from 10 parallel review agents (Python quality, architecture, security, performance, simplicity, patterns, agent-native, testing, Streamlit, git cleanup). Key changes from the original draft:

### Critical Fixes (Must Address Before Any Code Ships)

1. **SECURITY: Git history contains production client data** — Solved by creating a fresh `ars-pipeline` repo. Old repos stay as-is for reference. No data files brought into new repo (Phase 0).
2. **BUG: `plt.style.use()` mutates global state** — Must change to `plt.style.context()` context manager in `chart_figure()` (Phase 1).
3. **SECURITY: `diagnose=True` leaks local variables in tracebacks** — Must set `diagnose=False` in production log sinks, or gate behind `--debug` flag (Phase 1).
4. **Pin `numpy<3.0`** alongside pandas — numpy 3.0 removes deprecated APIs that pandas 2.x uses (Phase 1).

### Simplification Decisions (Reducing Scope)

5. **Consolidate 7 phases → 5 phases** — Phases 4 (CLI) and 5 (Scheduling) merged into Phase 3 alongside pipeline migration; testing/CI pulled into Phase 0 setup.
6. **Drop plugin auto-discovery (`pkgutil.walk_packages`)** — For 15 known modules, use an explicit ordered list. Simpler, deterministic, no import side effects.
7. **Drop `PipelineStep.max_retries`** — Retry logic is premature; no step has a known transient failure mode.
8. **Flatten exception hierarchy** — Reduce from 8 classes to 4 (`ARSError`, `ConfigError`, `DataError`, `OutputError`).
9. **`required_columns` / `required_ctx_keys` as class attributes** — Not abstract methods. Lists don't need polymorphism.

### Performance Wins (Low Effort, High Impact)

10. **Enable pandas Copy-on-Write** — Single line: `pd.set_option("mode.copy_on_write", True)`. Eliminates 55+ unnecessary `.copy()` calls.
11. **Remove 14 redundant `pd.to_datetime()` calls** — Pre-parse once at data load; all downstream modules get pre-parsed dates.
12. **Eliminate dual Excel write pattern** — Write source Excel once, copy the file for master, instead of writing twice.

### Automation & Scripting

13. **Add `--json` flag to data-emitting CLI commands** — `ars run`, `ars batch`, `ars scan` output structured JSON for scripting batch workflows across 300+ clients.
14. **Add `ars scan` subcommand** — "What clients have data ready this month?" is the #1 team question at scale.
15. **Defer `ars config show` and `ars history`** — Move to Phase 4 alongside scheduling; not critical path.

### Testing Strategy

16. **Synthetic ODD data factory** — `conftest.py` fixture generating 10-row DataFrames with all required columns + edge cases.
17. **`@pytest.fixture` for matplotlib** — Use `matplotlib.use("Agg")` + `plt.close("all")` teardown in `conftest.py`.
18. **Move test scaffolding to Phase 0** — Create `tests/conftest.py` and test infrastructure early so every phase can add tests incrementally.

---

## Overview

Revamp the ARS Analysis Pipeline from a developer-oriented prototype into a production-ready, team-deployable tool that non-technical CSMs can operate independently at scale. The pipeline processes **300+ client reviews** across a team of CSMs using **8 composable analysis modules** (Overview, DCTR, Reg E, Attrition, Value, Mailer, Transaction, ICS) totaling 100+ individual analyses. Modules are independent but connected — they share data where applicable and can be run individually, in preset groups, or as a comprehensive analysis. CSMs select which clients to process (one, some, or all) and which modules to run. The revamp transforms flat Python files across 3 repos into a properly packaged application with a 3-step automated workflow, structured logging, validated configuration, and an extensible module system.

**Scale:** 300+ client reviews, team of CSMs, batch runs of 30+ minutes.

**Target users:** CSMs (non-technical, primary), Analysts (semi-technical), VP (output consumer / compliance oversight), Developer (maintainer).

---

## Problem Statement

The current pipeline works but has critical problems for team deployment:

1. **Not installable** -- 17 flat Python files in main repo root, ICS process in a separate repo, original transaction scripts in a third repo — no unified `pyproject.toml`, no declared dependencies
2. **Hardcoded paths** -- 8+ Windows paths across 5 files pointing to `C:\Users\james.gilmore\...`
3. **No tests** -- 0 test files for the main pipeline (12,000+ lines); only `txn_analysis/` has tests
4. **Leaky secrets** -- `clients_config.json` (12 real clients), `.xls` code sheets, and `.pdf` presentations committed to git
5. **Monolithic files** -- `dctr.py` (2,631 lines), `pipeline.py` (1,984 lines), `reg_e.py` (1,587 lines)
6. **No structured logging** -- `print()` + callback pattern throughout; only `retrieve_odd.py` uses `logging`
7. **Fragile error handling** -- `try/except Exception` with `traceback.print_exc()`; silent exception swallowing in `_exec_report()`, `_safe()`, `run_tracker._save()`
8. **No dependency pinning** -- `pandas>=2.0` could resolve to 3.x and break everything
9. **Contradictory plans** -- 8 plan documents in `plans/` with overlapping and conflicting assumptions
10. **No review schedule management** -- stated requirement with zero specification

---

## Proposed Solution

### Architecture: `src/` Layout Python Package

```
ars-pipeline/                           # Repository root (renamed from ars_analysis-jupyter)
|
|-- pyproject.toml                      # Single source of truth: deps, build, entry points
|-- README.md                           # Setup guide, quick start, architecture overview
|-- CHANGELOG.md                        # Release history
|-- .gitignore                          # Comprehensive (see Phase 1)
|
|-- src/
|   |-- ars/
|   |   |-- __init__.py                 # Package version
|   |   |-- __main__.py                 # python -m ars entry point
|   |   |-- cli.py                      # Typer CLI: format, scan, run, batch, validate, init
|   |   |-- config.py                   # Pydantic settings + JSON loader
|   |   |-- logging_setup.py            # Loguru configuration
|   |   |-- exceptions.py               # Custom exception hierarchy
|   |   |
|   |   |-- pipeline/
|   |   |   |-- __init__.py
|   |   |   |-- context.py             # PipelineContext dataclass (replaces raw dict)
|   |   |   |-- runner.py              # Orchestrator: format -> analyze -> generate
|   |   |   |-- steps/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- format.py          # Step 1: retrieve + format ODD
|   |   |   |   |-- analyze.py         # Step 2: dispatch to analytics modules
|   |   |   |   |-- generate.py        # Step 3: deck build + executive report
|   |   |   |   |-- load.py            # Data loading + column validation
|   |   |   |   |-- subsets.py         # Filtered DataFrame creation
|   |   |
|   |   |-- analytics/
|   |   |   |-- __init__.py            # discover_modules()
|   |   |   |-- base.py               # AnalysisModule ABC + AnalysisResult dataclass
|   |   |   |-- registry.py           # @register decorator + module ordering
|   |   |   |-- overview/             # A1-A5: stat codes, products, eligibility
|   |   |   |   |-- __init__.py
|   |   |   |   |-- stat_codes.py
|   |   |   |   |-- product_codes.py
|   |   |   |   |-- eligibility.py
|   |   |   |-- dctr/                 # A6-A7: debit card penetration, trends, branches
|   |   |   |   |-- __init__.py
|   |   |   |   |-- penetration.py
|   |   |   |   |-- trends.py
|   |   |   |   |-- branches.py
|   |   |   |   |-- funnel.py
|   |   |   |   |-- overlays.py
|   |   |   |-- rege/                 # A8: Reg E analysis (13 analyses)
|   |   |   |   |-- __init__.py
|   |   |   |   |-- analysis.py
|   |   |   |-- attrition/            # A9: account attrition (13 analyses)
|   |   |   |   |-- __init__.py
|   |   |   |   |-- analysis.py
|   |   |   |-- value/                # A11: value of debit card + Reg E
|   |   |   |   |-- __init__.py
|   |   |   |   |-- analysis.py
|   |   |   |-- mailer/               # A12-A15: mailer insights, response, impact
|   |   |   |   |-- __init__.py
|   |   |   |   |-- insights.py
|   |   |   |   |-- response.py
|   |   |   |   |-- impact.py
|   |   |   |   |-- common.py
|   |   |
|   |   |-- txn_analysis/             # Transaction analysis (M1-M7, 28 analyses)
|   |   |   |-- __init__.py           # Already well-structured — migrate as-is
|   |   |   |-- pipeline.py           # Transaction orchestrator
|   |   |   |-- cli.py                # Standalone CLI for txn runs
|   |   |   |-- settings.py           # Transaction-specific config
|   |   |   |-- data_loader.py        # Load transaction CSV
|   |   |   |-- column_map.py         # Map transaction columns
|   |   |   |-- merchant_rules.py     # Merchant categorization
|   |   |   |-- competitor_patterns.py # Competitor detection rules
|   |   |   |-- financial_patterns.py # Financial services detection
|   |   |   |-- analyses/             # 28 analyses across 7 modules
|   |   |   |   |-- __init__.py       # ANALYSIS_REGISTRY
|   |   |   |   |-- base.py           # AnalysisResult (Pydantic)
|   |   |   |   |-- overall.py        # M1: top merchants
|   |   |   |   |-- mcc.py            # M2: MCC categories
|   |   |   |   |-- business.py       # M3: business merchants
|   |   |   |   |-- personal.py       # M4: personal merchants
|   |   |   |   |-- trends_*.py       # M5: trends (6 files)
|   |   |   |   |-- competitor_*.py   # M6: competitor (4 files)
|   |   |   |   |-- financial_services.py  # M7: financial services
|   |   |   |-- charts/               # Plotly visualizations
|   |   |   |-- exports/
|   |   |   |   |-- excel_report.py   # Transaction Excel export
|   |   |
|   |   |-- ics/                       # ICS module (from ics_append repo)
|   |   |   |-- __init__.py            # run_ics(ctx) entry point
|   |   |   |-- organizer.py           # Sort loose ICS files into client folders
|   |   |   |-- merger.py              # Merge REF + DM files, deduplicate, tag source
|   |   |   |-- matcher.py            # Match ICS accounts against ODD, append columns
|   |   |   |-- normalizer.py         # Account hash normalization
|   |   |   |-- validation.py         # Data quality checks + match rate thresholds
|   |   |
|   |   |-- charts/
|   |   |   |-- __init__.py
|   |   |   |-- style.py              # Constants from chart_style.py
|   |   |   |-- guards.py             # chart_figure() context manager
|   |   |   |-- ars.mplstyle           # matplotlib style sheet
|   |   |
|   |   |-- output/
|   |   |   |-- __init__.py
|   |   |   |-- deck_builder.py       # PowerPoint generation
|   |   |   |-- excel_writer.py       # Excel report writing
|   |   |   |-- report_builder.py     # HTML executive summary
|   |   |   |-- archiver.py           # File distribution + archiving
|   |   |
|   |   |-- scheduling/
|   |   |   |-- __init__.py
|   |   |   |-- models.py             # ReviewSchedule, ClientSchedule dataclasses
|   |   |   |-- tracker.py            # Run history + status tracking
|   |   |   |-- scheduler.py          # Due-date calculation, upcoming reviews
|   |   |
|   |   |-- ui/                        # Streamlit app (optional, separate entry point)
|   |   |   |-- __init__.py
|   |   |   |-- app.py                # Main Streamlit dashboard
|   |   |   |-- config_editor.py      # Client config editor page
|   |   |   |-- schedule_view.py      # Review schedule dashboard page
|
|-- tests/
|   |-- conftest.py                    # Shared fixtures, synthetic ODD data factory
|   |-- test_config.py
|   |-- test_pipeline/
|   |   |-- test_runner.py             # End-to-end smoke test
|   |   |-- test_format_step.py
|   |   |-- test_load.py
|   |-- test_analytics/
|   |   |-- test_registry.py
|   |   |-- test_overview.py
|   |   |-- test_dctr.py
|   |-- test_output/
|   |   |-- test_deck_builder.py
|   |   |-- test_excel_writer.py
|   |-- test_scheduling/
|   |   |-- test_scheduler.py
|
|-- configs/
|   |-- ars_config.default.json        # Shipped defaults (checked in)
|   |-- ars_config.json.example        # User override template
|   |-- clients_config.example.json    # Sanitized client config example
|
|-- templates/
|   |-- Template12.25.pptx             # PowerPoint template
|   |-- slide_layout_assignments.xlsx  # Layout mapping reference
```

### 3-Step Gated Workflow

Each step is tracked per client/month. A CSM cannot start Step 2 without Step 1 being completed for that client. This prevents analysis on unformatted data.

```
Step 1: FORMAT DATA (batch — run once per month for all CSMs)
  Input:  Raw ODD Excel files from each CSM's M: drive source folder
  Action: retrieve_odd (copy from CSM folders) + format_odd (calculate columns, age, mail groups)
  Output: Formatted ODD files in Test-Reports/{CSM}/{YYYY.MM}/{ClientID}/
  Tracked: RunTracker marks each client/month as "formatted"
  Gate:   Step 2 checks for "formatted" status before proceeding

Step 2: ANALYZE DATA (per client or batch)
  Input:  Formatted ODD file (must have "formatted" status) + client config
          + optional: transaction CSV, ICS revenue workbook
  Select: Which modules to run — individual, preset group, or "Comprehensive"
  Action: Load data -> validate columns -> create subsets -> run selected modules
          Each module checks its own data requirements before running
          Missing data = skip with message, not error
  Output: Chart PNGs + Excel sheets per module
  Tracked: RunTracker marks each client/month + which modules ran

Step 3: GENERATE DELIVERABLES (per client, immediately after Step 2)
  Input:  Analysis results + charts + template
  Action: Build PowerPoint deck + write Excel reports + generate executive summary
  Output: .pptx (60-80 slides) + .xlsx (3 copies) + .html executive report
  Tracked: RunTracker marks each client/month as "completed"
```

**Step 1 is separate from Steps 2-3 by design.** Formatting is a bulk operation (retrieve + transform all ODD files for the month), while analysis is per-client. The typical workflow:

```
Monday:    CSM or admin runs "ars format --month 2026.02" for all CSMs
           → 300+ ODD files retrieved and formatted
           → Dashboard shows which clients are now "ready for analysis"

Mon-Fri:   CSMs open Streamlit, see their ready clients, run analysis in batches
           → Only clients with "formatted" status can be selected
           → Unformatted clients show "Pending Format" (grayed out)
```

> **Note:** The current `MAX_PER_CSM = 1` in `format_odd.py` is a testing safeguard — remove it entirely. CSMs choose which clients to process: one, some, or all of their assigned clients. No artificial limit.

### Analysis Modules (Composable Architecture)

Analysis is **not** a monolithic "type" you pick from a dropdown. It's a set of **independent modules** that share data where applicable. Each module declares what data it needs. The CSM picks which modules to run — individually, in groups, or "comprehensive" (all modules with available data). This makes it easy to add new modules (like ICS) without touching existing ones.

#### Data Sources

| Source | Description | Used By |
|--------|-------------|---------|
| **Formatted ODD** | Core account data (formatted in Step 1) | All ODD-based modules |
| **Transaction CSV** | Debit card transaction detail by merchant | Transaction module |
| **ICS REF + DM files** | Referral and Direct Mail account lists from ICS portal (per client) | ICS module |
| **ICS Revenue Workbook** | Separate workbook with ICS-specific revenue metrics (not in ODD) | ICS module |

**ICS data flow:** The ICS module (from `ics_append` repo) has its own 3-step process:
1. **Organize** — sort loose ICS files into client folders by 4-digit client ID prefix
2. **Merge** — combine REF (referral) and DM (direct mail) account lists into one file per client, deduplicate, tag source
3. **Match** — match merged ICS accounts against the formatted ODD by account hash, appending 2 columns: `ICS Account` (Yes/No) and `ICS Source` (REF/DM/Both)

After matching, the annotated ODD has ICS flags that downstream modules can use for segmentation (e.g., DCTR by ICS vs non-ICS accounts, value of ICS-acquired accounts).

#### Module Inventory

Each module is self-contained. Modules that share a data source can see each other's results (e.g., Mailer can reference Reg E opt-in status, Value can reference DCTR penetration).

| Module | Data Source | Analyses | Status | Description |
|--------|-------------|----------|--------|-------------|
| **Overview** | ODD | 5 | Implemented | Stat codes, debit card, eligibility funnel, opening trends, branch distribution |
| **DCTR** | ODD | 26 | Implemented | Debit card penetration rates, trends, branches, funnels, heatmaps, vintage curves, decade overlays |
| **Reg E** | ODD | 13 | Implemented | Opt-in rates by branch, age, product; heatmaps, funnels, 24-month trends |
| **Attrition** | ODD | 13 | Implemented | Closure rates, duration, by branch/product/tenure/balance, revenue impact, velocity |
| **Value** | ODD | 2 | Implemented | Revenue value of debit card holder, revenue value of Reg E opt-in |
| **Mailer** | ODD | Dynamic | Implemented | Per-mail-month spend & swipes, response rates, demographics, market reach, spend share |
| **Transaction** | ODD + TXN CSV | 28+ | Implemented | Top merchants, MCC categories, competitor detection, trends, threat scoring, financial services. Can run on all accounts or eligible only. Embedded package in `ars_analysis-jupyter/txn_analysis/`; original Jupyter scripts in `txn-analysis` repo have additional analyses (non-bank threats, per-competitor segmentation, financial services deep drill-down) to port. |
| **ICS** | ODD + ICS REF/DM files + Revenue WB | TBD | Has repo (`ics_append`), needs integration | Insured Cash Sweep: annotates ODD with ICS account flags (Yes/No) + source (REF/DM/Both), separate revenue metrics, enables ICS-specific segmentation across all other modules |

#### How Modules Connect

```
Formatted ODD (shared base)
    |
    |-- Overview ──────────────── stat codes, eligibility, branches
    |-- DCTR ──────────────────── debit card penetration (uses eligibility subsets)
    |-- Reg E ─────────────────── opt-in rates (uses eligibility subsets)
    |-- Attrition ─────────────── account closures (uses open/closed subsets)
    |-- Value ─────────────────── revenue impact (references DCTR + Reg E results)
    |-- Mailer ────────────────── spend/swipes by mail month (references Reg E status)
    |
    +-- Transaction CSV (additional source)
    |   |-- Transaction ───────── merchant intelligence, competitor detection
    |   |                          can filter: all accounts OR eligible only
    |
    +-- ICS REF/DM files + Revenue Workbook (additional sources)
        |-- ICS ───────────────── organize -> merge -> match against ODD
        |                          appends: ICS Account (Yes/No), ICS Source (REF/DM/Both)
        |                          enables ICS segmentation in OTHER modules
        |                          + ICS-specific revenue metrics from separate workbook
```

**Key design principle:** Each module runs independently. But when modules run together, later modules can read earlier modules' results from the shared `PipelineContext.results` dict. This enables cross-module insights (e.g., "Value" module can see DCTR penetration rates and Reg E opt-in rates to calculate combined revenue impact).

#### CSM Selection Flow

1. CSM opens Streamlit (or CLI) and selects **month**
2. CSM sees their assigned clients with formatting status
3. CSM selects **which clients** to process (one, some, or all — no limit)
4. CSM selects **which modules** to run:
   - Individual modules (e.g., just DCTR, or just Transaction)
   - Preset groups (e.g., "Core ARS" = Overview + DCTR + Reg E + Attrition + Value + Mailer)
   - **Comprehensive** = all modules with available data for that client
5. Pipeline checks data availability (has transaction CSV? has ICS data?) and runs selected modules
6. Modules that lack required data are skipped with a clear message, not an error

### Dual Interface Strategy

**Streamlit (primary)** -- remains the main interface for CSMs. The existing app.py is working and deployed. Refactor it to import from the new `src/ars/` package instead of flat files.

**Typer CLI (secondary)** -- added for developer use, batch automation (Task Scheduler), and scripting. Rich progress bars provide operational visibility during 300+ client batch runs.

Both interfaces import from the same `src/ars/` package core. No business logic lives in either UI layer.

---

## Feature Set

### For CSMs (Streamlit UI)

| Feature | Description |
|---------|-------------|
| **One-Click Run** | Select client(s), pick modules, click "Run" — pipeline runs selected analyses, generates deliverables |
| **Module Selection** | Pick individual modules (DCTR, Reg E, Transaction...), a preset group ("Core ARS"), or "Comprehensive" (all modules with available data). Modules with missing data are skipped gracefully. |
| **Client Selection** | Pick one, some, or all assigned clients for the selected month — no artificial limits |
| **Batch Processing** | Select a month, check off clients (or "Select All"), run the full batch with a live progress bar showing client N of M |
| **Client Scan** | Dashboard shows which clients have data ready for the selected month, with status indicators (ready / missing / already processed) |
| **Run History** | See when each client was last processed, by whom, and whether it succeeded or failed |
| **Review Schedule** | View which clients are due this month/quarter based on their assigned cadence; see overdue reviews highlighted |
| **Client Config Editor** | Add/edit client settings (eligible stat codes, product codes, fee rates) without touching JSON files |
| **Error Messages** | When something goes wrong, see a plain-English explanation + suggested fix — not a stack trace |
| **Progress Tracking** | Live status: "Processing Guardians CU — Step 2 of 3: Analyzing data... (23 of 50 clients complete)" |

### For Developers / Automation (CLI)

| Feature | Description |
|---------|-------------|
| **`ars run <file>`** | Process a single client. `--modules dctr,rege,txn` selects modules (default: all available). `--json` for scripting. |
| **`ars batch <folder>`** | Process all clients in a month folder. `--modules` selects modules. Rich progress bar. `--json` for scripted pipelines. |
| **`ars scan --month 2026.02`** | List all clients with data ready for a given month. Essential for scripting batch workflows across 300+ clients. |
| **`ars validate <file>`** | Check an ODD file for required columns without running the full pipeline. Quick pre-flight check. |
| **`ars init`** | Set up a new machine: create config files, verify paths, check dependencies. Onboarding a new CSM in 15 minutes. |
| **`ars schedule list`** | Rich table of all clients, their cadence, assigned CSM, last run date, next due date. |
| **`ars schedule due`** | Filter to only clients due this month — pipe directly into `ars batch`. |
| **Structured Logging** | Every run logs to `pipeline_{date}.log` (full detail) + `errors.log` (errors only). Rotated, compressed, retained 30/90 days. |

### For VP / Management

| Feature | Description |
|---------|-------------|
| **PowerPoint Decks** | 60-80 slide presentations per client, auto-generated from data. Consistent formatting across all 300+ clients. |
| **Executive Summaries** | HTML report highlighting key findings, trends, and action items per client. |
| **Schedule Compliance** | Dashboard view showing which reviews are complete, pending, or overdue across the team. |
| **Audit Trail** | Full log of every pipeline run — who processed what, when, and whether it succeeded. |

### Output Per Client

Output scales with which modules are selected. Each module contributes its slides/sheets to the combined deliverables.

| Module | PowerPoint Slides | Excel Sheets | Charts |
|--------|------------------|--------------|--------|
| Overview | 5 slides | stat codes, products, eligibility | 5 PNGs |
| DCTR | 26+ slides | penetration tables, branch data | 26 PNGs |
| Reg E | 13 slides | opt-in tables, branch heatmaps | 13 PNGs |
| Attrition | 13 slides | closure tables, revenue impact | 13 PNGs |
| Value | 2 slides | revenue comparison | 2 PNGs |
| Mailer | Dynamic (per mail month) | spend/swipe tables, response | Dynamic |
| Transaction | — (Excel only) | 28 analyses across 7 modules | Plotly charts |
| ICS | TBD | ICS eligibility, revenue metrics | TBD |

**Always produced (regardless of modules):**
- **PowerPoint deck** — combined slides from all selected modules (60-80 for full Core ARS)
- **Excel workbook** (3 copies: source, master, archive) — sheets from all selected modules
- **Executive summary** (HTML) — key findings from whichever modules ran
- **Run log** — which modules ran, which were skipped, any warnings/errors

**Comprehensive run** = all modules with available data → largest possible deliverable for that client.

---

## User Workflows

### Workflow 1: Monthly Data Formatting (Admin / Lead CSM)

This runs once per month to retrieve and format all ODD files. Must complete before any CSM can run analysis.

```
Admin opens Streamlit dashboard → "Format Data" page
        |
        v
Selects month: "February 2026"
Clicks "Retrieve & Format All"
        |
        v
Step 1a — Retrieving ODD files from CSM source folders:
   Scanning JamesG (M:\JamesG\OD Data Dumps)... 52 files found
   Scanning GMiller (M:\GMiller\OD Data Dumps)... 38 files found
   Scanning Aburgard (M:\Aburgard\ODDD)... 45 files found
   ... copying to Test-Reports/CSM/2026.02/ClientID/
        |
        v
Step 1b — Formatting ODD files:
   "Formatting 1 of 312: 1200-2026-02-Guardians CU-ODD.xlsx"
   ... (7-step transform: delete PYTD, calculate totals, age, mail groups, control segments)
   "Formatting 312 of 312: 4501-2026-02-Heritage CU-ODD.xlsx"
        |
        v
Summary:
   308 clients formatted successfully
   3 clients had errors (logged — missing columns in source ODD)
   1 client skipped (ZIP file corrupt)
   RunTracker updated: 308 clients marked "formatted" for 2026.02
        |
        v
Dashboard now shows 308 clients as "Ready for Analysis" (green)
CSMs can begin Workflow 2
```

**CLI equivalent:** `ars format --month 2026.02 --json`

### Workflow 2: CSM Analysis Run (Streamlit)

A non-technical CSM processing their assigned clients. **Requires Step 1 (formatting) to be complete.**

```
CSM opens Streamlit dashboard in browser
        |
        v
Dashboard shows "February 2026" with client list
   - 47 clients ready for analysis (green — formatted)
   - 3 clients pending format (gray — cannot select)
   - 12 clients already processed (blue)
        |
        v
CSM checks the 47 ready clients (one, some, or all)
CSM selects modules:
   [x] Core ARS (Overview, DCTR, Reg E, Attrition, Value, Mailer)
   [ ] Transaction (grayed out if no transaction CSV available)
   [ ] ICS (grayed out if no ICS data available)
   — or clicks "Comprehensive" to select all available
        → clicks "Run Analysis"
        |
        v
Progress bar: "Processing client 1 of 47: Guardians CU"
   Running Overview... DCTR... Reg E... Attrition... Value... Mailer...
   Generating deliverables...
"Processing client 2 of 47: Connex CU"
   ... (continues for ~25 minutes)
        |
        v
Summary table appears:
   | Client           | Status  | PowerPoint        | Excel             |
   |------------------|---------|-------------------|-------------------|
   | Guardians CU     | Success | M:/1200/2026.02/  | M:/1200/2026.02/  |
   | Connex CU        | Success | M:/1453/2026.02/  | M:/1453/2026.02/  |
   | Acme CU          | FAILED  | —                 | Error: see log    |
        |
        v
CSM clicks output path → opens PowerPoint to review before sending to client
Failed clients show error message: "Acme CU: Missing column 'DC Indicator' — contact data team"
```

### Workflow 3: Batch Automation (CLI + Task Scheduler)

For scheduled overnight processing of all formatted clients.

```
Windows Task Scheduler runs monthly:

  Step 1 (1st of month, 2 AM):
    ars format --month 2026.02 --json > format_results.json

  Step 2 (2nd of month, 2 AM):
    ars batch --month 2026.02 --json > analysis_results.json
    (only processes clients with "formatted" status)

        |
        v
Next morning, CSMs open Streamlit dashboard
   - "Run History" tab shows overnight results
   - Green: 285 clients processed successfully
   - Red: 3 clients failed (with error details)
   - Yellow: 20 clients still pending (no ODD data yet)
```

### Workflow 4: New Client Onboarding

Adding a new client to the pipeline.

```
CSM opens Streamlit → "Client Config" page
        |
        v
Clicks "Add New Client"
   - Enters Client ID: 2001
   - Enters Client Name: "River Valley CU"
   - Sets eligible stat codes: A01, A02, A05
   - Sets eligible product codes: DDA, SAV
   - Sets cadence: Quarterly
   - Assigns CSM: "Sarah K"
        |
        v
Config saved to clients_config.json
Client appears in schedule: "Next review: April 2026"
        |
        v
When ODD data is placed in M:/2001/2026.04/
Client appears as "ready" on the dashboard
```

### Workflow 5: Error Investigation

When a client fails to process.

```
CSM sees "FAILED" status for Acme CU on dashboard
        |
        v
Clicks the error row → sees:
   "Data Problem: Column 'DC Indicator' not found in ODD file.
    This column is required for the DCTR analysis.
    Check with the data team that the ODD export includes all required fields."
        |
        v
CSM forwards the error to the data team
(or) Developer checks errors.log for full stack trace + context
```

### Workflow 6: VP Schedule Review

VP checking compliance across the team.

```
VP opens Streamlit → "Review Schedule" page
        |
        v
Sees table:
   | Client           | Cadence   | CSM       | Last Run   | Status    |
   |------------------|-----------|-----------|------------|-----------|
   | Guardians CU     | Monthly   | James G   | 2026-02-10 | Complete  |
   | River Valley CU  | Quarterly | Sarah K   | 2025-12-15 | Due       |
   | Heritage CU      | Monthly   | James G   | —          | OVERDUE   |

Summary: 285/300 complete, 12 pending, 3 overdue
        |
        v
VP filters by "Overdue" → sees 3 clients that need attention
VP filters by CSM → sees workload distribution
```

---

## Technical Approach

### Phase 0: New Repository + Safety Net

**Goal:** Create a fresh `ars-pipeline` repo (no secrets in history), set up `.gitignore`, pre-commit hooks, package skeleton, and test scaffolding. Old repos (`ars_analysis-jupyter`, `ics_append`, `txn-analysis`) stay as-is for reference — no destructive history rewriting needed.

> **Why a new repo instead of cleaning the old one?** The old repo has production client data in git history (12 real clients with names, IDs, paths). Purging with `git-filter-repo` rewrites ALL commit hashes, requiring every team member to re-clone. A fresh repo is simpler: start clean, bring in code without the data files.

#### Tasks

1. **Create the new `ars-pipeline` repository**

```bash
# Create new repo on GitHub (JG-CSI-Velocity org)
gh repo create JG-CSI-Velocity/ars-pipeline --private --clone

# Set up src/ layout
mkdir -p src/ars tests configs templates
```

2. **Expand `.gitignore`**

```gitignore
# Data files (NEVER commit client data)
*.xlsx
*.xls
*.csv
*.pdf
*.pptx
*.png
*.jpg
*.zip

# Config with secrets
clients_config.json
ars_config.json

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.eggs/

# Logs
*.log
pipeline log/

# IDE
.vscode/
.idea/
*.code-workspace

# OS
.DS_Store
Thumbs.db

# Virtual environments
.venv/
venv/
```

3. **Install pre-commit hooks to prevent re-introduction**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

```bash
pip install pre-commit && pre-commit install
```

4. **Create sanitized example configs**

- `configs/clients_config.example.json` -- same structure, fake data (e.g., "ACME Credit Union", ID "9999")
- `configs/ars_config.default.json` -- production defaults with placeholder paths

5. **Create test scaffolding** (`tests/conftest.py`)

```python
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for CI

import pytest
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


@pytest.fixture
def synthetic_odd_df():
    """Minimal ODD DataFrame with all required columns."""
    return pd.DataFrame({
        "Date Opened": pd.to_datetime(["2025-01-15"] * 10),
        "Client ID": ["1200"] * 10,
        "Account Number": [f"ACC{i:04d}" for i in range(10)],
        "Product Code": ["DDA"] * 5 + ["SAV"] * 5,
        "Stat Code": ["A01"] * 3 + ["A02"] * 4 + ["A03"] * 3,
        "Branch": ["Main"] * 6 + ["North"] * 4,
        "Balance": [1000.0 + i * 100 for i in range(10)],
    })


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Temporary output directory for test artifacts."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture(autouse=True)
def _close_all_figures():
    """Prevent matplotlib figure leaks across tests."""
    yield
    plt.close("all")
```

6. **Delete duplicate documentation**

- Remove `REFERENCE.md` (duplicate of `README.md`)
- Consolidate plan documents into this single roadmap

#### Success Criteria
- `git log --all -- clients_config.json` returns empty (purged from all history)
- `pre-commit run --all-files` passes (gitleaks + ruff)
- `.gitignore` catches all binary/config/output patterns
- `configs/clients_config.example.json` exists with sanitized data
- `tests/conftest.py` exists with synthetic ODD factory
- Repository is safe to share with VP

---

### Phase 1: Foundation (Package Structure + Dependencies)

**Goal:** Create the installable Python package with proper dependency management, without moving any business logic yet.

#### Tasks

1. **Create `pyproject.toml`**

```toml
[project]
name = "ars-pipeline"
version = "2.0.0"
description = "ARS Automated Reporting System -- Data analysis and presentation pipeline"
requires-python = ">=3.11"
license = {text = "Proprietary"}
dependencies = [
    # Core data processing (pin both pandas AND numpy to avoid breaking changes)
    "pandas>=2.2,<3.0",
    "numpy>=1.26,<3.0",
    "matplotlib>=3.10,<4.0",
    "seaborn>=0.13",
    "openpyxl>=3.1.5",
    "python-pptx>=1.0",
    "python-dateutil>=2.8",
    "Pillow>=10.0",
    # CLI and output
    "typer[all]>=0.12",
    # Logging
    "loguru>=0.7",
    # Configuration
    "pydantic>=2.10,<3.0",
    "pydantic-settings>=2.12",
]

[project.optional-dependencies]
ui = ["streamlit>=1.30"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.8,<1.0",
]

[project.scripts]
ars = "ars.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ars"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

2. **Create `src/ars/__init__.py`**

```python
"""ARS Pipeline -- Automated Reporting System."""
__version__ = "2.0.0"
```

3. **Create `src/ars/__main__.py`**

```python
"""Allow running as `python -m ars`."""
from ars.cli import app
app()
```

4. **Create exception hierarchy** (`src/ars/exceptions.py`)

> **Research Insight (Code Simplicity):** Reduced from 8 classes to 4. Deep hierarchies add cognitive overhead without benefit — callers almost always catch `ARSError` anyway. Each exception carries structured `detail` for logging.

```python
from typing import Any


class ARSError(Exception):
    """Base exception for all ARS pipeline errors."""
    def __init__(self, message: str, *, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}

    def __repr__(self) -> str:
        if self.detail:
            return f"{type(self).__name__}({self!s}, detail={self.detail})"
        return f"{type(self).__name__}({self!s})"


class ConfigError(ARSError):
    """Configuration or client setup problem."""

class DataError(ARSError):
    """Data loading, parsing, or validation failure."""

class OutputError(ARSError):
    """Deck build, Excel write, or report generation failure."""
```

5. **Create Loguru setup** (`src/ars/logging_setup.py`)

> **Research Insight (Security Sentinel):** `diagnose=True` serializes local variables into tracebacks — this leaks client data, file paths, and DataFrame contents into log files. Use `diagnose=False` in all production sinks. Only enable with `--debug` flag.

```python
import sys
from pathlib import Path
from loguru import logger


def setup_logging(
    log_dir: Path, verbose: bool = False, debug: bool = False
) -> None:
    """Configure Loguru sinks for the ARS pipeline."""
    logger.remove()

    # Console: human-readable, colorized
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File: detailed, rotated (encoding for Windows client names)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "pipeline_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    # Errors only: quick triage file
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        rotation="5 MB",
        retention="90 days",
        backtrace=True,
        diagnose=debug,  # NEVER True in production — leaks local variables
        encoding="utf-8",
    )
```

6. **Create Pydantic config** (`src/ars/config.py`)

> **Research Insight (Kieran Python Review):** Remove `@field_validator` for path existence from `PathsConfig` — it breaks testability (tests can't construct config without real paths) and fails at import time in CI. Validate paths at runtime in `run_pipeline()`, not at config parse time.

```python
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class PathsConfig(BaseModel):
    ars_base: Path
    template: str = "Template12.25.pptx"
    # No path existence validation here — validated at runtime in runner.py


class PipelineConfig(BaseModel):
    skip_pptx: bool = False
    skip_excel_archive: bool = False
    chart_dpi: int = Field(default=150, ge=72, le=600)


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_dir: Path = Path("logs")
    rotation: str = "10 MB"
    retention_days: int = Field(default=30, ge=1)


class ReviewScheduleConfig(BaseModel):
    default_cadence: Literal["monthly", "quarterly", "annual"] = "monthly"
    review_day: int = Field(default=15, ge=1, le=28)


class ARSSettings(BaseSettings):
    model_config = SettingsConfigDict(
        json_file=["ars_config.default.json", "ars_config.json"],
        env_prefix="ARS_",
        env_nested_delimiter="__",
    )

    paths: PathsConfig
    pipeline: PipelineConfig = PipelineConfig()
    logging: LoggingConfig = LoggingConfig()
    review_schedule: ReviewScheduleConfig = ReviewScheduleConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlConfigSettingsSource(settings_cls),
        )
```

7. **Create chart guards context manager** (`src/ars/charts/guards.py`)

> **Research Insight (Performance Oracle + Kieran):** `plt.style.use()` mutates global matplotlib state permanently — if one chart sets a style, all subsequent charts inherit it even on failure. Use `plt.style.context()` which is a proper context manager that restores defaults on exit.

```python
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

_ARS_STYLE = Path(__file__).parent / "ars.mplstyle"


@contextmanager
def chart_figure(
    figsize: tuple[float, float] = (10, 6),
    dpi: int = 150,
    style: str | None = None,
    save_path: Path | None = None,
) -> Generator[tuple[Figure, Axes], None, None]:
    """Context manager guaranteeing figure cleanup + style isolation."""
    style_path = style or str(_ARS_STYLE)
    with plt.style.context(style_path):
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        try:
            yield fig, ax
            if save_path is not None:
                fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        finally:
            plt.close(fig)
```

#### Success Criteria
- `pip install -e ".[dev]"` succeeds
- `python -m ars --help` shows CLI help
- `pytest` passes (even if only a placeholder test)
- `ruff check src/` passes with zero errors

---

### Phase 2: Analytics Plugin System

**Goal:** Define the plugin contract and registry, then migrate one simple analysis as a proof-of-concept.

> **Research Insight (Code Simplicity):** For 15 known modules, `pkgutil.walk_packages` auto-discovery is over-engineered. Use an explicit ordered list — it's deterministic, debuggable, and produces the same result. The `@register` decorator + explicit import list is the sweet spot.

> **Research Insight (Kieran Python Review):** `required_columns` and `required_ctx_keys` are static data, not behavior — make them class-level tuple attributes instead of abstract methods. Use immutable `tuple[str, ...]` to prevent mutable default sharing.

> **Research Insight (Architecture Strategist):** Define `PipelineContext` as a dataclass before this phase, not in Phase 3. The `run()` method should accept `PipelineContext`, not `dict`.

#### Tasks

1. **Define PipelineContext** (`src/ars/pipeline/context.py`)

> **Post-Review Fix (Kieran):** The original 8-field dataclass missed ~30 fields from the existing `ctx` dict. Expanded to a two-layer structure that covers all real pipeline state. Typed `results` and `config` properly — no untyped `dict` escape hatches.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd


@dataclass
class ClientInfo:
    """Client identity and configuration."""
    client_id: str
    client_name: str
    month: str  # "YYYY.MM"
    eligible_stat_codes: list[str] = field(default_factory=list)
    eligible_prod_codes: list[str] = field(default_factory=list)
    nsf_od_fee: float = 0.0
    ic_rate: float = 0.0
    dc_indicator: str = "DC Indicator"
    assigned_csm: str = ""


@dataclass
class OutputPaths:
    """Resolved output directories for one pipeline run."""
    base_dir: Path = Path(".")
    charts_dir: Path = Path(".")
    excel_dir: Path = Path(".")
    pptx_dir: Path = Path(".")

    @classmethod
    def from_base(cls, base: Path, client_id: str, month: str) -> OutputPaths:
        run_dir = base / client_id / month
        return cls(
            base_dir=run_dir,
            charts_dir=run_dir / "charts",
            excel_dir=run_dir,
            pptx_dir=run_dir,
        )


@dataclass
class DataSubsets:
    """Pre-computed filtered views of the ODD data."""
    open_accounts: pd.DataFrame | None = None
    eligible_data: pd.DataFrame | None = None
    eligible_personal: pd.DataFrame | None = None
    eligible_business: pd.DataFrame | None = None
    eligible_with_debit: pd.DataFrame | None = None
    last_12_months: pd.DataFrame | None = None
    # Additional subsets added as needed during migration


@dataclass
class PipelineContext:
    """Typed container replacing the raw ctx dict (~40 keys)."""
    client: ClientInfo
    paths: OutputPaths
    settings: object = None  # ARSSettings — set at runtime to avoid circular import
    data: pd.DataFrame | None = None
    data_original: pd.DataFrame | None = None
    subsets: DataSubsets = field(default_factory=DataSubsets)
    results: dict[str, list] = field(default_factory=dict)  # module_id -> [AnalysisResult]
    all_slides: list = field(default_factory=list)
    export_log: list[str] = field(default_factory=list)
    start_date: date | None = None
    end_date: date | None = None
```

2. **Define the AnalysisModule ABC** (`src/ars/analytics/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from ars.pipeline.context import PipelineContext

SectionName = Literal["overview", "dctr", "rege", "attrition", "value", "mailer"]


@dataclass
class AnalysisResult:
    """Standard output container for one analysis."""
    slide_id: str
    title: str
    chart_path: Path | None = None
    excel_data: dict[str, pd.DataFrame] | None = None
    notes: str = ""
    success: bool = True
    error: str = ""


class AnalysisModule(ABC):
    """Base class for all analytics modules.

    At 300+ clients, the ABC provides:
    - Centralized column validation before wasting processing time
    - Uniform error isolation per module (one module failure doesn't kill the batch)
    - Consistent logging of which modules ran/failed per client
    """
    module_id: str
    display_name: str
    section: SectionName

    # Class-level attributes — subclasses override. Tuples prevent mutable default sharing.
    required_columns: tuple[str, ...] = ()
    required_ctx_keys: tuple[str, ...] = ()

    @abstractmethod
    def run(self, ctx: PipelineContext) -> list[AnalysisResult]:
        """Execute all analyses. Return ordered results."""

    def validate(self, ctx: PipelineContext) -> list[str]:
        """Check prerequisites. Return error messages (empty = OK)."""
        errors: list[str] = []
        if ctx.data is None:
            errors.append("No data loaded in context")
            return errors
        missing_cols = set(self.required_columns) - set(ctx.data.columns)
        if missing_cols:
            errors.append(f"Missing columns: {', '.join(sorted(missing_cols))}")
        return errors
```

3. **Build the registry** (`src/ars/analytics/registry.py`)

```python
from __future__ import annotations

import importlib

from loguru import logger

from ars.analytics.base import AnalysisModule
from ars.exceptions import ConfigError

_REGISTRY: dict[str, type[AnalysisModule]] = {}

# Explicit execution order — deterministic, no import side effects
MODULE_ORDER: list[str] = [
    "overview.stat_codes",
    "overview.product_codes",
    "overview.eligibility",
    "dctr.penetration",
    "dctr.trends",
    "dctr.branches",
    "dctr.funnel",
    "dctr.overlays",
    "rege.analysis",
    "attrition.analysis",
    "value.analysis",
    "mailer.insights",
    "mailer.response",
    "mailer.impact",
]


def register(cls: type[AnalysisModule]) -> type[AnalysisModule]:
    """Class decorator to register an analytics module."""
    _REGISTRY[cls.module_id] = cls
    logger.debug("Registered analytics module: {id}", id=cls.module_id)
    return cls


def get_module(module_id: str) -> type[AnalysisModule]:
    try:
        return _REGISTRY[module_id]
    except KeyError:
        raise ConfigError(
            f"Unknown analytics module: {module_id!r}",
            detail={"available": list(_REGISTRY.keys())},
        ) from None


def ordered_modules() -> list[type[AnalysisModule]]:
    """Return registered modules in execution order. Warns on missing."""
    modules: list[type[AnalysisModule]] = []
    for mid in MODULE_ORDER:
        if mid not in _REGISTRY:
            logger.warning("Module {id} in MODULE_ORDER but not registered", id=mid)
            continue
        modules.append(_REGISTRY[mid])
    return modules


def load_all_modules() -> None:
    """Import all analytics subpackages to trigger @register decorators."""
    errors: list[str] = []
    for module_id in MODULE_ORDER:
        try:
            importlib.import_module(f"ars.analytics.{module_id}")
        except Exception as exc:
            logger.error("Failed to load module {id}: {err}", id=module_id, err=exc)
            errors.append(module_id)
    if errors:
        raise ConfigError(
            f"Failed to load {len(errors)} analytics module(s)",
            detail={"failed_modules": errors},
        )
```

4. **Migrate one proof-of-concept module** -- pick the simplest analysis (A1: stat code distribution) and implement it as a plugin to validate the pattern.

5. **Write tests** for the registry and base class:

```python
# tests/test_analytics/test_registry.py
def test_register_decorator_adds_to_registry():
    ...

def test_ordered_modules_returns_deterministic_order():
    ...

def test_ordered_modules_warns_on_missing(caplog):
    ...

def test_get_module_raises_config_error_on_unknown():
    with pytest.raises(ConfigError, match="Unknown analytics module"):
        get_module("nonexistent.module")

def test_validate_catches_missing_columns(synthetic_odd_df):
    ...
```

#### Success Criteria
- `load_all_modules()` registers the proof-of-concept module
- `module.validate(ctx)` returns errors for missing columns
- `module.run(ctx)` produces `AnalysisResult` objects
- `ordered_modules()` returns modules in the defined execution order and warns on missing
- `get_module()` raises `ConfigError` (not `KeyError`) for unknown modules
- Tests pass for registry + proof-of-concept module

---

### Phase 3: Core Pipeline Migration + CLI

**Goal:** Move the pipeline orchestrator and all analysis modules into the package, replace `print()` with Loguru, and build the CLI. Scheduling is deferred to Phase 4 to reduce scope and incorporate VP feedback.

> **Research Insight (Performance Oracle):** Three high-impact, low-effort performance wins to apply during migration:
> 1. Enable pandas Copy-on-Write: `pd.set_option("mode.copy_on_write", True)` — eliminates 55+ unnecessary `.copy()` calls
> 2. Pre-parse dates once at data load — removes 14 redundant `pd.to_datetime("Date Opened")` calls
> 3. Write source Excel once, then `shutil.copy2()` for master — eliminates the dual-write pattern

> **Research Insight (Code Simplicity):** Drop `PipelineStep.max_retries` — no step has a known transient failure mode. Keep `critical` flag only for steps where failure should not abort the pipeline (e.g., archiving).

> **Research Insight (Pattern Recognition):** The existing codebase has two conflicting `AnalysisResult` patterns — one in `txn_analysis/` (Pydantic) and one proposed here (dataclass). Reconcile by using the dataclass version for the main pipeline and keeping `txn_analysis` separate until Phase 7 integration.

#### Tasks

**Pipeline Migration**

1. **Migrate `pipeline.py`** into `src/ars/pipeline/`:
   - `context.py` -- `PipelineContext` dataclass (defined in Phase 2)
   - `runner.py` -- `run_pipeline()` orchestrator with step isolation
   - `steps/load.py` -- data loading with column validation + `pd.set_option("mode.copy_on_write", True)`
   - `steps/subsets.py` -- filtered DataFrame creation (remove redundant `.copy()` calls)
   - `steps/format.py` -- retrieve + format combined
   - `steps/analyze.py` -- dispatches to analytics registry via `ordered_modules()`
   - `steps/generate.py` -- deck build + excel (single write + copy) + executive report

2. **Migrate analysis modules** into `src/ars/analytics/`:
   - `overview/` -- A1-A5 from `pipeline.py`
   - `dctr/` -- split `dctr.py` (2,631 lines) into 5 files
   - `rege/` -- from `reg_e.py` (1,587 lines)
   - `attrition/` -- from `attrition.py` (1,369 lines)
   - `value/` -- from `value.py` (645 lines)
   - `mailer/` -- from `mailer_insights.py`, `mailer_response.py`, `mailer_impact.py`, `mailer_common.py`

3. **Migrate output modules** into `src/ars/output/`:
   - `deck_builder.py` -- from root `deck_builder.py` (1,123 lines)
   - `excel_writer.py` -- extracted from pipeline flush logic (single-write pattern)
   - `report_builder.py` -- from root `report_builder.py` (678 lines)
   - `archiver.py` -- from pipeline archive step

4. **Replace all `print()` with `logger`** across migrated modules:
   - `_report(ctx, msg)` calls -> `logger.info(msg)`
   - `traceback.print_exc()` -> `logger.exception()`
   - `print(f"...")` debug -> `logger.debug()`

5. **Replace all hardcoded paths** with `ARSSettings.paths.*` lookups.

6. **Pipeline step isolation** (simplified — no retry logic):

> **Post-Review Fix (Kieran):** Raw tuples with positional booleans are unclear. Use a frozen dataclass for self-documenting `critical=False`.

```python
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PipelineStep:
    name: str
    execute: Callable[[PipelineContext], None]
    critical: bool = True


PIPELINE_STEPS: list[PipelineStep] = [
    PipelineStep("load_data", step_load),
    PipelineStep("create_subsets", step_subsets),
    PipelineStep("run_analyses", step_analyze),
    PipelineStep("build_deck", step_generate),
    PipelineStep("archive", step_archive, critical=False),
]
```

**CLI**

7. **CLI commands** (`src/ars/cli.py`):

```
ars format [--month YYYY.MM] [--json]  # Step 1: Retrieve + format all ODD files for the month
ars scan [--month YYYY.MM] [--json]    # "What clients are formatted and ready for analysis?"
ars run <file> [--config] [--output-dir] [--skip-pptx] [--verbose] [--json]  # Steps 2+3 for one client
ars batch [--month YYYY.MM] [--config] [--json]  # Steps 2+3 for all ready clients
ars validate <file>                    # Pre-flight check: are required columns present?
ars init [--dir]                       # Set up a new machine
```

Commands deferred to Phase 4: `ars config show`, `ars history`, `ars schedule list/set/due`.

> **Gate enforcement:** `ars run` and `ars batch` check RunTracker for "formatted" status before proceeding. If a client/month is not formatted, the CLI displays: `"Client 1200 (2026.02) has not been formatted yet. Run 'ars format --month 2026.02' first."`

> **Post-Review Decision:** `--json` flag on `run`, `batch`, and `scan` enables scripting batch workflows. At 300+ clients, `ars scan` is the #1 team question: "what's ready this month?"

8. **Rich error guidance** for non-technical users:

> **Post-Review Fix (Kieran):** Use `isinstance()` matching, not `type(exc)` lookup, so subclass exceptions are caught.

```python
ERROR_GUIDANCE: list[tuple[type[Exception], str, str]] = [
    (FileNotFoundError, "File Not Found", "Check the file path and ensure M: drive is connected"),
    (PermissionError, "File Locked", "Close the file in Excel and try again"),
    (DataError, "Data Problem", "The ODD file format may have changed — check column names"),
    (ConfigError, "Setup Issue", "Run 'ars init' or check ars_config.json"),
    (OutputError, "Output Error", "Ensure Template12.25.pptx is in the templates/ folder"),
]


def get_error_guidance(exc: Exception) -> tuple[str, str]:
    for exc_type, title, message in ERROR_GUIDANCE:
        if isinstance(exc, exc_type):
            return title, message
    return "Unexpected Error", "An unexpected error occurred. Check the log file for details."
```

#### Success Criteria
- `ars run <file>` executes the full pipeline via CLI
- `ars run <file> --json` outputs structured JSON result
- `ars batch <folder>` processes all clients with Rich progress bar
- `ars scan --month 2026.02` lists ready clients
- All 60+ analyses produce identical output to the current pipeline
- All logging goes through Loguru (no `print()` in `src/ars/`)
- No hardcoded paths remain
- pandas Copy-on-Write is enabled, redundant `.copy()` / `to_datetime()` calls removed

---

### Phase 4: Streamlit UI + Scheduling

**Goal:** Refactor `app.py` (1,280 lines) to import from `src/ars/` instead of flat files, convert to multi-page app, and add review scheduling (deferred from Phase 3 to incorporate VP feedback on requirements).

> **Research Insight (Streamlit Best Practices):** Use `st.Page()` + `st.navigation()` (Streamlit 1.36+) for multi-page apps — each page is a separate `.py` file, no `pages/` directory magic needed. This is the modern replacement for the legacy `pages/` folder convention.

> **Research Insight (Streamlit Best Practices):** For pipeline progress in Streamlit, define a `ProgressCallback` protocol that both CLI (Rich) and UI (Streamlit) can implement:

```python
from typing import Protocol

class ProgressCallback(Protocol):
    def on_step_start(self, step_name: str, total: int) -> None: ...
    def on_step_progress(self, current: int, message: str) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_error(self, step_name: str, error: str) -> None: ...
```

> The CLI implementation uses `Rich.Progress`; the Streamlit implementation writes to `st.session_state` and `st.progress()`.

#### Tasks

1. **Update imports** in `app.py` to use the new package:
   - `from ars.pipeline.runner import run_pipeline`
   - `from ars.config import ARSSettings`
   - `from ars.scheduling.tracker import RunTracker`

2. **Convert to multi-page app** using `st.navigation()`:

```python
# src/ars/ui/app.py
import streamlit as st

dashboard = st.Page("ui/dashboard.py", title="Dashboard", icon=":material/dashboard:")
run_history = st.Page("ui/history.py", title="Run History", icon=":material/history:")
schedule = st.Page("ui/schedule.py", title="Review Schedule", icon=":material/calendar_month:")
config_editor = st.Page("ui/config.py", title="Client Config", icon=":material/settings:")

pg = st.navigation([dashboard, run_history, schedule, config_editor])
pg.run()
```

3. **Replace `_report(ctx, msg)` callback** with Loguru + Streamlit bridge:
   - Implement `StreamlitProgressCallback` that writes to `st.session_state` for live display
   - Loguru sink that pushes messages to a `collections.deque` read by the Streamlit UI

4. **Remove duplicate config_app.py** -- fold into multi-page app.

5. **Add basic auth** (if Streamlit Community Cloud or shared deployment):

> **Research Insight (Security Sentinel):** The current Streamlit app has no authentication. For internal deployment, use `st.secrets` + a simple password gate or Streamlit's built-in `st.experimental_user` if behind an auth proxy. Full OAuth is out of scope for v2.

**Scheduling (deferred from Phase 3)**

6. **Schedule data model** (`src/ars/scheduling/models.py`):

```python
@dataclass
class ClientSchedule:
    client_id: str
    client_name: str
    cadence: Literal["monthly", "quarterly", "annual"]
    assigned_csm: str
    last_run_date: date | None
    last_run_status: Literal["success", "failed", "pending"] | None

    @property
    def next_due_date(self) -> date: ...

    @property
    def is_due(self) -> bool: ...
```

7. **Schedule storage** in `ars_config.json` with `[[schedule.clients]]` table arrays.

8. **Schedule CLI** — `ars schedule list`, `ars schedule set`, `ars schedule due`.

9. **Deferred CLI commands** — `ars config show`, `ars history`.

#### Success Criteria
- Streamlit UI works identically to current behavior
- All imports come from `src/ars/` package
- Multi-page navigation works with `st.navigation()`
- Schedule view page displays due clients with overdue highlighting
- Config editor is integrated (not a separate app)
- `ars schedule list` displays all client schedules
- `ars schedule due` filters to clients due this month
- `ProgressCallback` protocol shared between CLI and UI

---

### Phase 5: Testing + CI/CD

**Goal:** Add test coverage for critical paths and set up GitHub Actions. Test scaffolding was created in Phase 0; this phase adds comprehensive tests.

> **Research Insight (Testing Best Practices):** Key patterns for this stack:
> - **matplotlib tests**: Always use `matplotlib.use("Agg")` in conftest, `plt.close("all")` in teardown, compare chart output via `fig.savefig()` to tmp_path (not pixel comparison — too fragile)
> - **python-pptx tests**: Mock `Presentation()` or use a minimal `.pptx` fixture; assert slide count, shape text, and layout indices
> - **pandas tests**: Use `pd.testing.assert_frame_equal()` with `check_dtype=False` for flexibility
> - **Pydantic tests**: Test validation errors with `pytest.raises(ValidationError)` and check `error.errors()` for field-level messages
> - **Typer tests**: Use `typer.testing.CliRunner` — `result = runner.invoke(app, ["run", str(file)]); assert result.exit_code == 0`

#### Tasks

1. **Unit tests** (added incrementally in each phase, finalized here):
   - Config validation (valid JSON, invalid JSON, missing paths)
   - Analytics registry (register, discover, validate, ordering, `__init_subclass__`)
   - Column validation (present, missing, extra)
   - ODD filename parsing (valid, hyphenated client name, malformed)
   - Schedule calculations (monthly, quarterly, annual due dates)
   - Chart guard context manager (figure cleanup verified, style isolation)
   - Exception hierarchy (`detail` dict propagation)

2. **Smoke test** (`tests/test_pipeline/test_runner.py`):
   - End-to-end: synthetic ODD -> pipeline -> verify Excel has expected sheets, PPTX has expected slide count
   - Uses synthetic ODD factory from `conftest.py`

3. **CLI tests** using `typer.testing.CliRunner`:

```python
from typer.testing import CliRunner
from ars.cli import app

runner = CliRunner()

def test_run_with_json_flag(tmp_path, synthetic_odd_file):
    result = runner.invoke(app, ["run", str(synthetic_odd_file), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "status" in data

def test_scan_lists_ready_clients(tmp_path):
    result = runner.invoke(app, ["scan", "--month", "2026.02", "--json"])
    assert result.exit_code == 0
```

4. **GitHub Actions** (`.github/workflows/ci.yml`):

```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff
      - run: ruff check src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: pytest --cov=ars --cov-report=term-missing

  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Success Criteria
- `pytest` runs with >50% coverage on core modules
- GitHub Actions CI passes on every push (lint + test + secrets scan)
- `ruff check` passes with zero errors
- No secrets detected by gitleaks

---

## Dependencies & Prerequisites

| Dependency | Type | Risk |
|-----------|------|------|
| pandas pinning `<3.0` | Critical | pandas 3.0 has breaking changes (CoW, string dtype, offset aliases). Must pin until dedicated migration. |
| Python 3.11+ | Required | Current `setup.bat` installs 3.11.9. |
| M: drive accessibility | Runtime | All CSM data lives on M: drive. Pipeline fails without it. |
| Template12.25.pptx | Runtime | Deck builder references 17 layout indices. Template changes break deck. |
| `clients_config.json` | Runtime | 300+ client configs. Must be present but NOT in git. |

---

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Regression in chart output during migration | High | High | Add visual regression tests (save expected PNGs, compare on CI) |
| pandas 3.0 pulled by `pip install` | Medium | High | Pin `pandas>=2.2,<3.0` in pyproject.toml |
| Team disruption during migration | Medium | High | Incremental migration: keep flat files working until package is validated |
| Concurrent users corrupting shared files | Medium | Medium | File locking on `clients_config.json` and `run_tracker.json` |
| M: drive unavailability | Low | High | Config override via `ARS_BASE` env var; all paths configurable |

---

## Migration Strategy: Incremental, Not Big-Bang

The migration follows a **strangler fig pattern**: the new package wraps and delegates to existing flat files initially, then replaces them module by module.

1. **Phase 0** -- purge secrets, set up safety net (pre-commit, test scaffolding); flat files still work
2. **Phase 1** -- new package skeleton coexists with flat files; `pip install -e .` works
3. **Phase 2** -- plugin registry + ABC defined; one proof-of-concept module migrated
4. **Phase 3** -- bulk code migration + CLI; flat files become thin wrappers
5. **Phase 4** -- Streamlit app updated + scheduling + deferred CLI commands; flat file wrappers removed
6. **Phase 5** -- comprehensive tests + CI ensure nothing regressed

At each phase, the pipeline remains runnable. There is no phase where the tool stops working.

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Clients supported | ~12 (manual config) | 300+ (JSON config + schedule tracking) |
| Time for CSM to run a single client | ~3 min (manual) | ~2 min (automated scan + one click) |
| Batch processing (50 clients) | Not supported | ~25 min with live progress |
| Time to onboard a new CSM | 1-2 hours + developer help | 15 min (self-service setup guide) |
| Schedule visibility | None (spreadsheet) | Dashboard: due/overdue/complete per CSM |
| Test coverage | 0% (main pipeline) | >50% on core modules |
| Logged pipeline errors | None (print to console) | 100% captured in `errors.log` |
| Files in repo root | 17 Python files | `pyproject.toml`, `README.md`, `CHANGELOG.md` |
| Hardcoded paths | 8+ | 0 |
| Production data in git | 5+ files | 0 |

---

## Future Considerations (Not In Scope)

- **Docker deployment** -- containerize for cloud/multi-server deployment
- **Email notifications** -- send completed reports to CSMs automatically
- **pandas 3.0 migration** -- dedicated effort after the revamp stabilizes
- **Transaction analysis integration** -- `txn_analysis/` package already well-structured; integrate into the plugin registry
- **Multi-tenant mode** -- separate configs per team/region
- **Database backend** -- replace JSON tracker with SQLite for concurrent access

---

## References

### Source Repositories
- **Main pipeline:** `ars_analysis-jupyter` — pipeline.py, dctr.py, reg_e.py, attrition.py, value.py, mailer_*.py, app.py, embedded txn_analysis/ package
- **ICS append:** `ics_append` — ICS account matching process (monolithic v2 + modular `feat/modular-pipeline` branch with Typer CLI, Pydantic settings, tests)
- **Transaction scripts:** `txn-analysis` — original Jupyter cell scripts (~80 files); additional analyses not yet in embedded package (non-bank threats, per-competitor segmentation, financial services deep drill-down)

### Internal Docs
- `/Users/jgmbp/Desktop/ARS-pwrpt/ars_analysis-jupyter/README.md` -- comprehensive pipeline reference (906 lines)
- `/Users/jgmbp/Desktop/ARS-pwrpt/ars_analysis-jupyter/ARS_DATA_FLOW.md` -- data flow + dependency map
- `/Users/jgmbp/Desktop/ARS-pwrpt/ars_analysis-jupyter/plans/` -- 11 existing plan documents

### External
- [Typer CLI documentation](https://typer.tiangolo.com/)
- [Rich terminal formatting](https://rich.readthedocs.io/)
- [Loguru logging](https://loguru.readthedocs.io/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [python-pptx documentation](https://python-pptx.readthedocs.io/)
- [pandas 3.0 migration guide](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)

### Architecture Decisions
- **Typer over Click**: Type-hint-driven, auto-completion, Rich integration built in
- **Loguru over stdlib logging**: Single import, structured JSON, rotation built in
- **JSON for config**: Team already knows JSON; both app config (`ars_config.json`) and client data (`clients_config.json`) stay JSON
- **Decorator registry over stevedore**: Lightweight, fits team size, no external deps
- **src/ layout over flat**: Ensures tests import installed package, catches packaging bugs

---

## Detailed Findings from Review Agents

> The following findings are organized by reviewer. Items already incorporated into the plan above are marked with [DONE]. Remaining items are for reference during implementation.

### Security Sentinel

| Finding | Severity | Status |
|---------|----------|--------|
| Git history contains production client data | CRITICAL | [DONE] Phase 0 — fresh repo, no data files |
| `diagnose=True` leaks local variables | HIGH | [DONE] Phase 1 — gated behind `--debug` |
| No authentication on Streamlit UI | MEDIUM | [DONE] Phase 4 — basic auth note |
| `.gitignore` gaps (missing `*.csv`, `*.zip`) | MEDIUM | [DONE] Phase 0 — expanded |
| File-based run tracker race conditions | LOW | Deferred — SQLite migration in Future Considerations |
| Path traversal via user-supplied file paths | LOW | Validate in `steps/load.py` — ensure paths are within `ars_base` |

### Performance Oracle

| Finding | Impact | Status |
|---------|--------|--------|
| Enable pandas Copy-on-Write | HIGH (55+ copies eliminated) | [DONE] Phase 3 |
| Remove 14 redundant `pd.to_datetime()` calls | MEDIUM | [DONE] Phase 3 |
| Eliminate dual Excel write pattern | MEDIUM | [DONE] Phase 3 |
| `plt.style.use()` → `plt.style.context()` | MEDIUM (global state bug) | [DONE] Phase 1 |
| `ProcessPoolExecutor` for batch mode | HIGH (4x speedup) | Deferred — add after single-client pipeline is stable |
| Remove 55+ excessive `.copy()` calls | MEDIUM | [DONE] Phase 3 (CoW makes them no-ops) |

### Code Simplicity Reviewer

| Finding | Status |
|---------|--------|
| Consolidate 7 phases → 5 | [DONE] |
| Drop `pkgutil.walk_packages` auto-discovery | [DONE] Phase 2 — explicit `MODULE_ORDER` list |
| Drop `PipelineStep.max_retries` | [DONE] Phase 3 — simplified to tuple |
| Flatten exception hierarchy (8 → 4 classes) | [DONE] Phase 1 |
| `required_columns`/`required_ctx_keys` as class tuple attributes | [DONE] Phase 2 |
| Drop CLI wizard if CSMs use Streamlit | [DONE] Cut — CSMs use Streamlit, wizard removed |
| Scheduling system is premature (zero specification) | Deferred to Phase 4 — build after core pipeline + VP feedback |

### Agent-Native Reviewer

| Finding | Status |
|---------|--------|
| `--json` global flag on all commands | [DONE] Phase 3 CLI |
| `ars config show` subcommand | Deferred to Phase 4 |
| `ars scan` subcommand | [DONE] Phase 3 CLI |
| `ars history` subcommand | Deferred to Phase 4 |
| JSONL log sink | Cut — trivial to add later with single `logger.add()` |
| Wizard blocks agent execution (non-TTY detection) | N/A — wizard removed |

### Pattern Recognition Specialist

| Finding | Status |
|---------|--------|
| Non-deterministic ordering in plugin registry | [DONE] Phase 2 — explicit `MODULE_ORDER` |
| `AnalysisResult` schema conflict (dataclass vs Pydantic in txn_analysis) | [DONE] Phase 3 note — keep separate until integration |
| Two logging frameworks in one repo (stdlib + Loguru) | Phase 3 — consolidate to Loguru only |
| Naming inconsistencies (`client_id` vs `clientid` vs `cid`) | Phase 3 — standardize to `client_id` everywhere |

### Architecture Strategist

| Finding | Status |
|---------|--------|
| Define `PipelineContext` dataclass before Phase 3 | [DONE] Phase 2 |
| Move test fixtures to Phase 0 | [DONE] Phase 0 |
| Use explicit ordering, not discovery order | [DONE] Phase 2 |
| Reconcile two registry patterns (txn_analysis vs new ars) | txn_analysis migrates as-is under `src/ars/txn_analysis/`; keeps its own Pydantic AnalysisResult + ANALYSIS_REGISTRY. Unified later if needed. |
| Extract schedule state from ars_config.json | Kept in JSON — simple enough for v2 scope |

---

## Open Questions

> These must be resolved before Phase 3 begins.

1. ~~**Should the repo be renamed from `ars_analysis-jupyter` to `ars-pipeline`?**~~ **RESOLVED:** Create a **new repo** `ars-pipeline`. Old repos stay as-is for reference. Code is brought in from all 3 repos.

2. ~~**Should `clients_config.json` migrate to TOML or remain JSON?**~~ **RESOLVED:** JSON for everything. `ars_config.json` for app settings, `clients_config.json` for client data. Team already knows JSON.

3. ~~**What is the `MAX_PER_CSM = 1` constant in `format_odd.py`?**~~ **RESOLVED:** Remove entirely. CSMs choose which clients to process (one, some, or all). No artificial limit.

4. ~~**Batch file setup?**~~ **RESOLVED:** CSMs use Streamlit. Not needed.
