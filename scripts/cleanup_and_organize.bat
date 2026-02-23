@echo off
REM ============================================================
REM  ARS Cleanup & Organize Script
REM  Moves stale folders to M:\ARS\_archive\ before deleting
REM  Run from any directory on your work machine
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo  ====================================
echo   ARS Directory Cleanup + Organize
echo  ====================================
echo.
echo  This script will:
echo    1. Archive stale folders from M:\ARS
echo    2. Archive stale folders from your user profile
echo    3. Clean __pycache__ from the repo
echo    4. Verify the final directory structure
echo.
echo  Nothing is permanently deleted -- everything moves to:
echo    M:\ARS\_archive\
echo.
pause

REM -----------------------------------------------------------
REM  Step 1: Create archive folder
REM -----------------------------------------------------------
echo.
echo [Step 1] Creating archive folder...
if not exist "M:\ARS\_archive" mkdir "M:\ARS\_archive"
echo   Created M:\ARS\_archive\

REM -----------------------------------------------------------
REM  Step 2: Archive stale M:\ARS folders
REM -----------------------------------------------------------
echo.
echo [Step 2] Archiving stale M:\ARS folders...

REM -- ars-pipeline (old V1 repo, superseded by analysis-platform)
if exist "M:\ARS\ars-pipeline" (
    echo   Moving M:\ARS\ars-pipeline  --^>  M:\ARS\_archive\ars-pipeline
    move "M:\ARS\ars-pipeline" "M:\ARS\_archive\ars-pipeline"
) else (
    echo   [skip] M:\ARS\ars-pipeline not found
)

REM -- v1 (even older version, everything ported)
if exist "M:\ARS\v1" (
    echo   Moving M:\ARS\v1  --^>  M:\ARS\_archive\v1
    move "M:\ARS\v1" "M:\ARS\_archive\v1"
) else (
    echo   [skip] M:\ARS\v1 not found
)

REM -- Scripts (empty, nothing uses it)
if exist "M:\ARS\Scripts" (
    echo   Moving M:\ARS\Scripts  --^>  M:\ARS\_archive\Scripts
    move "M:\ARS\Scripts" "M:\ARS\_archive\Scripts"
) else (
    echo   [skip] M:\ARS\Scripts not found
)

REM -- run_tracker.py (tracker logic is in the platform now)
if exist "M:\ARS\Config\run_tracker.py" (
    echo   Moving M:\ARS\Config\run_tracker.py  --^>  M:\ARS\_archive\run_tracker.py
    move "M:\ARS\Config\run_tracker.py" "M:\ARS\_archive\run_tracker.py"
) else (
    echo   [skip] M:\ARS\Config\run_tracker.py not found
)

REM -----------------------------------------------------------
REM  Step 3: Archive stale user profile folders
REM -----------------------------------------------------------
echo.
echo [Step 3] Archiving stale user profile folders...

REM -- charts/ (old chart output folder)
if exist "%USERPROFILE%\charts" (
    echo   Moving %USERPROFILE%\charts  --^>  M:\ARS\_archive\user_charts
    move "%USERPROFILE%\charts" "M:\ARS\_archive\user_charts"
) else (
    echo   [skip] %USERPROFILE%\charts not found
)

REM -- .streamlit/ at user root (old standalone config)
if exist "%USERPROFILE%\.streamlit" (
    echo   Moving %USERPROFILE%\.streamlit  --^>  M:\ARS\_archive\user_streamlit
    move "%USERPROFILE%\.streamlit" "M:\ARS\_archive\user_streamlit"
) else (
    echo   [skip] %USERPROFILE%\.streamlit not found
)

REM -----------------------------------------------------------
REM  Step 4: Clean __pycache__ from the repo
REM -----------------------------------------------------------
echo.
echo [Step 4] Cleaning __pycache__ from analysis-platform...

set "REPO=%USERPROFILE%\analysis-platform"
if exist "%REPO%" (
    for /d /r "%REPO%" %%d in (__pycache__) do (
        if exist "%%d" (
            echo   Removing %%d
            rd /s /q "%%d"
        )
    )
    echo   Done.
) else (
    echo   [skip] %REPO% not found
)

REM -----------------------------------------------------------
REM  Step 5: Clean .pytest_cache from the repo
REM -----------------------------------------------------------
echo.
echo [Step 5] Cleaning .pytest_cache from analysis-platform...

if exist "%REPO%" (
    for /d /r "%REPO%" %%d in (.pytest_cache) do (
        if exist "%%d" (
            echo   Removing %%d
            rd /s /q "%%d"
        )
    )
    echo   Done.
) else (
    echo   [skip] %REPO% not found
)

REM -----------------------------------------------------------
REM  Step 6: Verify final structure
REM -----------------------------------------------------------
echo.
echo [Step 6] Verifying final directory structure...
echo.
echo  === M:\ARS (should only have active folders) ===
dir "M:\ARS" /b /ad
echo.
echo  === M:\ARS\_archive (stale items moved here) ===
if exist "M:\ARS\_archive" (
    dir "M:\ARS\_archive" /b
) else (
    echo   (empty)
)
echo.
echo  === %USERPROFILE%\analysis-platform\packages ===
dir "%REPO%\packages" /b /ad 2>nul
echo.
echo  === M:\ARS\Config ===
dir "M:\ARS\Config" /b 2>nul

echo.
echo  ====================================
echo   Cleanup complete!
echo  ====================================
echo.
echo  Active structure:
echo    M:\ARS\Config\              clients_config.json
echo    M:\ARS\Presentations\       Template12.25.pptx
echo    M:\ARS\Incoming\            ODDD Files, Transaction Files, CSM-Data
echo    M:\ARS\Ready for Analysis\  Formatted files by CSM
echo    M:\ARS\Analysis Outputs\    Results
echo    M:\ARS\Logs\                Pipeline logs
echo    M:\ARS\Output\              Deck output
echo.
echo    %REPO%\                     The repo (all code)
echo.
echo  Archived to M:\ARS\_archive\:
echo    ars-pipeline\               Old V1 package
echo    v1\                         Original version
echo    Scripts\                    Empty folder
echo    run_tracker.py              Old tracker script
echo    user_charts\                Old chart output
echo    user_streamlit\             Old streamlit config
echo.
echo  Once validated, you can delete M:\ARS\_archive\ entirely.
echo.
pause
