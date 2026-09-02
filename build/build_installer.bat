@echo off
cd /d "%~dp0\.."
echo.
echo   ============================================================
echo         Audhd Scribbler — Build Installer
echo   ============================================================
echo.

echo   Step 1: Building EXE...
call build\build_exe.bat
if errorlevel 1 exit /b 1

echo.
echo   Step 2: Building Inno Setup installer...
iscc build\windows.iss
if errorlevel 1 (
    echo.
    echo   [FAILED] Inno Setup failed. Install Inno Setup first.
    echo   Download from: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

echo.
echo   ============================================================
echo              INSTALLER COMPLETE
echo   ============================================================
echo.
echo   Output: dist\Audhd-Scribbler-Setup.exe
echo.
pause
