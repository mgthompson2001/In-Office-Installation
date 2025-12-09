@echo off
REM Wrapper for IPS_IA_Referral_Form_Uploader_Dual_Tab.py
REM Auto-generated batch wrapper for: IPS_IA_Referral_Form_Uploader_Dual_Tab.py

echo Starting IPS_IA_Referral_Form_Uploader_Dual_Tab.py...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot is located)
cd /d "%SCRIPT_DIR%"

REM Run the Python script (will use python from PATH)
python "IPS_IA_Referral_Form_Uploader_Dual_Tab.py"

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)
