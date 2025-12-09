@echo off
REM Wrapper for isws_welcome_packet_uploader_v14style_FIXED.py
REM Auto-generated batch wrapper for: isws_welcome_packet_uploader_v14style_FIXED.py

echo Starting isws_welcome_packet_uploader_v14style_FIXED.py...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot is located)
cd /d "%SCRIPT_DIR%"

REM Run the Python script (will use python from PATH)
python "isws_welcome_packet_uploader_v14style_FIXED.py"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)
