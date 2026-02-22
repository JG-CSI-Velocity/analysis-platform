@echo off
setlocal
echo ==========================================
echo  Analysis Platform -- First-Time Setup
echo ==========================================
echo.

set "REAL_DIR=%~dp0"
if "%REAL_DIR:~-1%"=="\" set "REAL_DIR=%REAL_DIR:~0,-1%"

REM Check for Python
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo Found Python:
python --version
echo.

REM Delete old venv if it exists (clean slate)
if exist "%REAL_DIR%\.venv" (
    echo Removing old .venv for clean install...
    rmdir /s /q "%REAL_DIR%\.venv"
)

echo Creating virtual environment...
python -m venv "%REAL_DIR%\.venv"
if errorlevel 1 (
    echo ERROR: Failed to create .venv
    pause
    exit /b 1
)

echo Activating environment...
call "%REAL_DIR%\.venv\Scripts\activate.bat"

echo.
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

echo.
echo Installing dependencies (this may take a few minutes)...
pip install pandas numpy matplotlib plotly openpyxl python-pptx pydantic pydantic-core pyyaml streamlit rich typer xlrd kaleido==0.2.1
if errorlevel 1 (
    echo ERROR: Dependency install failed.
    pause
    exit /b 1
)

echo.
echo Installing workspace packages...
pip install --no-deps -e "%REAL_DIR%\packages\shared" -e "%REAL_DIR%\packages\ars_analysis" -e "%REAL_DIR%\packages\txn_analysis" -e "%REAL_DIR%\packages\ics_toolkit" -e "%REAL_DIR%\packages\platform_app"
if errorlevel 1 (
    echo ERROR: Workspace package install failed.
    pause
    exit /b 1
)

echo.
echo Verifying installation...
python -c "import shared; import ars_analysis; import txn_analysis; import ics_toolkit; import platform_app; print('All packages OK')"
if errorlevel 1 (
    echo.
    echo WARNING: Verification failed. Try running setup.bat again.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  Setup complete!
echo ==========================================
echo.
echo  To launch: double-click dashboard.bat
echo.
pause

endlocal
