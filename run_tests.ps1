# Crypto Project - Run Python Tests
# This script ensures Python is correctly located and runs pytest

$ErrorActionPreference = "Stop"

Write-Host "Crypto Project - Running Python Tests" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

# Define Python paths
$python314 = "C:\Users\decri\AppData\Local\Programs\Python\Python314\python.exe"
$python313 = "C:\Users\decri\AppData\Local\Programs\Python\Python313\python.exe"

# Check which Python is available
$pythonExe = $null
if (Test-Path $python314) {
    $pythonExe = $python314
    Write-Host "Using Python 3.14" -ForegroundColor Green
} elseif (Test-Path $python313) {
    $pythonExe = $python313
    Write-Host "Using Python 3.13" -ForegroundColor Green
} else {
    Write-Host "ERROR: Python not found at expected locations" -ForegroundColor Red
    exit 1
}

# Change to Crypto directory
Set-Location "C:\Users\decri\GitClones\Crypto"

# Show Python version
Write-Host "`nPython version:" -ForegroundColor Cyan
& $pythonExe --version

# Run pytest
Write-Host "`nRunning pytest..." -ForegroundColor Cyan
& $pythonExe -m pytest $args

Write-Host "`nDone!" -ForegroundColor Green
