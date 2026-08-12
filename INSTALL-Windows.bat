@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title The Audhd Scribbler - First Time Setup

echo.
echo   THE AUDHD SCRIBBLER - FIRST TIME SETUP
echo   =======================================
echo.
echo   This only prepares the app. Normal use will not show a console.
echo.

set "PYCMD="
where py >nul 2>&1 && set "PYCMD=py"
if not defined PYCMD where python >nul 2>&1 && set "PYCMD=python"

if not defined PYCMD (
    echo   Python is not installed. Trying Windows Package Manager...
    where winget >nul 2>&1
    if errorlevel 1 goto :no_python
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :fail
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYCMD=%LocalAppData%\Programs\Python\Python312\python.exe"
    if not defined PYCMD where py >nul 2>&1 && set "PYCMD=py"
    if not defined PYCMD where python >nul 2>&1 && set "PYCMD=python"
)
if not defined PYCMD goto :no_python

echo   [1/5] Creating local environment...
if not exist ".venv\Scripts\python.exe" "%PYCMD%" -m venv .venv
if errorlevel 1 goto :fail

echo   [2/5] Installing application dependencies...
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt >install.log 2>&1
if errorlevel 1 goto :fail

echo   [3/5] Installing Scribbler...
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -e . >>install.log 2>&1
if errorlevel 1 goto :fail

echo   [4/5] Preparing language model...
.venv\Scripts\python.exe -m spacy download en_core_web_sm >>install.log 2>&1
REM Model failure is non-fatal; the application has fallback tagging.

echo   [5/5] Initialising your workspace...
.venv\Scripts\python.exe -m scribbler.cli init >>install.log 2>&1
if errorlevel 1 goto :fail

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\The Audhd Scribbler.lnk'); $s.TargetPath='%SystemRoot%\\System32\\wscript.exe'; $s.Arguments='"""%~dp0SCRIBBLER-Windows.vbs"""'; $s.WorkingDirectory='%~dp0'; $s.IconLocation='%SystemRoot%\\System32\\shell32.dll,70'; $s.Save()" >nul 2>&1

echo.
echo   READY. A desktop shortcut has been created.
echo   Double-click The Audhd Scribbler on the desktop.
echo.
start "" wscript.exe "%~dp0SCRIBBLER-Windows.vbs"
exit /b 0

:no_python
echo.
echo   Python could not be installed automatically.
echo   Windows Package Manager (winget) is required for first-time setup.
echo.
goto :fail

:fail
echo.
echo   SETUP DID NOT COMPLETE.
echo   See install.log for the technical details.
echo.
pause
exit /b 1
