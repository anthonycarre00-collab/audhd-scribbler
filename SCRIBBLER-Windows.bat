@echo off
cd /d "%~dp0"
title The Audhd Scribbler

REM Check if installed
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo   The Audhd Scribbler is not installed yet.
    echo.
    echo   Please double-click INSTALL-Windows.bat first to install it.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Launch the menu
python -m scribbler.menu

pause
