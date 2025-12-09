@echo off
cd /d "%~dp0"
python document_translator_bot.py
if errorlevel 1 (
    echo.
    echo Error running the bot. Make sure Python is installed and dependencies are installed.
    echo Run install.bat to install dependencies.
    pause
)

