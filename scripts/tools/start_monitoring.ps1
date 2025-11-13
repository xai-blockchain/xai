# AIXN Blockchain - Start Monitoring Stack (PowerShell)
# Starts Prometheus, Grafana, and Alertmanager using Docker Compose

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PrometheusDir = Join-Path $ScriptDir "..\..\prometheus"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AIXN Blockchain - Monitoring Stack" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker is not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://www.docker.com/get-started"
    exit 1
}

# Check if Docker is running
try {
    docker ps | Out-Null
} catch {
    Write-Host "Error: Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop"
    exit 1
}

# Navigate to prometheus directory
Set-Location $PrometheusDir

Write-Host "Starting monitoring stack..." -ForegroundColor Yellow
Write-Host ""

# Start containers
try {
    docker compose up -d
} catch {
    # Try old docker-compose syntax
    docker-compose up -d
}

Write-Host ""
Write-Host "✓ Monitoring stack started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:" -ForegroundColor Cyan
Write-Host "  Prometheus:    http://localhost:9090"
Write-Host "  Grafana:       http://localhost:3000 (admin/admin)"
Write-Host "  Alertmanager:  http://localhost:9093"
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Cyan
Write-Host "  docker compose logs -f"
Write-Host ""
Write-Host "To stop:" -ForegroundColor Cyan
Write-Host "  docker compose down"
Write-Host ""

# Open Grafana in browser (optional)
$OpenBrowser = Read-Host "Open Grafana in browser? (Y/N)"
if ($OpenBrowser -eq "Y" -or $OpenBrowser -eq "y") {
    Start-Process "http://localhost:3000"
}
