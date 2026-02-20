@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM sync_ics.bat -- Sync ICS Toolkit from standalone repo into the monorepo
REM ============================================================================
REM
REM WHAT THIS DOES
REM --------------
REM Pulls the latest ICS toolkit code from the standalone GitHub repo
REM (JG-CSI-Velocity/ics_toolkit) and copies it into the right spots
REM in the analysis-platform monorepo. Use this after you've been working
REM in the standalone ics_toolkit repo (Jupyter, testing, etc.) and want
REM to bring those changes into the monorepo.
REM
REM HOW IT WORKS
REM ------------
REM 1. Fetches latest code from the "ics-upstream" git remote
REM 2. Extracts source files:  ics_toolkit\  ->  packages\ics_toolkit\src\ics_toolkit\
REM 3. Extracts test files:    tests\        ->  tests\ics\
REM 4. Extracts templates:     templates\    ->  packages\ics_toolkit\src\ics_toolkit\templates\
REM 5. Preserves monorepo-only files (runner.py, test_runner.py) by backing
REM    them up before sync and restoring after
REM
REM FIRST-TIME SETUP (run once in the analysis-platform directory)
REM ---------------------------------------------------------------
REM   git remote add ics-upstream https://github.com/JG-CSI-Velocity/ics_toolkit.git
REM
REM USAGE
REM -----
REM   scripts\sync_ics.bat          Sync latest code (modifies files)
REM   scripts\sync_ics.bat --dry    Preview what would change (no modifications)
REM
REM AFTER RUNNING
REM -------------
REM   1. Review changes:     git diff --stat
REM   2. Run tests:          uv run pytest tests/ics/ -q
REM   3. Fix lint:           uv run ruff check packages/ics_toolkit/ tests/ics/ --fix
REM   4. Check for stale imports -- the standalone repo uses "from tests.analysis..."
REM      but the monorepo needs "from tests.ics.analysis..." Search tests\ics\ for
REM      "from tests." and fix any that don't start with "from tests.ics."
REM   5. Stage and commit:   git add packages\ics_toolkit\src\ics_toolkit\ tests\ics\
REM                           git commit -m "chore(ics): sync from upstream"
REM
REM FILES PRESERVED (not overwritten by sync)
REM -----------------------------------------
REM   packages\ics_toolkit\src\ics_toolkit\runner.py   -- bridge to shared context
REM   packages\ics_toolkit\pyproject.toml              -- monorepo package config
REM   tests\ics\test_runner.py                         -- monorepo runner tests
REM
REM ============================================================================

set "REMOTE=ics-upstream"
set "BRANCH=main"
set "SRC_PKG=packages\ics_toolkit\src\ics_toolkit"
set "TEST_DIR=tests\ics"

REM Navigate to repo root (one level up from scripts\)
pushd "%~dp0\.."

REM --- Check remote exists ---
git remote | findstr /x "%REMOTE%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Remote '%REMOTE%' not found.
    echo.
    echo First-time setup -- run this once:
    echo   git remote add %REMOTE% https://github.com/JG-CSI-Velocity/ics_toolkit.git
    popd
    exit /b 1
)

set "DRY_RUN=0"
if "%~1"=="--dry" set "DRY_RUN=1"

if %DRY_RUN%==1 (
    echo === DRY RUN ^(no files will be modified^) ===
    echo.
)

echo Fetching latest from %REMOTE%/%BRANCH%...
git fetch %REMOTE% %BRANCH% --quiet

for /f %%i in ('git rev-parse %REMOTE%/%BRANCH%') do set "UPSTREAM_SHA=%%i"
echo Upstream commit: %UPSTREAM_SHA:~0,10%
echo.

REM --- DRY RUN: just list files and exit ---
if %DRY_RUN%==1 (
    echo [1/3] Source files that would be synced:
    git archive %REMOTE%/%BRANCH% -- ics_toolkit/ | tar -t 2>nul
    echo.
    echo [2/3] Test files that would be synced:
    git archive %REMOTE%/%BRANCH% -- tests/ | tar -t 2>nul
    echo.
    echo [3/3] Template files that would be synced:
    git archive %REMOTE%/%BRANCH% -- templates/ | tar -t 2>nul
    echo.
    echo ==========================================
    echo   DRY RUN complete. No files were changed.
    echo ==========================================
    popd
    exit /b 0
)

REM --- Backup monorepo-only files before sync ---
echo Backing up monorepo-only files...
if exist "%SRC_PKG%\runner.py" copy /y "%SRC_PKG%\runner.py" "%TEMP%\ics_runner_backup.py" >nul
if exist "%TEST_DIR%\test_runner.py" copy /y "%TEST_DIR%\test_runner.py" "%TEMP%\ics_test_runner_backup.py" >nul

REM --- Step 1: Sync source code ---
echo [1/3] Syncing source: ics_toolkit/ -^> %SRC_PKG%\
git archive %REMOTE%/%BRANCH% -- ics_toolkit/ | tar -x --strip-components=1 -C "%SRC_PKG%/"
echo   Done.
echo.

REM --- Step 2: Sync tests ---
echo [2/3] Syncing tests: tests/ -^> %TEST_DIR%\
git archive %REMOTE%/%BRANCH% -- tests/ | tar -x --strip-components=1 -C "%TEST_DIR%/"
echo   Done.
echo.

REM --- Step 3: Sync templates ---
echo [3/3] Syncing templates: templates/ -^> %SRC_PKG%\templates\
if not exist "%SRC_PKG%\templates" mkdir "%SRC_PKG%\templates"
git archive %REMOTE%/%BRANCH% -- templates/ | tar -x --strip-components=1 -C "%SRC_PKG%/templates/"
echo   Done.
echo.

REM --- Restore monorepo-only files ---
echo Restoring monorepo-only files...
if exist "%TEMP%\ics_runner_backup.py" (
    copy /y "%TEMP%\ics_runner_backup.py" "%SRC_PKG%\runner.py" >nul
    del "%TEMP%\ics_runner_backup.py"
)
if exist "%TEMP%\ics_test_runner_backup.py" (
    copy /y "%TEMP%\ics_test_runner_backup.py" "%TEST_DIR%\test_runner.py" >nul
    del "%TEMP%\ics_test_runner_backup.py"
)

echo.
echo ==========================================
echo   Sync complete from %REMOTE%/%BRANCH%
echo.
echo   Next steps:
echo     1. Review:  git diff --stat
echo     2. Test:    uv run pytest tests/ics/ -q
echo     3. Lint:    uv run ruff check packages/ics_toolkit/ tests/ics/ --fix
echo     4. Check:   Search tests\ics\ for "from tests." imports
echo        (fix any bare "from tests." to "from tests.ics.")
echo     5. Commit:  git add %SRC_PKG%\ %TEST_DIR%\
echo                 git commit -m "chore(ics): sync from upstream %UPSTREAM_SHA:~0,10%"
echo ==========================================

popd
endlocal
