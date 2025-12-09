@echo off
setlocal enabledelayedexpansion

REM ==============================================
REM  Python Installer - Downloads and Installs Python 3.11
REM  This script ensures Python 3.8-3.12 is installed before running INSTALL_BOTS.bat
REM ==============================================

echo.
echo ================================================
echo  Python Installation Check & Installer
echo ================================================
echo.
echo This script will check for Python and install Python 3.11.10 if needed.
echo Python 3.8-3.12 is required for all bots.
echo.
pause

REM Change to the root installation directory (parent of Installer folder)
cd /d "%~dp0.."

REM Check if Python is already installed and compatible
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [INFO] Found Python: !PYTHON_VERSION!
    
    REM Check if version is compatible (3.8-3.12)
    echo !PYTHON_VERSION! | findstr /R "^3\.[8-9] ^3\.1[0-2]" >nul
    if not errorlevel 1 (
        echo [OK] Python !PYTHON_VERSION! is compatible!
        echo.
        echo Python is already installed and compatible.
        echo You can proceed with INSTALL_BOTS.bat
        echo.
        pause
        exit /b 0
    ) else (
        echo [WARNING] Python !PYTHON_VERSION! is not compatible
        echo          Required: Python 3.8 - 3.12
        echo          Will install Python 3.11.10...
        echo.
    )
) else (
    echo [INFO] Python not found - will install Python 3.11.10
    echo.
)

REM Run the Python installer PowerShell script (now in same folder as this script)
set "PYTHON_INSTALLER=%~dp0install_python.ps1"

if not exist "%PYTHON_INSTALLER%" (
    echo [ERROR] Python installer script not found at: %PYTHON_INSTALLER%
    echo.
    echo Please install Python manually:
    echo   1. Download from: https://www.python.org/downloads/
    echo   2. Select Python 3.10 or 3.11
    echo   3. Check 'Add Python to PATH' during installation
    echo.
    pause
    exit /b 1
)

echo [INFO] Running Python installer...
echo This may take a few minutes...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%PYTHON_INSTALLER%" -PreferredVersion "3.11.10"

if errorlevel 1 (
    echo.
    echo [ERROR] Python installation failed!
    echo.
    echo Please install Python manually:
    echo   1. Download from: https://www.python.org/downloads/
    echo   2. Select Python 3.10 or 3.11
    echo   3. Check 'Add Python to PATH' during installation
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Python installation completed!
echo.

REM Wait for PATH to refresh
timeout /t 5 /nobreak >nul

REM Refresh PATH from registry
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
set "PATH=!SYSTEM_PATH!;!USER_PATH!"

REM Verify installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Python installed but not yet in PATH
    echo          Please close this window and restart your terminal
    echo          Then run INSTALL_BOTS.bat again
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python !PYTHON_VERSION! is now available!
echo.
echo Python installation successful!
echo You can now proceed with INSTALL_BOTS.bat
echo.
REM Don't pause if called from another script (check if parent is INSTALL_BOTS.bat)
if not "%1"=="NO_PAUSE" (
    pause
)

:end
endlocal

