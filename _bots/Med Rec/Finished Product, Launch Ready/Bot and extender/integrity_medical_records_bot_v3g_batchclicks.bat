@echo off
REM Wrapper for integrity_medical_records_bot_v3g_batchclicks.py
REM Auto-generated batch wrapper for: integrity_medical_records_bot_v3g_batchclicks.py

echo Starting integrity_medical_records_bot_v3g_batchclicks.py...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot is located)
cd /d "%SCRIPT_DIR%"

REM Run the Python script (will use python from PATH)
python "integrity_medical_records_bot_v3g_batchclicks.py"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)
