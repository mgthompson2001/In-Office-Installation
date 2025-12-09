@echo off
REM Setup Ollama to Auto-Start on Windows Boot
REM This ensures Ollama is always available for training

echo ======================================================================
echo SETTING UP OLLAMA AUTO-START
echo ======================================================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] This script requires Administrator privileges.
    echo.
    echo Please right-click this file and select "Run as Administrator"
    pause
    exit /b 1
)

echo Finding Ollama installation...

REM Try to find Ollama
where ollama >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where ollama') do set OLLAMA_PATH=%%i
    echo [OK] Found Ollama at: %OLLAMA_PATH%
) else (
    REM Check common locations
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        set OLLAMA_PATH=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
        echo [OK] Found Ollama at: %OLLAMA_PATH%
    ) else if exist "C:\Program Files\Ollama\ollama.exe" (
        set OLLAMA_PATH=C:\Program Files\Ollama\ollama.exe
        echo [OK] Found Ollama at: %OLLAMA_PATH%
    ) else (
        echo [ERROR] Could not find Ollama installation.
        echo Please install Ollama from https://ollama.ai first.
        pause
        exit /b 1
    )
)

echo.
echo Creating scheduled task for auto-start...

REM Create scheduled task to start Ollama on login
schtasks /create /tn "Ollama Auto-Start" /tr "\"%OLLAMA_PATH%\" serve" /sc onlogon /ru "%USERNAME%" /f >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [OK] Scheduled task created successfully!
    echo.
    echo Ollama will now start automatically when you log in.
    echo.
    echo To test, you can start it now:
    echo   "%OLLAMA_PATH%" serve
    echo.
    echo Or restart your computer to verify auto-start works.
) else (
    echo [ERROR] Failed to create scheduled task.
    echo You may need to create it manually in Task Scheduler.
)

echo.
pause

