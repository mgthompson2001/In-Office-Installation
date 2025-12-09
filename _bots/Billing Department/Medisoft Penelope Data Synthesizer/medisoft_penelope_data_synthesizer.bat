@echo off
REM Wrapper for medisoft_penelope_data_synthesizer.py
REM Auto-generated batch wrapper for: medisoft_penelope_data_synthesizer.py

echo Starting medisoft_penelope_data_synthesizer.py...
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

REM Try 'py' (Python launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :run_bot
)

REM Try 'python3'
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :run_bot
)

REM If we get here, Python wasn't found
echo ERROR: Python not found!
echo.
echo Please install Python 3.7 or later from https://www.python.org/
echo Or add Python to your PATH environment variable.
echo.
pause
exit /b 1

:run_bot
echo Using Python: %PYTHON_CMD%
echo Running: medisoft_penelope_data_synthesizer.py
echo.

REM Run the Python script
%PYTHON_CMD% "medisoft_penelope_data_synthesizer.py"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)

