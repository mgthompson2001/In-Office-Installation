@echo off
echo ======================================================================
echo Full System Monitoring - Dependency Installation
echo ======================================================================
echo.
echo This will install required dependencies for full system monitoring.
echo.
echo Required packages:
echo   - mss (screen capture)
echo   - pynput (keyboard/mouse monitoring)
echo   - psutil (process monitoring)
echo   - watchdog (file system monitoring)
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

cd /d "%~dp0"

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install mss>=9.0.0
python -m pip install pynput>=1.7.6
python -m pip install psutil>=5.9.0
python -m pip install watchdog>=3.0.0

echo.
echo ======================================================================
echo Installation Complete!
echo ======================================================================
echo.
echo You can now launch Full System Monitoring using:
echo   launch_full_monitoring.bat
echo.
pause

