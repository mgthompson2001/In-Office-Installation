@echo off
REM Bot Installation Script - Enterprise Deployment
REM Automatically installs all dependencies and creates desktop shortcut

echo ====================================================================
echo Enterprise Bot Installation
echo ====================================================================
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory
cd /d "%SCRIPT_DIR%"

REM Run the Python installation script (creates desktop shortcut automatically)
python install_bots.py
set INSTALL_EXIT_CODE=%ERRORLEVEL%

REM If Python script failed, try VBScript shortcut creation as fallback
if %INSTALL_EXIT_CODE% NEQ 0 (
    echo.
    echo Attempting to create desktop shortcut using VBScript...
    cscript //nologo create_desktop_shortcut_universal.vbs
)

REM Always try to create shortcut (even if Python succeeded, as backup)
echo.
echo Verifying desktop shortcut creation...
cscript //nologo create_desktop_shortcut_universal.vbs

REM Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error occurred! Press any key to close...
    pause > nul
)

