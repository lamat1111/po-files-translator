@echo off
:: Po File Translator - po-file-translator
:: Direct launcher for this tool

title Po File Translator

:: Check if Python is available (try python3 first, then python)
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo ❌ Python is not installed or not in PATH
        echo Please install Python 3.x and try again
        pause
        exit /b 1
    )
)

:: Change to script directory
cd /d "%~dp0"

:: Launch the tool
echo 🚀 Starting Po File Translator...
%PYTHON_CMD% run.py

:: Keep window open to see results
pause