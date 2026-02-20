@echo off
setlocal
echo ==========================================
echo  Analysis Platform -- Headless Batch
echo ==========================================
echo.

set "REAL_DIR=%~dp0"
if "%REAL_DIR:~-1%"=="\" set "REAL_DIR=%REAL_DIR:~0,-1%"

where uv >nul 2>&1
if errorlevel 1 (
    echo ERROR: uv not found. Install it from https://docs.astral.sh/uv/
    pause
    exit /b 1
)

uv sync --all-packages >nul 2>&1

set MONTH=%1
if "%MONTH%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy.MM"') do set MONTH=%%i
)

echo Review month: %MONTH%
echo.

echo [1/3] Retrieving ODD files...
uv run python -m ars_analysis retrieve --month %MONTH%
echo.

echo [2/3] Formatting ODD files...
uv run python -m ars_analysis format --month %MONTH%
echo.

echo [3/3] Running batch analysis...
uv run python -m ars_analysis batch --month %MONTH%
echo.

echo Done!
pause

endlocal
