@echo off
cd /d "%~dp0"
title The Audhd Scribbler

REM Check if installed
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo   The Audhd Scribbler is not installed yet.
    echo.
    echo   Please double-click INSTALL-Windows.bat first.
    echo.
    pause
    exit /b 1
)

REM Clear Python cache so the latest code is always used
echo   Clearing cache...
if exist "scribbler\__pycache__" rmdir /s /q "scribbler\__pycache__"
if exist "scribbler\analyzers\__pycache__" rmdir /s /q "scribbler\analyzers\__pycache__"
if exist "scribbler\dashboard\__pycache__" rmdir /s /q "scribbler\dashboard\__pycache__"

REM Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo   The installation appears to be broken.
    echo   Please re-run INSTALL-Windows.bat to fix it.
    echo.
    pause
    exit /b 1
)

REM Launch the menu
python -m scribbler.menu

echo.
pause
