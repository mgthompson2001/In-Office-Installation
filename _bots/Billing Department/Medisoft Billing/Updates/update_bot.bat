@echo off
REM Centralized Update Bot Launcher
REM Employees run this to update all their bots

cd /d "%~dp0"

echo ========================================
echo Software Update Manager
echo ========================================
echo.
echo This will help you update all your bots.
echo.

python update_bot.py

if errorlevel 1 (
    echo.
    echo ERROR: Could not start update bot
    echo Make sure Python is installed
    pause
    exit /b 1
)

