@echo off
echo Installing Referral Document Cleanup Bot dependencies...
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Find Python
set "PYTHON_CMD="

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :install
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :install
)

py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :install
)

echo [ERROR] Python is not installed or not in PATH
echo Please install Python 3.8+ from https://www.python.org/
pause
exit /b 1

:install
echo Using Python: %PYTHON_CMD%
echo.
echo Installing required packages...
echo.

%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo Installation complete!
echo.
echo You can now run the bot by double-clicking: referral_document_cleanup_bot.bat
echo.
pause

