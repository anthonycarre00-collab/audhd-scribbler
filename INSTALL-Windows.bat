@echo off
cd /d "%~dp0"
title The Audhd Scribbler - Installer

echo.
echo   ============================================================
echo                  THE AUDHD SCRIBBLER - INSTALLER
echo            Your memoir's calm companion. One click. Done.
echo   ============================================================
echo.

REM Try to find Python (python, py launcher, or python3)
set "PYCMD="
python --version >nul 2>&1 && set "PYCMD=python"
if not defined PYCMD (
    py --version >nul 2>&1 && set "PYCMD=py"
)
if not defined PYCMD (
    python3 --version >nul 2>&1 && set "PYCMD=python3"
)

if not defined PYCMD (
    echo   [ERROR] Python is not installed or not in PATH.
    echo.
    echo   You said Python 3.14 is installed, but Windows can't find it.
    echo   This usually means Python was not added to PATH during install.
    echo.
    echo   FIX: Open the Python installer again and choose "Modify",
    echo   then make sure "Add Python to PATH" is checked.
    echo.
    echo   Or add Python manually to PATH:
    echo   1. Find where Python is installed (usually C:\Users\YOU\AppData\Local\Programs\Python\Python314)
    echo   2. Search Windows for "Environment Variables"
    echo   3. Edit PATH, add the Python folder and the Python\Scripts folder
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYCMD% --version') do set PYVER=%%i
echo   [OK] Found %PYVER%

REM Create virtual environment
if not exist ".venv" (
    echo   Creating virtual environment...
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo   [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip
echo   Updating pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo   Installing dependencies (this takes 2-3 minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo   [WARNING] Retrying dependency install with verbose output...
    pip install -r requirements.txt
)

REM Install the package
echo   Installing scribbler...
pip install -e . --quiet

REM Download spaCy model
echo   Downloading language model (this takes a minute)...
python -m spacy download en_core_web_sm --quiet
if errorlevel 1 (
    echo   [WARNING] Language model download skipped. Character detection will use fallback.
)

REM Initialize project
echo   Setting up folders...
python -m scribbler.cli init

echo.
echo   ============================================================
echo                     INSTALLATION COMPLETE!
echo   ============================================================
echo.
echo   Your tool is ready. To use it:
echo.
echo     1. Drop text files (.txt or .md) into the "raw-dumps" folder
echo        (brain dumps, voice memos, freewrites - anything goes)
echo.
echo     2. Double-click "SCRIBBLER-Windows.bat" to open the menu
echo.
echo     3. Pick option 1 to tag your files
echo.
echo     4. Pick option 2 to see your dashboard
echo.
echo   That's it. No console needed.
echo.
pause
