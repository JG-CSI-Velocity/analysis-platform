# Deployment Checklist: RPE Rebrand

## Deployment Context

- **Scope**: Rebrand from "UAP" / "Unified Analysis Platform" to "RPE Analysis Platform" by "CSI | Velocity"
- **Environment**: Windows M: drive shared deployment (manual git pull, no CI/CD)
- **Users**: ~10 CSM users launching via .bat files
- **Current State**: 2,536 tests, 94% coverage
- **Impact Level**: LOW RISK (cosmetic rebrand, no logic changes)
- **Rollback Window**: Unlimited (no data changes, reversible via git revert)

## Invariants

State the specific invariants that must remain true before and after deployment:

```
- [ ] All 4 .bat files launch without errors
- [ ] Streamlit UI loads at http://localhost:8501
- [ ] Browser tab title displays the product name
- [ ] Port-kill mechanism (line 62 in run.bat, line 13 in dashboard.bat) functions correctly
- [ ] CLI commands (python -m ars_analysis, txn_analysis, ics_toolkit, platform_app) execute
- [ ] Test suite passes: 2,536 tests, 94% coverage maintained
- [ ] No ruff lint errors
- [ ] No functional regressions in analysis pipelines
```

---

## Pre-Deploy Checklist (DEV MACHINE)

### 1. Pre-Deploy Audits (Read-Only)

Run these commands BEFORE deploying to M: drive:

```bash
# Baseline: Verify all tests pass
uv run pytest tests/ -q
# Expected: 2,536 passed, ~2.5 minutes

# Baseline: Verify coverage threshold
uv run pytest tests/ --cov --cov-report=term-missing --cov-fail-under=80 -q
# Expected: 94% coverage (must be >= 80%)

# Baseline: Verify lint clean
uv run ruff check packages/
# Expected: All checks passed

# Baseline: Verify format clean
uv run ruff format --check packages/
# Expected: All files already formatted

# Baseline: Count CSS references (should be 0 after rebrand)
grep -r "uap-\|--uap-" packages/platform_app/ --include="*.py" | grep -v "uap_" | wc -l
# Expected before deploy: 224+ occurrences
# Expected after deploy: 0 occurrences (session state `uap_` keys intentionally preserved)

# Baseline: Verify .bat files reference old brand
grep -h "CSI Velocity Solutions\|Analysis Platform v2.0" *.bat
# Expected: 4 matches (run.bat, dashboard.bat, run_batch.bat, setup.bat)
```

**Expected Results:**
- All tests pass
- Coverage >= 80% (currently 94%)
- No ruff errors
- CSS prefix `uap-` present in 224+ locations (to be replaced)
- .bat files show old brand text

**Deviation from expected = STOP deployment**

---

### 2. Rebrand Verification (DEV MACHINE)

After completing the rebrand changes from `/plans/feat-rebrand-rpe-and-platform-improvements.md`, run:

```bash
# Verify CSS rename complete
grep -r "uap-\|--uap-" packages/platform_app/ --include="*.py" | grep -v "uap_"
# Expected: 0 results (only session state `uap_` should remain)

# Verify session state keys intentionally preserved
grep -r "uap_" packages/platform_app/ --include="*.py" | wc -l
# Expected: ~114 occurrences (21 distinct keys across 7 files - DO NOT CHANGE)

# Verify .bat file rebrand
grep -h "RPE Analysis Platform\|CSI | Velocity" *.bat
# Expected: 4 matches minimum (run.bat, dashboard.bat, run_batch.bat, setup.bat)

# Verify browser title
grep "page_title=" packages/platform_app/src/platform_app/app.py
# Expected: page_title="RPE" or page_title=BRAND.short

# Verify pyproject.toml description
grep "description.*RPE" pyproject.toml
# Expected: description = "RPE Analysis Platform: ARS, Transaction, and ICS pipelines."

# Verify CLI help text
grep "RPE Analysis Platform" packages/platform_app/src/platform_app/cli.py
# Expected: Match in help text

# Run full test suite
uv run pytest tests/ -q
# Expected: 2,536 passed (same count as baseline)

# Verify no new lint errors
uv run ruff check packages/
# Expected: All checks passed
```

