@echo off
echo ============================================
echo XAI P2P Exchange - Frontend Quick Start
echo ============================================
echo.
echo Starting local web server on port 8080...
echo.
echo Open your browser and navigate to:
echo http://localhost:8080
echo.
echo To test the connection first, go to:
echo http://localhost:8080/test.html
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================
echo.

REM Try Python 3
python -m http.server 8080 2>nul

REM If Python fails, show error message
if errorlevel 1 (
    echo.
    echo ERROR: Python not found!
    echo.
    echo Please install Python or open index.html directly in your browser.
    echo.
    pause
)
