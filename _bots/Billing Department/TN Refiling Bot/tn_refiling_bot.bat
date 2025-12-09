@echo off
REM Wrapper for tn_refiling_bot.py
REM Auto-generated batch wrapper for: tn_refiling_bot.py

echo Starting tn_refiling_bot.py...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot is located)
cd /d "%SCRIPT_DIR%"

REM Run the Python script (will use python from PATH)
python "tn_refiling_bot.py"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)
