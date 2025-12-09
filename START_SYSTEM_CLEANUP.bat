@echo off
REM Standalone System-Wide Passive Cleanup Service
REM This runs cleanup independently of any bot
REM Can be scheduled via Windows Task Scheduler or run manually

echo Starting System-Wide Passive Cleanup...
echo.

cd /d "%~dp0"

REM Run the cleanup service from the tools folder
python "_tools\cleanup\SYSTEM_CLEANUP_SERVICE.py"

echo.
echo Cleanup complete. Press any key to exit...
pause >nul
