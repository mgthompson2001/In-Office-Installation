@echo off
echo ================================================
echo CCMD Bot Troubleshooter
echo ================================================
echo.
echo This will diagnose any issues with the bot installation.
echo.
pause

cd /d "%~dp0"
python "_system\troubleshoot_launcher.py"

echo.
echo Troubleshooting complete!
pause
