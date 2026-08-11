@echo off
cd /d "%~dp0"
title The Audhd Scribbler - Installer

echo.
echo   ============================================================
echo                  THE AUDHD SCRIBBLER - INSTALLER
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
    echo   You said Python 3.14 is installed, but Windows can't find it.
    echo   This means Python was not added to PATH during install.
    echo.
    echo   FIX:
    echo   1. Press Windows key, type "environment variables"
    echo   2. Open "Edit the system environment variables"
    echo   3. Click "Environment Variables" button
    echo   4. Under "User variables", find "Path", click Edit
    echo   5. Click New, add: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314
    echo   6. Click New, add: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314\Scripts
    echo   7. Click OK on all windows, close any command prompts
    echo   8. Re-run this installer
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYCMD% --version') do set PYVER=%%i
echo   [OK] Found %PYVER%

REM Step 2: Delete old broken venv (THIS IS THE KEY FIX)
echo.
echo   Step 2: Cleaning up old installation...
if exist ".venv" (
    echo   Found old .venv - deleting it to start fresh...
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
    echo   This is unusual. Error has been saved to install.log
    echo.
    pause
    exit /b 1
)
echo   [OK]

REM Step 4: Activate venv and verify it works
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
python -m pip install --upgrade pip > install.log 2>&1
if errorlevel 1 (
    echo   [WARNING] pip upgrade had issues, continuing anyway...
)

REM Step 6: Install dependencies
echo.
echo   Step 6: Installing dependencies (this takes 2-3 minutes)...
echo   (Progress is being saved to install.log)
pip install -r requirements.txt >> install.log 2>&1
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not install dependencies.
    echo.
    echo   This is likely a Python 3.14 compatibility issue.
    echo   Python 3.14 is very new and some packages may not support it yet.
    echo.
    echo   RECOMMENDED FIX:
    echo   Install Python 3.12 from https://www.python.org/downloads/
    echo   During install, check "Add Python to PATH"
    echo   Then re-run this installer.
    echo.
    echo   --- Last 20 lines of error log: ---
    powershell -command "Get-Content install.log -Tail 20" 2>nul
    echo   -----------------------------------
    echo.
    echo   Full log saved to: install.log
    echo   Send me this file if you need help.
    echo.
    pause
    exit /b 1
)
echo   [OK]

REM Step 7: Install scribbler package
echo.
echo   Step 7: Installing scribbler...
pip install -e . >> install.log 2>&1
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not install scribbler.
    echo   See install.log for details.
    echo.
    pause
    exit /b 1
)
echo   [OK]

REM Step 8: Download spaCy model
echo.
echo   Step 8: Downloading language model (about 1 minute)...
python -m spacy download en_core_web_sm >> install.log 2>&1
if errorlevel 1 (
    echo   [WARNING] Language model download skipped.
    echo   Character detection will use a simpler fallback method.
    echo   Everything else still works.
) else (
    echo   [OK]
)

REM Step 9: Initialize project
echo.
echo   Step 9: Setting up folders...
python -m scribbler.cli init
if errorlevel 1 (
    echo.
    echo   [FAILED] Could not set up folders.
    echo.
    pause
    exit /b 1
)

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
echo     4. Pick option 2 to see your dashboard
echo.
echo   That's it. No console needed.
echo.
pause
