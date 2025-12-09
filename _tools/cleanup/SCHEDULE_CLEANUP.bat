@echo off
REM Schedule System Cleanup to Run Daily via Windows Task Scheduler
REM This ensures cleanup runs even if no bots are used

echo Scheduling System-Wide Cleanup Service...
echo.

REM Get installation root directory
cd /d "%~dp0\..\.."

REM Create scheduled task to run cleanup daily at 2 AM
REM Use full path to the cleanup service
set "CLEANUP_SCRIPT=%~dp0SYSTEM_CLEANUP_SERVICE.py"
set "WORK_DIR=%~dp0\..\.."
schtasks /create /tn "Integrity Bots - System Cleanup" /tr "python \"%CLEANUP_SCRIPT%\"" /sc daily /st 02:00 /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Cleanup scheduled to run daily at 2:00 AM
    echo.
    echo To view the task:
    echo   schtasks /query /tn "Integrity Bots - System Cleanup"
    echo.
    echo To run manually:
    echo   python "_tools\cleanup\SYSTEM_CLEANUP_SERVICE.py"
    echo.
    echo To remove the scheduled task:
    echo   schtasks /delete /tn "Integrity Bots - System Cleanup" /f
) else (
    echo.
    echo ERROR: Failed to create scheduled task
    echo You may need to run this as Administrator
)

pause
