@echo off
REM Referral Document Cleanup Bot Launcher
REM This batch file launches the bot with Python

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Run the bot
python referral_document_cleanup_bot.py

if errorlevel 1 (
    echo.
    echo An error occurred. Check the log for details.
    pause
)

