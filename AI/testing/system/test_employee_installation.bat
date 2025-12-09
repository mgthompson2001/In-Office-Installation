@echo off
REM Test Employee Installation Process
REM Simulates what happens when an employee runs install_bots.bat

echo ====================================================================
echo Testing Employee Installation Process
echo ====================================================================
echo.
echo This will simulate what happens when an employee runs install_bots.bat
echo.
pause

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory
cd /d "%SCRIPT_DIR%"

REM Run the installation script
echo Running installation script...
python install_bots.py

echo.
echo ====================================================================
echo Installation Test Complete
echo ====================================================================
echo.
echo Now run view_user_registry.bat to see if the test employee was registered.
echo.
pause

