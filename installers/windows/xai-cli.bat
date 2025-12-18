@echo off
REM XAI Blockchain CLI Launcher for Windows
REM This script launches the XAI command-line interface with proper environment setup

setlocal enabledelayedexpansion

REM Determine script directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Set Python path
set "PYTHON_HOME=%SCRIPT_DIR%\python"
set "PYTHON_EXE=%PYTHON_HOME%\python.exe"

REM Set XAI paths
set "XAI_HOME=%SCRIPT_DIR%"
set "XAI_DATA_DIR=%APPDATA%\XAI"

REM Set Python environment
set "PYTHONPATH=%XAI_HOME%\xai;%PYTHONPATH%"
set "PYTHONUNBUFFERED=1"

REM Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python not found at %PYTHON_EXE%
    echo Please reinstall XAI Blockchain
    pause
    exit /b 1
)

REM Display startup banner
echo.
echo ===============================================
echo   XAI Blockchain CLI
echo   Version: 0.2.0
echo ===============================================
echo.

REM Launch the CLI
"%PYTHON_EXE%" -m xai.cli.main %*

REM Check exit code
if errorlevel 1 (
    echo.
    echo ERROR: XAI CLI exited with error code %errorlevel%
    pause
    exit /b %errorlevel%
)

endlocal
