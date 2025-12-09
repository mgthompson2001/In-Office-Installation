@echo off
echo.
echo ================================================
echo Full System Monitoring - Data Verification
echo ================================================
echo.
echo This will check if monitoring is actually recording data.
echo.
pause

cd /d "%~dp0"
python verify_monitoring_data.py

pause

