@echo off
REM XAI Blockchain Node Launcher for Windows
REM This script launches the XAI node with proper environment setup

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
set "XAI_CONFIG_DIR=%XAI_DATA_DIR%\config"
set "XAI_LOG_DIR=%XAI_DATA_DIR%\logs"

REM Create directories if they don't exist
if not exist "%XAI_DATA_DIR%\blockchain" mkdir "%XAI_DATA_DIR%\blockchain"
if not exist "%XAI_DATA_DIR%\wallets" mkdir "%XAI_DATA_DIR%\wallets"
if not exist "%XAI_DATA_DIR%\state" mkdir "%XAI_DATA_DIR%\state"
if not exist "%XAI_LOG_DIR%" mkdir "%XAI_LOG_DIR%"
if not exist "%XAI_CONFIG_DIR%" mkdir "%XAI_CONFIG_DIR%"

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
echo   XAI Blockchain Node
echo   Version: 0.2.0
echo ===============================================
echo.
echo Data Directory: %XAI_DATA_DIR%
echo Config Directory: %XAI_CONFIG_DIR%
echo Log Directory: %XAI_LOG_DIR%
echo.

REM Launch the node
"%PYTHON_EXE%" -m xai.core.node %*

REM Check exit code
if errorlevel 1 (
    echo.
    echo ERROR: XAI Node exited with error code %errorlevel%
    echo Check logs at: %XAI_LOG_DIR%
    pause
    exit /b %errorlevel%
)

endlocal
