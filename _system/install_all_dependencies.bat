@echo off
echo ======================================================================
echo Full System Monitoring - Complete Dependency Installation
echo ======================================================================
echo.
echo This will install ALL dependencies for full system monitoring.
echo.
cd /d "%~dp0"

echo.
echo Installing core dependencies...
python -m pip install --upgrade mss pynput psutil watchdog cryptography pillow opencv-python numpy

echo.
echo Installing advanced AI dependencies...
python -m pip install --upgrade transformers torch accelerate langchain langchain-community ollama pandas scikit-learn requests httpx

echo.
echo ======================================================================
echo Installation Complete!
echo ======================================================================
echo.
echo Verifying installation...
python verify_full_monitoring_dependencies.py

echo.
pause

