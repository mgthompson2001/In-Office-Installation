@echo off
REM Fix for NumPy compilation error
REM This installs NumPy using pre-built wheels to avoid compilation

echo ================================================
echo NumPy Installation Fix
echo ================================================
echo.
echo This will install NumPy using pre-built wheels
echo to avoid compilation errors on systems without
echo Visual Studio C++ compiler.
echo.

REM Find Python
set "PYTHON_CMD="
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :found_python
)

py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :found_python
)

echo [ERROR] Python not found!
pause
exit /b 1

:found_python
echo [OK] Python found: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

echo Installing NumPy with pre-built wheels...
echo This avoids compilation errors.
echo.

REM Try to install NumPy with pre-built wheels
%PYTHON_CMD% -m pip install --upgrade --only-binary :all: numpy

if errorlevel 1 (
    echo.
    echo [WARNING] Pre-built wheel installation failed
    echo Trying standard installation...
    echo.
    %PYTHON_CMD% -m pip install --upgrade numpy
    if errorlevel 1 (
        echo.
        echo [ERROR] NumPy installation failed!
        echo.
        echo This usually means:
        echo   1. Python version is too new (packages don't have wheels yet)
        echo   2. Missing C++ compiler (Visual Studio)
        echo.
        echo Solutions:
        echo   1. Use Python 3.10 or 3.11 (recommended)
        echo   2. Install Visual Studio Build Tools
        echo      Download: https://visualstudio.microsoft.com/downloads/
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [OK] NumPy installation complete!
echo.
echo You can now continue with the main installation.
echo.
pause

