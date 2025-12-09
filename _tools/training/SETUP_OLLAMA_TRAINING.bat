@echo off
REM Setup Ollama for Free Local AI Training
REM This enables free, local training without API charges

echo ======================================================================
echo SETTING UP OLLAMA FOR FREE LOCAL AI TRAINING
echo ======================================================================
echo.
echo Ollama is a free, local AI training system that runs on your computer.
echo No API charges, no data sent to external servers.
echo.
echo.

REM Check if Ollama is installed
where ollama >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Ollama is already installed!
    echo.
    echo Checking if Ollama is running...
    curl -s http://localhost:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Ollama is running!
        echo.
        echo Your system is ready for free local training.
    ) else (
        echo [WARNING] Ollama is installed but not running.
        echo.
        echo Starting Ollama...
        start "" ollama serve
        timeout /t 3 >nul
        echo [OK] Ollama should now be running.
    )
) else (
    echo [ERROR] Ollama is not installed.
    echo.
    echo To install Ollama:
    echo   1. Visit: https://ollama.ai
    echo   2. Download and install Ollama
    echo   3. Run this script again
    echo.
    echo Or install via winget:
    echo   winget install Ollama.Ollama
    echo.
)

echo.
echo ======================================================================
echo SETUP COMPLETE
echo ======================================================================
echo.
echo Your cleanup system will now use Ollama for free local training.
echo Training data stays on your computer - no API charges!
echo.
pause

