@echo off
setlocal enabledelayedexpansion

REM ==============================================
REM  Poppler Installer
REM  Installs Poppler for PDF to image conversion
REM ==============================================

echo.
echo ================================================
echo  Poppler Installation
echo ================================================
echo.
echo This script will install Poppler, which is required
echo for converting PDF pages to images for OCR processing.
echo.
pause

REM Change to the root installation directory (parent of Installer folder)
cd /d "%~dp0.."

REM Check if Poppler is already installed
set "POPPLER_FOUND=0"
set "POPPLER_PATH="

REM Check common installation locations
if exist "%ProgramFiles%\poppler\Library\bin\pdftoppm.exe" (
    set "POPPLER_PATH=%ProgramFiles%\poppler\Library\bin"
    set "POPPLER_FOUND=1"
) else if exist "%ProgramFiles(x86)%\poppler\Library\bin\pdftoppm.exe" (
    set "POPPLER_PATH=%ProgramFiles(x86)%\poppler\Library\bin"
    set "POPPLER_FOUND=1"
)

REM Check vendor directory (in root directory)
set "VENDOR_DIR=%~dp0..\vendor"
if exist "%VENDOR_DIR%\poppler\Library\bin\pdftoppm.exe" (
    set "POPPLER_PATH=%VENDOR_DIR%\poppler\Library\bin"
    set "POPPLER_FOUND=1"
)

if "%POPPLER_FOUND%"=="1" (
    echo [OK] Poppler is already installed at: !POPPLER_PATH!
    echo.
    if not "%1"=="NO_PAUSE" (
        echo Poppler is ready to use!
        echo.
        pause
    )
    exit /b 0
)

echo [INFO] Poppler not found - installing now...
echo.

REM Create vendor directory for portable installation (in root directory)
if not exist "%VENDOR_DIR%" mkdir "%VENDOR_DIR%"

REM Run PowerShell installer (use the correct script in Installer folder)
set "POPPLER_SCRIPT=%~dp0install_ocr_dependencies.ps1"

if exist "%POPPLER_SCRIPT%" (
    echo [INFO] Running Poppler installer...
    cd /d "%~dp0.."
    powershell -NoProfile -ExecutionPolicy Bypass -File "%POPPLER_SCRIPT%" -InstallDir "%CD%"
    cd /d "%~dp0"
    
    REM Check again after installation
    if exist "%ProgramFiles%\poppler\Library\bin\pdftoppm.exe" (
        set "POPPLER_PATH=%ProgramFiles%\poppler\Library\bin"
        set "POPPLER_FOUND=1"
    ) else if exist "%ProgramFiles(x86)%\poppler\Library\bin\pdftoppm.exe" (
        set "POPPLER_PATH=%ProgramFiles(x86)%\poppler\Library\bin"
        set "POPPLER_FOUND=1"
    ) else if exist "%VENDOR_DIR%\poppler\Library\bin\pdftoppm.exe" (
        set "POPPLER_PATH=%VENDOR_DIR%\poppler\Library\bin"
        set "POPPLER_FOUND=1"
    )
)

if "%POPPLER_FOUND%"=="1" (
    echo.
    echo [OK] Poppler installed successfully at: !POPPLER_PATH!
    echo.
    echo Setting environment variable...
    setx POPPLER_PATH "!POPPLER_PATH!" >nul 2>&1
    echo [OK] Environment variable set (restart terminal to apply)
    echo.
    echo Poppler installation complete!
    echo.
) else (
    echo.
    echo [WARNING] Poppler installation may have failed
    echo.
    echo Manual installation options:
    echo   1. Run this script as Administrator and try again
    echo   2. Install via winget: winget install -e --id Poppler.Poppler
    echo   3. Download from: https://github.com/oschwartz10612/poppler-windows/releases
    echo.
    echo The bot will still work, but PDF to image conversion may be limited.
    echo.
)

if not "%1"=="NO_PAUSE" (
    pause
)

:end
endlocal

