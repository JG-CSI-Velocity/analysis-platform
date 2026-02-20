@echo off
setlocal
echo ==========================================
echo  Analysis Platform -- Dashboard
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

echo   Opening browser at http://localhost:8501
echo   Close this window or press Ctrl+C to stop.
echo.
uv run streamlit run "%REAL_DIR%\packages\platform_app\src\platform_app\app.py" --server.port 8501

endlocal
