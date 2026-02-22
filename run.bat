@echo off
setlocal
echo ==========================================
echo  Analysis Platform v2.0
echo  CSI Velocity Solutions
echo ==========================================
echo.

set "REAL_DIR=%~dp0"
if "%REAL_DIR:~-1%"=="\" set "REAL_DIR=%REAL_DIR:~0,-1%"

set "APP=%REAL_DIR%\packages\platform_app\src\platform_app\app.py"

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
        set "ST=streamlit"
    ) else (
        echo ERROR: No Python environment found.
        echo   Run setup.bat first to create the environment.
        pause
        exit /b 1
    )
) else (
    echo Syncing packages...
    uv sync --all-packages >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Package sync failed.
        pause
        exit /b 1
    )
    set "PY=uv run python"
    set "ST=uv run streamlit"
)

echo [1/3] Retrieving and formatting ODD files...
%PY% -m ars_analysis retrieve --month %MONTH%
%PY% -m ars_analysis format --month %MONTH%
echo.

echo [2/3] Running batch analysis...
%PY% -m ars_analysis batch --month %MONTH%
echo.

echo [3/3] Launching Streamlit dashboard...
echo   Close this window or press Ctrl+C to stop.
echo.
%ST% run "%APP%" --server.port 8501 --server.headless true

endlocal
