@echo off
cd /d "%~dp0"
echo.
echo Launching Master AI Dashboard...
echo.
python MASTER_AI_DASHBOARD.py
if errorlevel 1 (
    echo.
    echo Error launching dashboard. Make sure Python is installed.
    pause
)

