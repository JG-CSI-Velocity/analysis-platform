@echo off
setlocal
echo ==========================================
echo  Analysis Platform -- Headless Batch
echo ==========================================
echo.

set "REAL_DIR=%~dp0"
if "%REAL_DIR:~-1%"=="\" set "REAL_DIR=%REAL_DIR:~0,-1%"

REM Resolve month
set MONTH=%1
if "%MONTH%"=="" (
    for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy.MM"') do set MONTH=%%i
)
echo Review month: %MONTH%
echo.

REM Detect Python environment
where uv >nul 2>&1
if errorlevel 1 (
    if exist "%REAL_DIR%\.venv\Scripts\activate.bat" (
        echo Using local .venv environment...
        call "%REAL_DIR%\.venv\Scripts\activate.bat"
        set "PY=python"
    ) else (
        echo ERROR: No Python environment found.
        echo   Run setup.bat first to create the environment.
        pause
        exit /b 1
    )
) else (
    uv sync --all-packages >nul 2>&1
    set "PY=uv run python"
)

echo [1/3] Retrieving ODD files...
%PY% -m ars_analysis retrieve --month %MONTH%
echo.

echo [2/3] Formatting ODD files...
%PY% -m ars_analysis format --month %MONTH%
echo.

echo [3/3] Running batch analysis...
%PY% -m ars_analysis batch --month %MONTH%
echo.

echo Done!
pause

endlocal
