<#
.SYNOPSIS
    XAI Blockchain - Windows PowerShell Installer

.DESCRIPTION
    One-click installation script for XAI blockchain node and tools on Windows.
    Installs Python dependencies, creates shortcuts, and configures the environment.

.PARAMETER Venv
    Install in a virtual environment (recommended for isolation)

.PARAMETER Dev
    Install with development dependencies

.PARAMETER NoShortcuts
    Skip creating desktop shortcuts

.EXAMPLE
    .\install-xai.ps1
    Standard installation

.EXAMPLE
    .\install-xai.ps1 -Venv
    Install in virtual environment

.EXAMPLE
    .\install-xai.ps1 -Dev
    Install with development tools
#>

[CmdletBinding()]
param(
    [switch]$Venv,
    [switch]$Dev,
    [switch]$NoShortcuts
)

# ============================================================================
# Configuration
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$XAI_VERSION = "0.2.0"
$XAI_DATA_DIR = Join-Path $env:USERPROFILE ".xai"
$XAI_CONFIG_DIR = Join-Path $XAI_DATA_DIR "config"
$XAI_LOG_DIR = Join-Path $XAI_DATA_DIR "logs"
$MIN_PYTHON_VERSION = [version]"3.10.0"
$GENESIS_URL = "https://raw.githubusercontent.com/xai-blockchain/xai/main/genesis.json"

# ============================================================================
# Utility Functions
# ============================================================================

