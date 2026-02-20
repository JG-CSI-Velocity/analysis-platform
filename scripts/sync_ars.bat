@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM sync_ars.bat -- Sync ARS Pipeline from standalone repo into the monorepo
REM ============================================================================
REM
REM WHAT THIS DOES
REM --------------
REM Pulls the latest ARS pipeline code from the standalone GitHub repo
REM (JG-CSI-Velocity/ars-pipeline) and copies it into the right spots
REM in the analysis-platform monorepo. Use this after you've been working
REM in the standalone ars-pipeline repo and want to bring those changes
REM into the monorepo.
REM
REM IMPORTANT: The standalone package is named "ars" but the monorepo
REM package is named "ars_analysis". This script automatically renames
REM all imports after extraction:
REM   from ars.analytics.dctr  ->  from ars_analysis.analytics.dctr
REM   import ars.config        ->  import ars_analysis.config
REM
REM HOW IT WORKS
REM ------------
REM 1. Fetches latest code from the "ars-upstream" git remote
REM 2. Extracts source files:  src\ars\  ->  packages\ars_analysis\src\ars_analysis\
REM    - Skips: ics\, txn_analysis\, analytics\ics\, analytics\transaction\,
REM      ui\, scheduling\, __main__.py  (these are separate monorepo packages)
REM 3. Renames imports: "from ars." -> "from ars_analysis." in all .py files
REM 4. Extracts test files:  tests\  ->  tests\ars\
REM    - Skips: test_ics_runner.py, test_transaction_runner.py
REM 5. Renames imports in test files too
REM 6. Preserves monorepo-only files (runner.py) by backing up and restoring
REM
REM FIRST-TIME SETUP (run once in the analysis-platform directory)
REM ---------------------------------------------------------------
REM   git remote add ars-upstream https://github.com/JG-CSI-Velocity/ars-pipeline.git
REM
REM USAGE
REM -----
REM   scripts\sync_ars.bat          Sync latest code (modifies files)
REM   scripts\sync_ars.bat --dry    Preview what would change (no modifications)
REM
REM AFTER RUNNING
REM -------------
REM   1. Review changes:     git diff --stat
REM   2. Run tests:          uv run pytest tests/ars/ -q
REM   3. Fix lint:           uv run ruff check packages/ars_analysis/ tests/ars/ --fix
REM   4. Verify imports:     Search for "from ars." in packages\ars_analysis\src\ and tests\ars\
REM      (should find ZERO matches -- everything should say "from ars_analysis.")
REM   5. Stage and commit:   git add packages\ars_analysis\src\ars_analysis\ tests\ars\
REM                           git commit -m "chore(ars): sync from upstream"
REM
REM FILES PRESERVED (not overwritten by sync)
REM -----------------------------------------
REM   packages\ars_analysis\src\ars_analysis\runner.py   -- bridge to shared context
REM   packages\ars_analysis\pyproject.toml               -- monorepo package config
REM
REM DIRECTORIES EXCLUDED (separate monorepo packages)
REM --------------------------------------------------
REM   src\ars\ics\                  -- ics_toolkit package
REM   src\ars\txn_analysis\         -- txn_analysis package
REM   src\ars\analytics\ics\        -- ICS wrapper (removed in monorepo)
REM   src\ars\analytics\transaction\ -- TXN wrapper (removed in monorepo)
REM   src\ars\ui\                   -- platform_app package
REM   src\ars\scheduling\           -- not used
REM   src\ars\__main__.py           -- monorepo uses different entry point
REM
REM ============================================================================

set "REMOTE=ars-upstream"
set "BRANCH=main"
set "SRC_PKG=packages\ars_analysis\src\ars_analysis"
set "TEST_DIR=tests\ars"

REM Navigate to repo root (one level up from scripts\)
pushd "%~dp0\.."

REM --- Check remote exists ---
git remote | findstr /x "%REMOTE%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Remote '%REMOTE%' not found.
    echo.
    echo First-time setup -- run this once:
    echo   git remote add %REMOTE% https://github.com/JG-CSI-Velocity/ars-pipeline.git
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

REM --- DRY RUN: just list and exit ---
if %DRY_RUN%==1 (
    echo [1/4] Source files that would be synced ^(excluding ics, txn, ui^):
    git archive %REMOTE%/%BRANCH% -- src/ars/ | tar -t 2>nul
    echo.
    echo [2/4] Import rename: "from ars." -^> "from ars_analysis."
    echo.
    echo [3/4] Test files that would be synced:
    git archive %REMOTE%/%BRANCH% -- tests/ | tar -t 2>nul
    echo.
    echo [4/4] Template files that would be synced:
    echo   Template12.25.pptx
    echo.
    echo ==========================================
    echo   DRY RUN complete. No files were changed.
    echo ==========================================
    popd
    exit /b 0
)

REM --- Backup monorepo-only files ---
echo Backing up monorepo-only files...
if exist "%SRC_PKG%\runner.py" copy /y "%SRC_PKG%\runner.py" "%TEMP%\ars_runner_backup.py" >nul

REM --- Step 1: Extract source into temp, filter, then copy ---
echo [1/4] Syncing source: src\ars\ -^> %SRC_PKG%\
echo        ^(excluding ics\, txn_analysis\, ui\, scheduling\^)

