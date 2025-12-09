@echo off
REM Medisoft Billing Bot - Installation Script (Legacy)
REM This script is kept for backward compatibility
REM For new installations, use: Installer\Install.bots
REM The new installer is more robust and handles all dependencies automatically

setlocal enabledelayedexpansion

echo ========================================
echo Medisoft Billing Bot - Installation
echo ========================================
echo.
echo NOTE: This is the legacy installer.
echo For better installation experience, use: Installer\Install.bots
echo.
echo The new installer handles:
echo   - OCR dependencies (Poppler, Tesseract) automatically
echo   - Desktop shortcut with icon setup
echo   - Data migration from old installations
echo   - More robust Python detection
echo.
set /p USE_NEW="Use new installer? (Y/n): "
if /i not "!USE_NEW!"=="n" (
    if exist "Installer\Install.bots" (
        echo.
        echo Launching new installer...
        echo.
        call "Installer\Install.bots"
        exit /b %ERRORLEVEL%
    ) else (
        echo.
        echo [WARNING] New installer not found, using legacy installer...
        echo.
    )
)
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
    echo This script must be run from the Medisoft Billing Bot folder.
    echo Current directory: %CD%
    echo.
    echo Please ensure install.bat is in the same folder as:
    echo   - requirements.txt
    echo   - medisoft_billing_bot.py
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
echo [1/4] Checking Python installation...
%PYTHON_CMD% --version
if errorlevel 1 (
    echo [ERROR] Python command failed unexpectedly
    pause
    exit /b 1
)
echo.

REM Check Python version (should be 3.7+)
echo [2/4] Verifying Python version...
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: !PYTHON_VERSION!
echo.

echo [3/4] Installing required dependencies...
echo This may take a few minutes...
echo.

REM Upgrade pip first
echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
    echo.
)

REM Install core dependencies first (one at a time for better error reporting)
echo Installing core dependencies...
%PYTHON_CMD% -m pip install pyautogui pywinauto Pillow keyboard pdfplumber pdf2image pytesseract pandas openpyxl pyperclip PyPDF2 reportlab fpdf2 selenium webdriver-manager
if errorlevel 1 (
    echo.
    echo [WARNING] Some core dependencies may have failed to install
    echo Continuing with requirements.txt installation...
    echo.
)

REM Install OpenCV with pre-built wheels (avoids compilation issues)
echo.
echo Installing OpenCV (required for image recognition)...
%PYTHON_CMD% -m pip install --only-binary :all: opencv-python --quiet
if errorlevel 1 (
    echo [WARNING] OpenCV installation failed - this is optional
    echo The bot will still work without it (image recognition uses exact matching)
    echo.
)

REM Install any remaining dependencies from requirements.txt
echo Installing dependencies from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [WARNING] Some dependencies from requirements.txt may have failed
    echo This is often OK - optional packages may fail without affecting core functionality
    echo.
)

echo.
echo [4/4] Installation complete!
echo.

REM Verify critical packages are installed
echo Verifying critical packages...
%PYTHON_CMD% -c "import pyautogui; import pywinauto; import PIL; print('✓ Core packages verified')" 2>nul
if errorlevel 1 (
    echo [WARNING] Some core packages may not be installed correctly
    echo You may need to install them manually
) else (
    echo ✓ Core packages are installed correctly
)
echo.

echo ========================================
echo Installation Summary:
echo ========================================
echo.
echo Required packages installed:
echo   - pyautogui (GUI automation)
echo   - pywinauto (Windows UI automation)
echo   - Pillow (Image processing)
echo   - pandas (Excel/CSV file reading)
echo   - openpyxl (Excel .xlsx file support)
echo   - pyperclip (Clipboard operations)
echo.
echo Optional packages (if installed successfully):
echo   - keyboard (F8/F9 hotkeys for training)
echo   - opencv-python (Better image recognition)
echo   - pdfplumber (PDF parsing for insurance requests)
echo   - pdf2image (PDF to image conversion for OCR)
echo   - pytesseract (OCR text extraction)
echo   - PyPDF2 (PDF reading/manipulation)
echo   - reportlab (PDF creation/generation)
echo   - fpdf2 (Simple PDF creation)
echo   - selenium (Web browser automation)
echo   - webdriver-manager (Chrome driver management)
echo.
echo IMPORTANT - For scanned PDFs, you also need TWO additional components:
echo   1. Poppler (for PDF to image conversion):
echo      Download from: https://github.com/oschwartz10612/poppler-windows/releases/
echo      Extract and add bin folder to PATH
echo   2. Tesseract OCR (for text recognition):
echo      Download from: https://github.com/tesseract-ocr/tesseract/wiki
echo      Install and add to PATH
echo.
echo   See OCR_SETUP.md for detailed installation instructions!
echo.
echo   You can also run: setup\install_ocr.ps1 (right-click, Run with PowerShell)
echo   to automatically install Tesseract and Poppler.
echo.
echo ========================================
echo.
echo You can now run the bot by double-clicking:
echo   medisoft_billing_bot.py
echo.
echo Or run from command line:
echo   %PYTHON_CMD% medisoft_billing_bot.py
echo.
echo Installation directory: %CD%
echo.
pause

endlocal
