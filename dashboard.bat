@echo off
setlocal
echo ==========================================
echo  Analysis Platform -- Dashboard
echo ==========================================
echo.

set "REAL_DIR=%~dp0"
if "%REAL_DIR:~-1%"=="\" set "REAL_DIR=%REAL_DIR:~0,-1%"

set "APP=%REAL_DIR%\packages\platform_app\src\platform_app\app.py"

REM Try uv first, fall back to .venv
where uv >nul 2>&1
if errorlevel 1 (
    if exist "%REAL_DIR%\.venv\Scripts\activate.bat" (
        echo Using local .venv environment...
        call "%REAL_DIR%\.venv\Scripts\activate.bat"
        echo   Opening browser at http://localhost:8501
        echo   Close this window or press Ctrl+C to stop.
        echo.
        streamlit run "%APP%" --server.port 8501 --server.headless true
    ) else (
        echo ERROR: No Python environment found.
        echo   Run setup.bat first to create the environment.
        pause
        exit /b 1
    )
) else (
    uv sync --all-packages >nul 2>&1
    echo   Opening browser at http://localhost:8501
    echo   Close this window or press Ctrl+C to stop.
    echo.
    uv run streamlit run "%APP%" --server.port 8501
)

endlocal
