@echo off
REM Network connectivity check before installation
REM Prevents installation failures due to network issues

echo Checking network connectivity...
echo.

REM Test Python.org (for Python download)
ping -n 1 www.python.org >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Cannot reach python.org - Python download may fail
) else (
    echo [OK] Network connectivity: python.org reachable
)

REM Test GitHub (for OCR downloads)
ping -n 1 github.com >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Cannot reach github.com - OCR downloads may fail
) else (
    echo [OK] Network connectivity: github.com reachable
)

echo.
echo Network check complete. Installation will proceed.
echo If downloads fail, you may need to check your internet connection.
echo.
pause

