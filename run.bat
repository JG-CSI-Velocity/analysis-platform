@echo off
setlocal
echo ==========================================
echo  Analysis Platform v2.0
echo  CSI Velocity Solutions
echo ==========================================
echo.

set "REAL_DIR=%~dp0"
if "%REAL_DIR:~-1%"=="\" set "REAL_DIR=%REAL_DIR:~0,-1%"

REM Check for uv
where uv >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv not found. Install it from https://docs.astral.sh/uv/
    pause
    exit /b 1
)

REM Sync packages
echo Syncing packages...
uv sync --all-packages >nul 2>&1
if errorlevel 1 (
    echo ERROR: Package sync failed.
    pause
    exit /b 1
)

REM Accept optional arguments: run.bat [MONTH]
set MONTH=%1
if "%MONTH%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy.MM"') do set MONTH=%%i
)

echo Review month: %MONTH%
echo.

echo [1/3] Retrieving and formatting ODD files...
uv run python -m ars_analysis retrieve --month %MONTH%
uv run python -m ars_analysis format --month %MONTH%
echo.

echo [2/3] Running batch analysis...
uv run python -m ars_analysis batch --month %MONTH%
echo.

echo [3/3] Launching Streamlit dashboard...
echo   Close this window or press Ctrl+C to stop.
echo.
uv run streamlit run "%REAL_DIR%\packages\platform_app\src\platform_app\app.py" --server.port 8501

endlocal
