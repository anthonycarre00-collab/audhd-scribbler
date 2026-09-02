@echo off
cd /d "%~dp0\.."
echo.
echo   ============================================================
echo              Audhd Scribbler — Build EXE
echo   ============================================================
echo.

echo   Cleaning previous build...
rmdir /s /q build\__pycache__ 2>nul
rmdir /s /q dist\AudhdScribbler 2>nul

echo   Building with PyInstaller...
pyinstaller build\scribbler.spec --noconfirm --clean
if errorlevel 1 (
    echo.
    echo   [FAILED] PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo   ============================================================
echo              BUILD COMPLETE
echo   ============================================================
echo.
echo   Output: dist\AudhdScribbler\AudhdScribbler.exe
echo.
echo   To create installer: run build_installer.bat
echo.
pause