**Pre-Deploy Gate:**
- [ ] All CSS `uap-` prefixes renamed to `rpe-`
- [ ] Session state `uap_` keys intentionally preserved (documented in brand.py)
- [ ] All 4 .bat files show "RPE Analysis Platform" and "CSI | Velocity"
- [ ] Browser title shows "RPE"
- [ ] All tests pass (2,536)
- [ ] Coverage >= 94%
- [ ] Ruff clean

---

### 3. Manual UI Verification (DEV MACHINE)

Launch the dashboard locally and verify user-facing strings:

```bash
uv run streamlit run packages/platform_app/src/platform_app/app.py
```

**Visual Checklist (browser at http://localhost:8501):**
- [ ] Browser tab title shows "RPE" (not "UAP")
- [ ] Sidebar footer (bottom of left sidebar) shows "RPE v2.0 // ANALYSIS PLATFORM"
- [ ] Home page header shows "RPE ANALYSIS PLATFORM" (large centered text)
- [ ] No visible references to "UAP" or "Unified Analysis Platform" anywhere in the UI
- [ ] CSS styling looks identical to pre-rebrand (colors, fonts, spacing unchanged)
- [ ] All 8 pages load without errors: Home, Workspace, Data Ingestion, Run Analysis, Batch Workflow, Outputs, Run History, Module Library

**Port-Kill Mechanism Test:**
1. Launch dashboard via `dashboard.bat`
2. Note the process ID: `Get-Process | Where-Object {$_.ProcessName -like "*streamlit*"}`
3. Close the dashboard window
4. Launch dashboard again via `dashboard.bat`
5. [ ] Dashboard launches on port 8501 without "port already in use" error
6. [ ] No manual `taskkill` required

---

### 4. CLI Verification (DEV MACHINE)

Verify CLI help text shows the rebrand:

```bash
uv run python -m platform_app --help
# Expected: "RPE Analysis Platform: ARS, Transaction, and ICS pipelines."

uv run python -m ars_analysis --help
# Expected: Help text loads (no crashes)

uv run python -m txn_analysis --help
# Expected: Help text loads

uv run python -m ics_toolkit --help
# Expected: Help text loads
```

---

## Deploy Steps (M: DRIVE)

**Important:** Deploy during off-peak hours (early morning or late afternoon) to minimize CSM disruption.

### Step 1: Announce Deployment
- [ ] Send Slack/email to CSMs: "Deploying visual rebrand to RPE Analysis Platform in 5 minutes. Close any open dashboards. Will take 2 minutes."

### Step 2: Backup Current State
- [ ] On M: drive, create backup: `xcopy M:\analysis-platform M:\analysis-platform-backup-YYYYMMDD /E /I /H /Y`
- [ ] Or note the current commit SHA: `git rev-parse HEAD`
- [ ] Save this SHA in a safe place for rollback

### Step 3: Deploy via Git Pull

On the M: drive machine:

```cmd
cd M:\analysis-platform
git fetch origin
git status
REM Expected: "Your branch is behind 'origin/main' by X commits"

git pull origin main
REM Expected: "Updating <old-sha>..<new-sha>"

REM Verify the pull succeeded
git log -1 --oneline
REM Expected: Shows the rebrand commit message
```

### Step 4: Verify Deployment Files Changed

```cmd
REM Verify .bat files updated
findstr /C:"RPE Analysis Platform" run.bat dashboard.bat run_batch.bat setup.bat
REM Expected: 4 matches minimum

REM Verify pyproject.toml updated
findstr /C:"RPE" pyproject.toml
REM Expected: description line matches
```

---

## Post-Deploy Verification (M: DRIVE) - WITHIN 5 MINUTES

### 1. Smoke Test: Launch Dashboard

```cmd
REM From M:\analysis-platform directory
dashboard.bat
```

**Expected Behavior:**
- [ ] Port-kill mechanism runs (PowerShell command at top of dashboard.bat)
- [ ] "Using local .venv environment..." or uv sync message displays
- [ ] "Opening browser at http://localhost:8501" displays
- [ ] Browser opens to Streamlit dashboard within 10 seconds
- [ ] Browser tab title shows "RPE"
- [ ] Sidebar footer shows "RPE v2.0 // ANALYSIS PLATFORM"
- [ ] Home page header shows "RPE ANALYSIS PLATFORM"
- [ ] No error messages in console or browser

**If any of the above fail, proceed to rollback.**

---

### 2. Smoke Test: CLI Commands

```cmd
REM Test ARS CLI
python -m ars_analysis --help
REM Expected: Help text displays, mentions "account review"

REM Test TXN CLI
python -m txn_analysis --help
REM Expected: Help text displays, mentions "transaction"

REM Test ICS CLI
python -m ics_toolkit --help
REM Expected: Help text displays, mentions "ICS"

REM Test Platform CLI
python -m platform_app --help
REM Expected: "RPE Analysis Platform: ARS, Transaction, and ICS pipelines."
```

---

### 3. Smoke Test: Run Batch Script

**IMPORTANT**: Only run this if you have a safe test ODD file on the M: drive. Do NOT run against production client data until Post-Deploy +1 Hour verification.

```cmd
REM Test with a known-good test file
run_batch.bat 2026.02
```

**Expected Behavior:**
- [ ] Banner displays "RPE Analysis Platform -- Headless Batch"
- [ ] Script runs [1/3] Retrieve, [2/3] Format, [3/3] Batch without errors
- [ ] Output files created in expected directories
- [ ] "Done!" displays at end
- [ ] No Python stack traces

---

### 4. User Acceptance Test (First CSM)

- [ ] Ask ONE CSM volunteer to launch `dashboard.bat` from their machine
- [ ] CSM confirms:
  - Dashboard launches without errors
  - Browser tab title shows "RPE"
  - UI looks identical to before (only text changed, not colors/layout)
  - Can navigate to Workspace page
  - Can click "Run Analysis" (don't actually run)
  - No visible errors or broken styles

**If CSM reports issues, proceed to rollback.**

---

## Post-Deploy Monitoring (First 24 Hours)

### +1 Hour: Real Client Data Test

Have a CSM run a real analysis on a known-good client:

```cmd
REM Launch dashboard
dashboard.bat

REM In UI:
1. Navigate to Workspace page
2. Select a test client (e.g., 1200 Test CU)
3. Click "Run Analysis"
4. Wait for completion (2-5 minutes)
5. Navigate to Outputs page
6. Verify PPTX and XLSX files generated
7. Open PPTX in PowerPoint
8. Open XLSX in Excel
9. Verify no corrupted data or formatting issues
```

**Expected:**
- [ ] Analysis completes without errors
- [ ] PPTX and XLSX files generated
- [ ] Files open correctly in Office
- [ ] Slide content looks identical to pre-rebrand
- [ ] Excel tabs have data
- [ ] No "UAP" references in output files

---

### +4 Hours: Check for User Reports

- [ ] Check Slack/email for CSM bug reports
- [ ] If no issues reported, deployment is successful

---

### +24 Hours: Full Validation

- [ ] Confirm at least 3 CSMs have used the platform successfully
- [ ] Confirm no error reports in Slack/email
- [ ] Confirm no rollbacks were needed
- [ ] Close deployment ticket

---

## Rollback Plan

**Can we roll back?**
- [x] **YES** - This is a cosmetic rebrand with no data changes. Rollback is instant and safe.

**Rollback is required if:**
- .bat files fail to launch
- Streamlit UI fails to load
- Port-kill mechanism breaks
- CSMs report visual corruption or missing text
- Any functional regression in analysis pipelines

### Rollback Steps (M: DRIVE)

**Estimated Time: 2 minutes**

```cmd
cd M:\analysis-platform

REM Option A: Revert to backup directory
xcopy M:\analysis-platform-backup-YYYYMMDD\* M:\analysis-platform\ /E /I /H /Y

REM Option B: Git revert to previous commit
git log --oneline -5
REM Identify the commit SHA BEFORE the rebrand (saved in Step 2 above)
git reset --hard <previous-sha>
REM Example: git reset --hard a1b2c3d4

REM Verify rollback
findstr /C:"Analysis Platform v2.0" run.bat
REM Expected: Old brand text ("CSI Velocity Solutions" instead of "CSI | Velocity")
```

### Post-Rollback Verification

```cmd
REM Test dashboard launch
dashboard.bat
REM Expected: Browser tab title shows "UAP" (old brand)

REM Test CLI
python -m platform_app --help
REM Expected: Old help text ("Unified banking analysis platform...")
```

### Announce Rollback
- [ ] Send Slack/email to CSMs: "Rebrand rolled back due to [reason]. Platform back to previous version. Please report any issues."

---

## Port-Kill Mechanism: Does Rebrand Affect It?

**Answer: NO**

The port-kill mechanism is in lines 62 (run.bat) and 13 (dashboard.bat):

```batch
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul
```

This PowerShell one-liner:
1. Finds any process listening on port 8501
2. Kills the process forcefully
3. Suppresses all error output

**The rebrand changes:**
- Banner text (lines 3-6 in run.bat)
- Echo statements
- NO changes to the PowerShell command itself

**Therefore:**
- Port-kill logic is unchanged
- Mechanism will function identically pre- and post-rebrand
- No additional testing required beyond the standard smoke test

---

## Deployment Success Criteria

Mark deployment as successful when:

- [x] All 4 .bat files launch without errors
- [x] Streamlit UI loads and displays "RPE" in browser tab
- [x] Sidebar footer shows "RPE v2.0 // ANALYSIS PLATFORM"
- [x] Home page header shows "RPE ANALYSIS PLATFORM"
- [x] No visible "UAP" references in UI
- [x] Port-kill mechanism works (dashboard.bat can be launched twice without error)
- [x] At least one real client analysis completes successfully post-deploy
- [x] No CSM bug reports within first 4 hours
- [x] At least 3 CSMs confirm platform works on their machines
- [x] Test suite passes on M: drive (if uv is available)

---

## Monitoring Dashboards

**For this deployment: None required**

Rationale:
- No backend changes (no database, no API, no external services)
- No performance-critical code changes
- No data processing logic changes
- Rebrand is purely cosmetic (UI strings, CSS class names, docstrings)

**Monitor via:**
- Slack channel for CSM reports
- Email for bug reports
- Direct check-ins with CSMs at +1h, +4h, +24h

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| .bat file syntax error | LOW | HIGH | Pre-deploy: Run all 4 .bat files on dev machine |
| CSS class mismatch | MEDIUM | MEDIUM | Pre-deploy: Visual check in Streamlit UI |
| Session state breakage | LOW | HIGH | Session state keys NOT renamed (documented) |
| Port-kill mechanism breaks | LOW | MEDIUM | No changes to PowerShell command |
| Browser caching shows old brand | LOW | LOW | Hard refresh (Ctrl+Shift+R) or clear cache |
| CSMs see broken styles | LOW | MEDIUM | CSS variables renamed consistently |
| Git pull fails on M: drive | LOW | MEDIUM | Use backup xcopy if git unavailable |

**Overall Risk Level: LOW**

This is a text-only rebrand with no logic changes, no data transformations, and no external dependencies. The worst-case scenario is broken UI text, which is immediately visible and reversible via git revert in 2 minutes.

---

## Lessons Learned (Post-Deployment)

After deployment completes, document:

- [ ] Actual deployment time (target: < 5 minutes)
- [ ] Any unexpected issues encountered
- [ ] CSM feedback on new branding
- [ ] Any edge cases discovered (e.g., cached browser tabs, .bat file permissions)
- [ ] Update this checklist with improvements for next deployment

---

## Sign-Off

**Deployed by:** _______________
**Date/Time:** _______________
**Verified by (CSM):** _______________
**Rollback required?** YES / NO
**Notes:** _______________
