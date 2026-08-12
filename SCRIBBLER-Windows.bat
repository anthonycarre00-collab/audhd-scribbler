@echo off
setlocal
cd /d "%~dp0"

REM This compatibility launcher intentionally does NOT open a console-based menu.
REM It starts the browser workspace using pythonw so no terminal remains visible.
if not exist ".venv\Scripts\pythonw.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Scribbler is not installed yet. Please run INSTALL-Windows.bat first.','The Audhd Scribbler')" >nul 2>&1
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "ScribblerWindows.py"
exit /b 0