set "TMPDIR=%TEMP%\ars_sync_%RANDOM%"
mkdir "%TMPDIR%"
git archive %REMOTE%/%BRANCH% -- src/ars/ | tar -x --strip-components=2 -C "%TMPDIR%/"

REM Remove excluded directories
if exist "%TMPDIR%\ics" rmdir /s /q "%TMPDIR%\ics"
if exist "%TMPDIR%\txn_analysis" rmdir /s /q "%TMPDIR%\txn_analysis"
if exist "%TMPDIR%\analytics\ics" rmdir /s /q "%TMPDIR%\analytics\ics"
if exist "%TMPDIR%\analytics\transaction" rmdir /s /q "%TMPDIR%\analytics\transaction"
if exist "%TMPDIR%\ui" rmdir /s /q "%TMPDIR%\ui"
if exist "%TMPDIR%\scheduling" rmdir /s /q "%TMPDIR%\scheduling"
if exist "%TMPDIR%\__main__.py" del "%TMPDIR%\__main__.py"

REM Copy filtered files into monorepo
xcopy /s /y /q "%TMPDIR%\*" "%SRC_PKG%\" >nul
rmdir /s /q "%TMPDIR%"
echo   Done.
echo.

REM --- Step 2: Rename imports ---
echo [2/4] Renaming imports: "from ars." -^> "from ars_analysis."

REM Use PowerShell for the sed-like replacement (works on Windows)
powershell -NoProfile -Command ^
    "Get-ChildItem -Path '%SRC_PKG%' -Filter '*.py' -Recurse | ForEach-Object { ^
        $content = Get-Content $_.FullName -Raw; ^
        if ($content -match 'from ars\.' -or $content -match 'import ars\.') { ^
            $content = $content -replace 'from ars\.', 'from ars_analysis.'; ^
            $content = $content -replace 'from ars import', 'from ars_analysis import'; ^
            $content = $content -replace 'import ars\.', 'import ars_analysis.'; ^
            $content = $content -replace 'import ars$', 'import ars_analysis'; ^
            Set-Content $_.FullName $content -NoNewline; ^
        } ^
    }"
echo   Done.
echo.

REM --- Restore monorepo-only files ---
if exist "%TEMP%\ars_runner_backup.py" (
    copy /y "%TEMP%\ars_runner_backup.py" "%SRC_PKG%\runner.py" >nul
    del "%TEMP%\ars_runner_backup.py"
)

REM --- Step 3: Sync tests ---
echo [3/4] Syncing tests: tests\ -^> %TEST_DIR%\
echo        ^(excluding test_ics_runner.py, test_transaction_runner.py^)

set "TMPDIR_T=%TEMP%\ars_test_sync_%RANDOM%"
mkdir "%TMPDIR_T%"
git archive %REMOTE%/%BRANCH% -- tests/ | tar -x --strip-components=1 -C "%TMPDIR_T%/"

REM Remove excluded test files
if exist "%TMPDIR_T%\test_analytics\test_ics_runner.py" del "%TMPDIR_T%\test_analytics\test_ics_runner.py"
if exist "%TMPDIR_T%\test_analytics\test_transaction_runner.py" del "%TMPDIR_T%\test_analytics\test_transaction_runner.py"

REM Copy filtered tests
xcopy /s /y /q "%TMPDIR_T%\*" "%TEST_DIR%\" >nul
rmdir /s /q "%TMPDIR_T%"

REM Rename imports in test files
powershell -NoProfile -Command ^
    "Get-ChildItem -Path '%TEST_DIR%' -Filter '*.py' -Recurse | ForEach-Object { ^
        $content = Get-Content $_.FullName -Raw; ^
        if ($content -match 'from ars\.' -or $content -match 'import ars\.') { ^
            $content = $content -replace 'from ars\.', 'from ars_analysis.'; ^
            $content = $content -replace 'from ars import', 'from ars_analysis import'; ^
            $content = $content -replace 'import ars\.', 'import ars_analysis.'; ^
            $content = $content -replace 'import ars$', 'import ars_analysis'; ^
            Set-Content $_.FullName $content -NoNewline; ^
        } ^
    }"
echo   Done.
echo.

REM --- Step 4: Sync template ---
echo [4/4] Syncing template...
if not exist "%SRC_PKG%\output\template" mkdir "%SRC_PKG%\output\template"
git archive %REMOTE%/%BRANCH% -- src/ars/output/template/ | tar -x --strip-components=4 -C "%SRC_PKG%/output/template/" 2>nul
echo   Done.
echo.

echo ==========================================
echo   Sync complete from %REMOTE%/%BRANCH%
echo.
echo   Next steps:
echo     1. Review:  git diff --stat
echo     2. Test:    uv run pytest tests/ars/ -q
echo     3. Lint:    uv run ruff check packages/ars_analysis/ tests/ars/ --fix
echo     4. Verify:  Search for "from ars." in source and tests
echo        ^(should find ZERO -- all should say "from ars_analysis."^)
echo     5. Commit:  git add %SRC_PKG%\ %TEST_DIR%\
echo                 git commit -m "chore(ars): sync from upstream %UPSTREAM_SHA:~0,10%"
echo ==========================================

popd
endlocal
