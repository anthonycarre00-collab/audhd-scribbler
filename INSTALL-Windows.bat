@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title The Audhd Scribbler - Windows Installer

echo.
echo   ============================================================
echo                  THE AUDHD SCRIBBLER
 echo                 WINDOWS INSTALLER
 echo   ============================================================
echo.
echo   This is a one-time setup. No terminal commands are required.
echo.

REM ------------------------------------------------------------
REM Step 1: Find a supported Python. If missing, use winget.
REM ------------------------------------------------------------
echo   Step 1/6  Checking Python...
set "PYCMD="
where py >nul 2>&1 && set "PYCMD=py"
if not defined PYCMD where python >nul 2>&1 && set "PYCMD=python"

if not defined PYCMD (
    echo.
    echo   Python is not installed. Windows Package Manager will now
    echo   install Python 3.12 automatically if winget is available.
    echo.
    where winget >nul 2>&1
    if errorlevel 1 (
        echo   [FAILED] Windows Package Manager (winget) is not available.
        echo.
        echo   Please install Python 3.12 once from python.org, then
        echo   double-click this installer again.
        echo.
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo   [FAILED] Python installation did not complete.
        echo   Please install Python 3.12 and run this installer again.
        echo.
        pause
        exit /b 1
    )
    REM Refresh PATH from the standard per-user Python location.
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYCMD=%LocalAppData%\Programs\Python\Python312\python.exe"
    if not defined PYCMD where py >nul 2>&1 && set "PYCMD=py"
    if not defined PYCMD where python >nul 2>&1 && set "PYCMD=python"
)

if not defined PYCMD (
    echo   [FAILED] Python was installed but could not be located.
    echo   Close this window, open it again, and re-run the installer.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('"%PYCMD%" --version 2^>^&1') do set PYVER=%%i
echo   [OK] Found %PYVER%

REM ------------------------------------------------------------
REM Step 2: Clean/recreate the local virtual environment.
REM ------------------------------------------------------------
echo.
echo   Step 2/6  Preparing the local environment...
if exist ".venv" rmdir /s /q .venv
if exist "install.log" del /q install.log
"%PYCMD%" -m venv .venv >> install.log 2>&1
if errorlevel 1 goto :fail_venv
echo   [OK]

REM ------------------------------------------------------------
REM Step 3: Install Python dependencies.
REM ------------------------------------------------------------
echo.
echo   Step 3/6  Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip >> install.log 2>&1
.venv\Scripts\python.exe -m pip install -r requirements.txt >> install.log 2>&1
if errorlevel 1 goto :fail_deps
echo   [OK]

REM ------------------------------------------------------------
REM Step 4: Install Scribbler locally.
REM ------------------------------------------------------------
echo.
echo   Step 4/6  Installing Scribbler...
.venv\Scripts\python.exe -m pip install -e . >> install.log 2>&1
if errorlevel 1 goto :fail_package
echo   [OK]

REM ------------------------------------------------------------
REM Step 5: Download spaCy model.
REM ------------------------------------------------------------
echo.
echo   Step 5/6  Preparing language model...
.venv\Scripts\python.exe -m spacy download en_core_web_sm >> install.log 2>&1
if errorlevel 1 echo   [WARNING] Language model download failed; fallback tagging remains available.
echo   [OK]

REM ------------------------------------------------------------
REM Step 6: Initialise folders/database.
REM ------------------------------------------------------------
echo.
echo   Step 6/6  Initialising your writing workspace...
.venv\Scripts\python.exe -m scribbler.cli init >> install.log 2>&1
if errorlevel 1 goto :fail_init

REM Create a simple desktop shortcut to the Windows launcher.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\The Audhd Scribbler.lnk'); $s.TargetPath='%~dp0SCRIBBLER-Windows.bat'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%SystemRoot%\\System32\\shell32.dll,70'; $s.Save()" >nul 2>&1

echo.
echo   ============================================================
echo                     INSTALLATION COMPLETE
 echo   ============================================================
echo.
echo   A desktop shortcut has been created.
echo.
echo   Put .txt or .md writing into the raw-dumps folder, then
 echo   double-click The Audhd Scribbler from your desktop.
echo.
echo   No console commands are required.
echo.
start "" "%~dp0SCRIBBLER-Windows.bat"
exit /b 0

:fail_venv
echo.
echo   [FAILED] Could not create the local Python environment.
goto :fail
:fail_deps
echo.
echo   [FAILED] Dependencies could not be installed.
goto :fail
:fail_package
echo.
echo   [FAILED] Scribbler could not be installed.
goto :fail
:fail_init
echo.
echo   [FAILED] The writing workspace could not be initialised.
goto :fail
:fail
echo.
echo   See install.log for the technical details.
echo   You can send that file to the developer if something went wrong.
echo.
pause
exit /b 1
