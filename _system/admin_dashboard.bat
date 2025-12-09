@echo off
REM Admin Dashboard - View Employee Registry and Collected Data
REM Run this to view all registered employees and their collected data

echo ====================================================================
echo Admin Dashboard - Employee Registry and Data Review
echo ====================================================================
echo.
echo This will show you all registered employees and their collected data.
echo.
pause

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory
cd /d "%SCRIPT_DIR%"

REM Run the admin dashboard
python admin_dashboard.py

pause

