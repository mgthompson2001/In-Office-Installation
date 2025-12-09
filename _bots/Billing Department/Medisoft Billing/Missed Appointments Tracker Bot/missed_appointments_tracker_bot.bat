@echo off
REM Wrapper for missed_appointments_tracker_bot.py
REM Auto-generated batch wrapper for: missed_appointments_tracker_bot.py

echo Starting Missed Appointments Tracker Bot...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot is located)
cd /d "%SCRIPT_DIR%"

REM Find Python - try multiple methods
set "PYTHON_CMD="

REM Try 'python' first
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :run_bot
)

REM Try 'python3' next
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :run_bot
)

REM Try 'py' launcher (Windows Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :run_bot
)

REM Python not found
echo [ERROR] Python is not installed or not in PATH
echo.
echo Please install Python 3.7+ from https://www.python.org/
echo Make sure to check "Add Python to PATH" during installation
echo.
echo Or run the installer: install.bat
echo.
pause
exit /b 1

:run_bot
REM Run the Python script
%PYTHON_CMD% "missed_appointments_tracker_bot.py"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)

