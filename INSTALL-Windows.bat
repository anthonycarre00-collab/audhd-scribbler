@echo off
cd /d "%~dp0"
title The Audhd Scribbler - Installer
set PYTHONIOENCODING=utf-8

echo.
echo   ============================================================
echo                  THE AUDHD SCRIBBLER - INSTALLER
echo            One click. Done. No console needed after this.
echo   ============================================================
echo.

REM Step 1: Find Python
echo   Step 1: Looking for Python...
set "PYCMD="
python --version >nul 2>&1 && set "PYCMD=python"
if not defined PYCMD (
    py --version >nul 2>&1 && set "PYCMD=py"
)
if not defined PYCMD (
    python3 --version >nul 2>&1 && set "PYCMD=python3"
)

if not defined PYCMD (
    echo.
    echo   [FAILED] Python not found in PATH.
    echo.
    echo   Install Python 3.10-3.13 from https://www.python.org/downloads/
    echo   IMPORTANT: Check "Add Python to PATH" during install.
    echo   Python 3.14 may have compatibility issues — use 3.12 or 3.13.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYCMD% --version') do set PYVER=%%i
echo   [OK] Found %PYVER%

REM Step 2: Delete old broken venv
echo.
echo   Step 2: Cleaning up old installation...
if exist ".venv" (
    echo   Found old .venv - deleting to start fresh...
    rmdir /s /q .venv
)
if exist "install.log" del install.log
echo   [OK]

REM Step 3: Create fresh venv
echo.
echo   Step 3: Creating virtual environment...
%PYCMD% -m venv .venv
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not create virtual environment.
    pause
    exit /b 1
)
echo   [OK]

REM Step 4: Activate and verify
echo.
echo   Step 4: Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not activate virtual environment.
    pause
    exit /b 1
)
echo   [OK]

REM Step 5: Upgrade pip
echo.
echo   Step 5: Updating pip...
python -m pip install --upgrade pip --quiet

REM Step 6: Install dependencies
echo.
echo   Step 6: Installing dependencies (2-3 minutes)...
echo   (Progress saved to install.log)
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo   [WARNING] Retrying with verbose output...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo   [FAILED] Could not install dependencies.
        echo   This may be a Python version issue.
        echo   Python 3.12 or 3.13 recommended.
        echo.
        echo   --- Last 20 lines of error log: ---
        powershell -command "Get-Content install.log -Tail 20" 2>nul
        echo   -----------------------------------
        echo.
        pause
        exit /b 1
    )
)
echo   [OK]

REM Step 7: Install scribbler
echo.
echo   Step 7: Installing scribbler...
pip install -e . --quiet
echo   [OK]

REM Step 8: spaCy model
echo.
echo   Step 8: Downloading language model (about 1 minute)...
python -m spacy download en_core_web_sm --quiet
if errorlevel 1 (
    echo   [WARNING] Language model download skipped. Using fallback.
) else (
    echo   [OK]
)

REM Step 9: Initialize
echo.
echo   Step 9: Setting up folders...
python -m scribbler.cli init

echo.
echo   ============================================================
echo                     INSTALLATION COMPLETE!
echo   ============================================================
echo.
echo   Your tool is ready. To use it:
echo.
echo     1. Drop text files (.txt or .md) into the "raw-dumps" folder
echo     2. Double-click "SCRIBBLER-Windows.bat" to open the menu
echo     3. Pick option 1 to tag your files
echo     4. Pick option 8 to analyze a chapter
echo     5. Pick option 10 for manuscript-level analysis
echo.
echo   That's it. No console needed.
echo.
pause
