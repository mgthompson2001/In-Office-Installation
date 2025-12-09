@echo off
REM Medisoft/Penelope Data Synthesizer - Installation Script
REM This script installs all required dependencies for the bot
REM Works from any location - automatically finds the script directory

setlocal enabledelayedexpansion

echo ========================================
echo Medisoft/Penelope Data Synthesizer - Installation
echo ========================================
echo.

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory (where the bot files are located)
cd /d "%SCRIPT_DIR%"

echo [INFO] Working directory: %CD%
echo.

REM Verify we're in the right directory by checking for requirements.txt
if not exist "requirements.txt" (
    echo [ERROR] Cannot find requirements.txt in the script directory!
    echo.
    echo This script must be run from the Medisoft Penelope Data Synthesizer folder.
    echo Current directory: %CD%
    echo.
    echo Please ensure install.bat is in the same folder as:
    echo   - requirements.txt
    echo   - medisoft_penelope_data_synthesizer.py
    echo.
    pause
    exit /b 1
)

echo [INFO] Found requirements.txt - proceeding with installation...
echo.

REM Find Python - try multiple methods
set "PYTHON_CMD="

REM Try 'python' first
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :found_python
)

REM Try 'python3' next
python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :found_python
)

REM Try 'py' launcher (Windows Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :found_python
)

REM Python not found
echo [ERROR] Python is not installed or not in PATH
echo.
echo Please install Python 3.7+ from https://www.python.org/
echo Make sure to check "Add Python to PATH" during installation
echo.
echo After installing Python:
echo   1. Close and reopen this window
echo   2. Or restart your computer
echo   3. Then run this installer again
echo.
pause
exit /b 1

:found_python
echo [1/3] Checking Python installation...
%PYTHON_CMD% --version
if errorlevel 1 (
    echo [ERROR] Python command failed unexpectedly
    pause
    exit /b 1
)
echo.

REM Check Python version (should be 3.7+)
echo [2/3] Verifying Python version...
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: !PYTHON_VERSION!
echo.

echo [3/3] Installing required dependencies...
echo This may take a few minutes...
echo.

REM Upgrade pip first
echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
    echo.
)

REM Install dependencies from requirements.txt
echo Installing dependencies from requirements.txt...
echo.
echo Installing:
echo   - pandas (Excel file reading/writing)
echo   - openpyxl (Excel .xlsx file support)
echo   - pdfplumber (PDF file parsing)
echo.

%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install some dependencies
    echo.
    echo Please try installing manually:
    echo   %PYTHON_CMD% -m pip install pandas openpyxl pdfplumber
    echo.
    pause
    exit /b 1
)

echo.
echo [VERIFY] Verifying installations...
echo.

REM Verify critical packages are installed
%PYTHON_CMD% -c "import pandas; import openpyxl; import pdfplumber; print('✓ All packages verified successfully!')" 2>nul
if errorlevel 1 (
    echo [WARNING] Some packages may not be installed correctly
    echo.
    echo Verifying each package individually...
    echo.
    
    %PYTHON_CMD% -c "import pandas; print('✓ pandas')" 2>nul || echo [ERROR] pandas not found
    %PYTHON_CMD% -c "import openpyxl; print('✓ openpyxl')" 2>nul || echo [ERROR] openpyxl not found
    %PYTHON_CMD% -c "import pdfplumber; print('✓ pdfplumber')" 2>nul || echo [ERROR] pdfplumber not found
    
    echo.
    echo If any packages failed, please install them manually:
    echo   %PYTHON_CMD% -m pip install pandas openpyxl pdfplumber
) else (
    echo ✓ All required packages are installed correctly!
)
echo.

echo ========================================
echo Installation Summary:
echo ========================================
echo.
echo Required packages:
echo   ✓ pandas - Excel file reading and writing
echo   ✓ openpyxl - Excel .xlsx file support
echo   ✓ pdfplumber - PDF file parsing and table extraction
echo.
echo pdfplumber automatically installs its dependencies:
echo   - pdfminer.six (core PDF parsing library)
echo   - Pillow (image processing)
echo.
echo ========================================
echo.
echo Installation complete!
echo.
echo You can now run the bot by:
echo   1. Double-clicking: medisoft_penelope_data_synthesizer.bat
echo   2. Or launching from the Billing Department launcher
echo.
echo Installation directory: %CD%
echo.
pause

endlocal

