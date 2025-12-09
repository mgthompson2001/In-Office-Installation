@echo off
setlocal enabledelayedexpansion

REM ==============================================
REM  CCMD Bot Installation - Main Installer
REM  This will:
REM  1. Install Python 3.11 if needed
REM  2. Install Tesseract OCR and Poppler
REM  3. Install all Python dependencies (including AI monitoring)
REM     - PDF creation libraries (PyPDF2, reportlab, fpdf2)
REM     - PDF parsing libraries (pdfplumber, pdf2image, pytesseract)
REM     - Web automation (selenium, webdriver-manager, playwright)
REM     - All bot-specific dependencies
REM  4. Create desktop shortcut "Automation Hub" with Red I icon
REM  5. Create batch wrappers for all bots
REM ==============================================

echo.
echo ================================================
echo  CCMD Bot Installation - Main Installer
echo ================================================
echo.
echo This will install all required dependencies and create
echo the desktop shortcut for launching all bots.
echo.
echo Installation steps:
echo   1. Install Python 3.11 (if needed)
echo   2. Install Tesseract OCR and Poppler (automatic)
echo   3. Install all Python packages
echo   4. Create desktop shortcut with icon
echo   5. Configure employee data transfer (automatic)
echo.
pause

REM Change to the In-Office Installation directory (this script's directory)
cd /d "%~dp0"

REM ==========================================
REM STEP 1: Install Python (if needed)
REM ==========================================
echo.
echo ================================================
echo  STEP 1: Python Installation Check
echo ================================================
echo.

REM Try to find Python using multiple methods
set "PYTHON_CMD="
set "PYTHON_VERSION="

REM Method 1: Try python command
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo !PYTHON_VERSION! | findstr /R "^3\.[8-9] ^3\.1[0-2]" >nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        goto :python_found
    )
)

REM Method 2: Try py launcher
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('py -3.11 --version 2^>^&1') do set PYTHON_VERSION=%%i
    set "PYTHON_CMD=py -3.11"
    goto :python_found
)

py -3.10 --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('py -3.10 --version 2^>^&1') do set PYTHON_VERSION=%%i
    set "PYTHON_CMD=py -3.10"
    goto :python_found
)

REM Method 3: Try direct paths
set "PYTHON_PATHS=C:\Program Files\Python311\python.exe;C:\Program Files (x86)\Python311\python.exe;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe;C:\Python311\python.exe"
for %%p in (%PYTHON_PATHS%) do (
    if exist "%%p" (
        "%%p" --version >nul 2>&1
        if not errorlevel 1 (
            for /f "tokens=2" %%i in ('"%%p" --version 2^>^&1') do set PYTHON_VERSION=%%i
            echo !PYTHON_VERSION! | findstr /R "^3\.[8-9] ^3\.1[0-2]" >nul
            if not errorlevel 1 (
                set "PYTHON_CMD=%%p"
                goto :python_found
            )
        )
    )
)

REM Python not found - install it
echo [INFO] Python not found or incompatible - running Python installer...
echo.
    call "%~dp0Installer\INSTALL_PYTHON.bat" NO_PAUSE
if errorlevel 1 (
    echo.
    echo [ERROR] Python installation failed!
    echo Please run Installer\INSTALL_PYTHON.bat manually or install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Wait longer for installation to complete
timeout /t 10 /nobreak >nul

REM Refresh PATH multiple times with different methods
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
set "PATH=!SYSTEM_PATH!;!USER_PATH!"

REM Use PowerShell to refresh PATH more reliably
powershell -NoProfile -Command "$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')" >nul 2>&1

timeout /t 5 /nobreak >nul

REM Try to find Python again after installation
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo !PYTHON_VERSION! | findstr /R "^3\.[8-9] ^3\.1[0-2]" >nul
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
        goto :python_found
    )
)

