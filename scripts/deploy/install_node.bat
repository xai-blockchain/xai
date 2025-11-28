@echo off
REM XAI Blockchain Node Installation Script - Windows
REM INTERNAL USE ONLY - DELETE BEFORE PUBLIC RELEASE

echo ============================================================
echo XAI BLOCKCHAIN NODE INSTALLER (Windows)
echo ============================================================
echo.

REM Check Python
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

python --version
echo.

REM Create installation directory
echo [2/6] Creating installation directory...
set INSTALL_DIR=%USERPROFILE%\xai-blockchain
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"
echo Installation directory: %INSTALL_DIR%
echo.

REM Copy files
echo [3/6] Installing XAI blockchain...
REM In production, files would be downloaded
REM For now, assume running from source directory
if exist "..\core\node.py" (
    xcopy /E /I /Y ..\*.* .
    echo Files copied from source
) else (
    echo Error: Blockchain files not found
    pause
    exit /b 1
)
echo.

REM Create virtual environment
echo [4/6] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [5/6] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Create data directories
echo [6/6] Creating data directories...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "gamification_data" mkdir gamification_data
if not exist "mining_data" mkdir mining_data
if not exist "recovery_data" mkdir recovery_data
if not exist "exchange_data" mkdir exchange_data
if not exist "governance_data" mkdir governance_data
echo.

REM Create configuration
echo Creating configuration file...
(
echo # XAI Node Configuration
echo XAI_HOST=0.0.0.0
echo XAI_PORT=5000
echo XAI_NETWORK=mainnet
) > config.env
echo.

echo ============================================================
echo INSTALLATION COMPLETE
echo ============================================================
echo.
echo Installation directory: %INSTALL_DIR%
echo.
echo To start the node:
echo   cd %INSTALL_DIR%
echo   venv\Scripts\activate.bat
echo   python core\node.py
echo.
echo To install as Windows service:
echo   Run deploy\install_service.bat as Administrator
echo.
echo ============================================================
echo.
pause