function Write-Header {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  XAI Blockchain Installer v$XAI_VERSION" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Test-Administrator {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Command {
    param([string]$Command)
    try {
        if (Get-Command $Command -ErrorAction SilentlyContinue) {
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

# ============================================================================
# Python Verification
# ============================================================================

function Test-Python {
    Write-Info "Checking Python installation..."

    $pythonCommands = @("python", "python3", "py")
    $pythonPath = $null
    $pythonVersion = $null

    foreach ($cmd in $pythonCommands) {
        if (Test-Command $cmd) {
            try {
                $versionOutput = & $cmd --version 2>&1 | Out-String
                if ($versionOutput -match "Python (\d+\.\d+\.\d+)") {
                    $version = [version]$matches[1]
                    if ($version -ge $MIN_PYTHON_VERSION) {
                        $pythonPath = (Get-Command $cmd).Source
                        $pythonVersion = $version
                        $global:PYTHON_CMD = $cmd
                        Write-Success "Found Python $version at $pythonPath"
                        return $true
                    }
                }
            }
            catch {
                continue
            }
        }
    }

    Write-Error "Python $MIN_PYTHON_VERSION or higher is required but not found"
    Write-Info "Please install Python from https://www.python.org/downloads/"
    Write-Info "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

# ============================================================================
# Installation
# ============================================================================

function New-Directories {
    Write-Info "Creating XAI directories..."

    $directories = @(
        $XAI_DATA_DIR,
        (Join-Path $XAI_DATA_DIR "blockchain"),
        (Join-Path $XAI_DATA_DIR "wallets"),
        (Join-Path $XAI_DATA_DIR "state"),
        $XAI_CONFIG_DIR,
        $XAI_LOG_DIR
    )

    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }

    Write-Success "Created directories in $XAI_DATA_DIR"
}

function Install-XAIVenv {
    Write-Info "Installing XAI in virtual environment..."

    $venvDir = Join-Path $XAI_DATA_DIR "venv"

    # Create virtual environment
    & $global:PYTHON_CMD -m venv $venvDir

    # Activate virtual environment
    $activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
    . $activateScript

    # Upgrade pip
    python -m pip install --quiet --upgrade pip setuptools wheel

    # Install XAI
    if ($Dev) {
        python -m pip install --quiet "xai-blockchain[dev]==$XAI_VERSION"
    }
    else {
        python -m pip install --quiet "xai-blockchain==$XAI_VERSION"
    }

    Write-Success "XAI installed in virtual environment"

    # Create activation script
    $activateScriptPath = Join-Path $XAI_DATA_DIR "activate.ps1"
    @"
# XAI virtual environment activation
& "$venvDir\Scripts\Activate.ps1"
Write-Host "XAI environment activated ($XAI_VERSION)" -ForegroundColor Green
Write-Host "Run 'xai --help' to get started" -ForegroundColor Cyan
"@ | Out-File -FilePath $activateScriptPath -Encoding UTF8

    Write-Info "To activate XAI: . $activateScriptPath"
}

function Install-XAISystem {
    Write-Info "Installing XAI system-wide..."

    # Install with pip
    if ($Dev) {
        & $global:PYTHON_CMD -m pip install --user --quiet "xai-blockchain[dev]==$XAI_VERSION"
    }
    else {
        & $global:PYTHON_CMD -m pip install --user --quiet "xai-blockchain==$XAI_VERSION"
    }

    Write-Success "XAI installed system-wide"

    # Add Python Scripts to PATH if not already there
    $pythonScripts = Join-Path ([System.IO.Path]::GetDirectoryName((Get-Command $global:PYTHON_CMD).Source)) "Scripts"
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")

    if ($userPath -notlike "*$pythonScripts*") {
        Write-Info "Adding Python Scripts to PATH..."
        [Environment]::SetEnvironmentVariable(
            "Path",
            "$userPath;$pythonScripts",
            "User"
        )
        $env:Path = "$env:Path;$pythonScripts"
        Write-Success "Added to PATH (restart shell to take effect)"
    }
}

# ============================================================================
# Configuration
# ============================================================================

function Get-Genesis {
    Write-Info "Downloading genesis file..."

    $genesisPath = Join-Path $XAI_CONFIG_DIR "genesis.json"

    try {
        Invoke-WebRequest -Uri $GENESIS_URL -OutFile $genesisPath -UseBasicParsing -ErrorAction Stop
        Write-Success "Genesis file downloaded"
    }
    catch {
        Write-Warning "Could not download genesis file, creating default configuration"
        @"
{
  "chain_id": "xai-testnet-1",
  "genesis_time": "2025-01-01T00:00:00Z",
  "initial_difficulty": 4,
  "max_supply": 121000000,
  "block_time": 120,
  "network_id": "0xABCD"
}
"@ | Out-File -FilePath $genesisPath -Encoding UTF8
        Write-Success "Created default genesis configuration"
    }
}

function New-Config {
    Write-Info "Creating default configuration..."

    $configPath = Join-Path $XAI_CONFIG_DIR "node.yaml"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    @"
# XAI Node Configuration
# Generated by installer on $timestamp

network:
  name: testnet
  port: 18545
  rpc_port: 18546

data:
  dir: $($XAI_DATA_DIR -replace '\\', '/')/blockchain
  wallets_dir: $($XAI_DATA_DIR -replace '\\', '/')/wallets
  state_dir: $($XAI_DATA_DIR -replace '\\', '/')/state

logging:
  level: INFO
  dir: $($XAI_LOG_DIR -replace '\\', '/')

node:
  enable_mining: false
  max_peers: 50
  checkpoint_sync: true
"@ | Out-File -FilePath $configPath -Encoding UTF8

    Write-Success "Created node configuration"
}

# ============================================================================
# Shortcuts
# ============================================================================

function New-Shortcuts {
    Write-Info "Creating desktop shortcuts..."

    $desktop = [Environment]::GetFolderPath("Desktop")
    $shell = New-Object -ComObject WScript.Shell

    # XAI Node shortcut
    try {
        $shortcut = $shell.CreateShortcut((Join-Path $desktop "XAI Node.lnk"))
        $shortcut.TargetPath = "powershell.exe"
        $shortcut.Arguments = "-NoExit -Command `"xai-node --network testnet`""
        $shortcut.WorkingDirectory = $XAI_DATA_DIR
        $shortcut.Description = "Start XAI Blockchain Node"
        $shortcut.Save()
        Write-Success "Created XAI Node shortcut"
    }
    catch {
        Write-Warning "Could not create node shortcut: $_"
    }

    # XAI Wallet shortcut
    try {
        $shortcut = $shell.CreateShortcut((Join-Path $desktop "XAI Wallet.lnk"))
        $shortcut.TargetPath = "powershell.exe"
        $shortcut.Arguments = "-NoExit -Command `"xai-wallet --help`""
        $shortcut.WorkingDirectory = $XAI_DATA_DIR
        $shortcut.Description = "XAI Wallet CLI"
        $shortcut.Save()
        Write-Success "Created XAI Wallet shortcut"
    }
    catch {
        Write-Warning "Could not create wallet shortcut: $_"
    }
}

# ============================================================================
# Verification
# ============================================================================

function Test-Installation {
    Write-Info "Verifying installation..."

    if ($Venv) {
        $activateScript = Join-Path $XAI_DATA_DIR "venv\Scripts\Activate.ps1"
        . $activateScript
    }

    # Test commands
    $commands = @("xai", "xai-node", "xai-wallet")
    $allFound = $true

    foreach ($cmd in $commands) {
        if (Test-Command $cmd) {
            Write-Success "$cmd installed"
        }
        else {
            Write-Warning "$cmd not found in PATH"
            $allFound = $false
        }
    }

    if (-not $allFound) {
        Write-Warning "Some commands not found. You may need to restart your shell."
    }
}

# ============================================================================
# Post-Installation
# ============================================================================

function Show-NextSteps {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host ""

    if ($Venv) {
        Write-Host "  1. Activate XAI environment:" -ForegroundColor White
        Write-Host "     . $(Join-Path $XAI_DATA_DIR 'activate.ps1')" -ForegroundColor Yellow
        Write-Host ""
    }
    else {
        Write-Host "  1. Restart PowerShell to refresh PATH" -ForegroundColor White
        Write-Host ""
    }

    Write-Host "  2. Generate a wallet:" -ForegroundColor White
    Write-Host "     xai-wallet generate-address" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. Start a node:" -ForegroundColor White
    Write-Host "     xai-node --network testnet" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  4. Get test coins:" -ForegroundColor White
    Write-Host "     xai-wallet request-faucet --address YOUR_ADDRESS" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Documentation:" -ForegroundColor Cyan
    Write-Host "  • Node configuration: $XAI_CONFIG_DIR\node.yaml"
    Write-Host "  • Data directory: $XAI_DATA_DIR"
    Write-Host "  • Logs: $XAI_LOG_DIR"
    Write-Host "  • Online docs: https://docs.xai-blockchain.io"
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Cyan
    Write-Host "  xai --help          Show all available commands"
    Write-Host "  xai-node --help     Node management options"
    Write-Host "  xai-wallet --help   Wallet operations"
    Write-Host ""
}

# ============================================================================
# Main Installation Flow
# ============================================================================

function Main {
    Write-Header

    # System checks
    Test-Python

    # Installation
    New-Directories

    if ($Venv) {
        Install-XAIVenv
    }
    else {
        Install-XAISystem
    }

    # Configuration
    Get-Genesis
    New-Config

    # Shortcuts
    if (-not $NoShortcuts) {
        New-Shortcuts
    }

    # Verification
    Test-Installation

    # Complete
    Show-NextSteps
}

# Run installer
try {
    Main
}
catch {
    Write-Error "Installation failed: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}
