@echo off
REM Launcher for Automation Hub - Runs without console window
REM This script launches the Automation Hub without showing a console window

REM Hide this batch file's console window
if not "%1"=="min" start /min cmd /c "%~0" min & exit

REM Get the directory where this .bat file is located
set "SCRIPT_DIR=%~dp0"

REM Change to that directory
cd /d "%SCRIPT_DIR%"

REM Try to use pythonw.exe first (no console window)
where pythonw.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Use pythonw.exe (no console window)
    start "" pythonw.exe secure_launcher.py
) else (
    REM Use VBScript to hide console window (more reliable)
    cscript //nologo launch_automation_hub.vbs
)

