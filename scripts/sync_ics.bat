@echo off
setlocal enabledelayedexpansion
REM sync_ics.bat - Sync ICS toolkit from standalone repo into monorepo
REM
REM Usage:
REM   scripts\sync_ics.bat          Sync from GitHub remote
REM   scripts\sync_ics.bat --dry    Show what would change without writing
REM
REM Prerequisites:
REM   git remote add ics-upstream https://github.com/JG-CSI-Velocity/ics_toolkit.git

set "REMOTE=ics-upstream"
set "BRANCH=main"
set "SRC_PKG=packages\ics_toolkit\src\ics_toolkit"
set "TEST_DIR=tests\ics"

REM Navigate to repo root (one level up from scripts/)
pushd "%~dp0\.."

REM Check remote exists
git remote | findstr /x "%REMOTE%" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Remote '%REMOTE%' not found.
    echo Run: git remote add %REMOTE% https://github.com/JG-CSI-Velocity/ics_toolkit.git
    popd
    exit /b 1
)

set "DRY_RUN=0"
if "%~1"=="--dry" set "DRY_RUN=1"

if %DRY_RUN%==1 (
    echo === DRY RUN (no files will be modified) ===
    echo.
)

echo Fetching latest from %REMOTE%/%BRANCH%...
git fetch %REMOTE% %BRANCH% --quiet

for /f %%i in ('git rev-parse %REMOTE%/%BRANCH%') do set "UPSTREAM_SHA=%%i"
echo Upstream commit: %UPSTREAM_SHA:~0,10%
echo.

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

REM --- Backup monorepo-only files ---
echo Backing up monorepo-only files...
if exist "%SRC_PKG%\runner.py" copy /y "%SRC_PKG%\runner.py" "%TEMP%\ics_runner_backup.py" >nul
if exist "%TEST_DIR%\test_runner.py" copy /y "%TEST_DIR%\test_runner.py" "%TEMP%\ics_test_runner_backup.py" >nul

REM --- Sync source ---
echo [1/3] Syncing source: ics_toolkit/ -^> %SRC_PKG%\
git archive %REMOTE%/%BRANCH% -- ics_toolkit/ | tar -x --strip-components=1 -C "%SRC_PKG%/"
echo   Done.
echo.

REM --- Sync tests ---
echo [2/3] Syncing tests: tests/ -^> %TEST_DIR%\
git archive %REMOTE%/%BRANCH% -- tests/ | tar -x --strip-components=1 -C "%TEST_DIR%/"
echo   Done.
echo.

REM --- Sync templates ---
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
echo   Review changes:
echo     git diff --stat
echo     git diff %SRC_PKG%/
echo.
echo   If everything looks good:
echo     git add %SRC_PKG%/ %TEST_DIR%/
echo     git commit -m "chore(ics): sync from ics_toolkit upstream %UPSTREAM_SHA:~0,10%"
echo ==========================================

popd
endlocal
