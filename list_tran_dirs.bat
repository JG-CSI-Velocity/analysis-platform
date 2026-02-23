@echo off
REM ============================================================
REM List the directory structure of M:\ARS\Incoming\Transaction Files
REM Run this on your Windows workstation, then share the output.
REM ============================================================

setlocal enabledelayedexpansion

set "ROOT=M:\ARS\Incoming\Transaction Files"

echo.
echo ============================================================
echo  ARS Transaction Files -- Directory Listing
echo  Root: %ROOT%
echo  Date: %date% %time%
echo ============================================================
echo.

if not exist "%ROOT%" (
    echo ERROR: Directory not found: %ROOT%
    echo.
    echo Checking parent directory...
    if exist "M:\ARS\Incoming" (
        echo.
        echo Contents of M:\ARS\Incoming:
        dir "M:\ARS\Incoming" /b /ad
    ) else (
        echo M:\ARS\Incoming does not exist either.
        if exist "M:\ARS" (
            echo.
            echo Contents of M:\ARS:
            dir "M:\ARS" /b /ad
        )
    )
    echo.
    pause
    exit /b 1
)

echo Folder structure (3 levels deep):
echo ----------------------------------
echo.

REM Show top-level folders (client folders)
for /d %%D in ("%ROOT%\*") do (
    echo [DIR] %%~nxD
    REM Show files in each client folder
    for %%F in ("%%D\*.*") do (
        echo       %%~nxF  (%%~zF bytes)
    )
    REM Show subfolders if any
    for /d %%S in ("%%D\*") do (
        echo       [DIR] %%~nxS
        for %%F in ("%%S\*.*") do (
            echo             %%~nxF  (%%~zF bytes)
        )
    )
    echo.
)

echo.
echo ============================================================
echo  Total client folders:
dir "%ROOT%" /b /ad 2>nul | find /c /v ""
echo ============================================================

REM Also save to file for easy sharing
set "OUTFILE=%~dp0tran_dirs_output.txt"
echo.
echo Saving full output to: %OUTFILE%

(
    echo ARS Transaction Files -- Directory Listing
    echo Root: %ROOT%
    echo Date: %date% %time%
    echo.
    tree "%ROOT%" /f
) > "%OUTFILE%"

echo Done. Share the file: %OUTFILE%
echo.
pause
