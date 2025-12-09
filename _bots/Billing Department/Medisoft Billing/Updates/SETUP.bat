@echo off
REM One-time setup script - just double-click this!

echo ========================================
echo Update System Setup
echo ========================================
echo.
echo This will set up version tracking for all bots.
echo You only need to run this once.
echo.
pause

cd /d "%~dp0\.."

echo.
echo Setting up bots...
echo.

python Updates\setup_all_bots.py

if errorlevel 1 (
    echo.
    echo ERROR: Setup failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Now you can push updates using PUSH_UPDATE.bat
echo.
pause