REM Try py launcher after installation
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('py -3.11 --version 2^>^&1') do set PYTHON_VERSION=%%i
    set "PYTHON_CMD=py -3.11"
    goto :python_found
)

REM Try direct paths again
for %%p in (%PYTHON_PATHS%) do (
    if exist "%%p" (
        "%%p" --version >nul 2>&1
        if not errorlevel 1 (
            for /f "tokens=2" %%i in ('"%%p" --version 2^>^&1') do set PYTHON_VERSION=%%i
            echo !PYTHON_VERSION! | findstr /R "^3\.[8-9] ^3\.1[0-2]" >nul
            if not errorlevel 1 (
                set "PYTHON_CMD=%%p"
                goto :python_found
            )
        )
    )
)

REM Still not found - give helpful error
echo [ERROR] Python was installed but cannot be found in PATH
echo.
echo Please try one of the following:
echo   1. Close this window, open a NEW Command Prompt, and run INSTALL_BOTS.bat again
echo   2. Restart your computer and run INSTALL_BOTS.bat again
echo   3. Manually add Python to PATH and run INSTALL_BOTS.bat again
echo.
pause
exit /b 1

:python_found
echo [OK] Python found: !PYTHON_CMD! (version: !PYTHON_VERSION!)
echo.

REM ==========================================
REM STEP 2: Install Tesseract and Poppler
REM ==========================================
echo ================================================
echo  STEP 2: OCR Dependencies (Tesseract and Poppler)
echo ================================================
echo.
echo [INFO] Installing OCR dependencies...
echo This may take a few minutes if downloading...
echo.

REM Install both using the unified script (more reliable)
set "OCR_SCRIPT=%~dp0Installer\install_ocr_dependencies.ps1"
if exist "%OCR_SCRIPT%" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%OCR_SCRIPT%" -InstallDir "%~dp0" 2>&1
    if errorlevel 1 (
        echo [WARNING] OCR installation had some issues, but continuing...
        echo The bot will still work for text-based PDFs.
    ) else (
        echo [OK] OCR dependencies installation completed
    )
) else (
    echo [WARNING] OCR installer script not found, skipping...
    echo The bot will still work for text-based PDFs.
)
echo.

REM ==========================================
REM STEP 3: Upgrade pip
REM ==========================================
echo ================================================
echo  STEP 3: Upgrading pip
echo ================================================
echo.

!PYTHON_CMD! -m pip install --quiet --upgrade pip --no-warn-script-location
if errorlevel 1 (
    echo [WARNING] pip upgrade failed, continuing anyway...
)
echo.

REM ==========================================
REM STEP 4: Install Python packages
REM ==========================================
echo ================================================
echo  STEP 4: Installing Python Packages
echo ================================================
echo.
echo This will install all dependencies and create the desktop shortcut.
echo.

REM Run the main installation script
!PYTHON_CMD! "Installer\install_for_employee.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Main installation failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo [OK] Main installation completed successfully!
echo.

echo.
echo ================================================
echo Installation Summary
echo ================================================
echo.
echo Installation complete! Check the following:
echo.
echo 1. Desktop shortcut "Automation Hub" should be on your desktop
echo 2. The shortcut should have a RED "I" icon (not blank)
echo 3. Double-click the shortcut to launch the bot launcher
echo.
echo If you don't see the desktop shortcut:
echo   - Check if you have permission to create desktop shortcuts
echo   - Try running this installer as Administrator
echo   - Contact IT support
echo.
echo If the icon is blank (white page):
echo   - The icon file may not be accessible
echo   - Try running this installer as Administrator
echo   - Contact IT support
echo.
echo If you see errors about missing modules:
echo   - The installer should have installed them automatically
echo   - This includes PDF creation libraries (PyPDF2, reportlab, fpdf2)
echo   - This includes web automation (selenium, webdriver-manager)
echo   - If not, contact IT support with the error message
echo.
echo ================================================
pause

:end
endlocal
