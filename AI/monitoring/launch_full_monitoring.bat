@echo off
cd /d "%~dp0"

REM Try to use Python 3.14 first (where packages are installed)
set PYTHON_EXE=python
if exist "C:\Users\mthompson\AppData\Local\Programs\Python\Python314\python.exe" (
    set PYTHON_EXE=C:\Users\mthompson\AppData\Local\Programs\Python\Python314\python.exe
)

echo Installing/verifying dependencies...
REM Install core dependencies (skip numpy - already installed and may need compiler)
"%PYTHON_EXE%" -m pip install --quiet --upgrade --only-binary :all: mss pynput psutil watchdog cryptography pillow
echo.
echo Launching Full System Monitoring GUI...
"%PYTHON_EXE%" full_monitoring_gui.py
pause

