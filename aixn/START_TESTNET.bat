@echo off
echo ============================================================
echo XAI BLOCKCHAIN - LOCAL TESTNET LAUNCHER
echo ============================================================
echo.
echo This will start:
echo   1. Testnet Node (localhost:5000)
echo   2. Block Explorer (localhost:3000)
echo   3. Testing Dashboard (localhost:3000/dashboard)
echo.
echo Press Ctrl+C in any window to stop that service
echo ============================================================
echo.

REM Check if genesis block exists
if not exist "genesis_testnet.json" (
    echo [STEP 1/3] Generating testnet genesis block...
    echo.
    python generate_premine.py
    echo.
    echo Genesis block created!
    echo.
    pause
) else (
    echo [INFO] Genesis block already exists
    echo.
)

echo [STEP 2/3] Starting blockchain node on port 5000...
echo.
start "XAI Node" cmd /k "python core/node.py"
timeout /t 3 /nobreak >nul

echo [STEP 3/3] Starting block explorer on port 3000...
echo.
start "XAI Explorer" cmd /k "python explorer.py"
timeout /t 2 /nobreak >nul

echo.
echo ============================================================
echo XAI BLOCKCHAIN TESTNET RUNNING
echo ============================================================
echo.
echo Node API:        http://localhost:5000
echo Block Explorer:  http://localhost:3000
echo Test Dashboard:  http://localhost:3000/dashboard
echo.
echo Opening dashboard in browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000/dashboard
echo.
echo ============================================================
echo.
echo Services are running in separate windows.
echo Close those windows or press Ctrl+C to stop services.
echo.
pause
