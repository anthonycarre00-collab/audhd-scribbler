@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
title The Audhd Scribbler - Installer

echo.
echo   ============================================================
echo                  THE AUDHD SCRIBBLER - INSTALLER
echo            Your memoir's calm companion. One click. Done.
echo   ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python is not installed or not in PATH.
    echo.
    echo   Please install Python 3.8 or newer from:
    echo     https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: During installation, check the box that says
    echo   "Add Python to PATH" at the bottom of the installer.
    echo.
    echo   Then re-run this script.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYVER=%%i
echo   [OK] Found %PYVER%

REM Create virtual environment
if not exist ".venv" (
    echo   Creating virtual environment...
    python -m venv .venv
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
    echo   [WARNING] Some dependencies failed to install. Trying again...
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
echo        (brain dumps, voice memos, freewrites — anything goes)
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
