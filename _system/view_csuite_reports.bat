@echo off
REM Quick script to view C-Suite reports

echo Opening C-Suite Reports Viewer...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory
cd /d "%SCRIPT_DIR%"

REM Run the Python script
python view_csuite_reports.py

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)

