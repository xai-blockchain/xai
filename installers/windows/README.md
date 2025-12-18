# Windows Installer for XAI Blockchain

This directory contains configuration files for building Windows installers (.exe) for XAI Blockchain.

## Overview

Two installer systems are provided:

1. **Inno Setup** (`setup.iss`) - Recommended, modern UI
2. **NSIS** (`xai-nsis.nsi`) - Alternative, more customizable

Both create self-contained installers with embedded Python distribution.

## Prerequisites

### For Inno Setup
- [Inno Setup 6.2+](https://jrsoftware.org/isinfo.php)
- Windows 10 or later
- Python 3.12.1 embedded distribution
- Built XAI package

### For NSIS
- [NSIS 3.08+](https://nsis.sourceforge.io/)
- EnVar plugin for PATH modification
- Windows 10 or later
- Python 3.12.1 embedded distribution
- Built XAI package

## Building the Installer

### Step 1: Prepare Python Embedded Distribution

Download Python embeddable package:
```powershell
# Download Python 3.12.1 embedded
$url = "https://www.python.org/ftp/python/3.12.1/python-3.12.1-embed-amd64.zip"
Invoke-WebRequest -Uri $url -OutFile "python-3.12.1-embed-amd64.zip"
Expand-Archive -Path "python-3.12.1-embed-amd64.zip" -DestinationPath "python-3.12.1-embed-amd64"

# Enable pip by uncommenting import site in python312._pth
(Get-Content "python-3.12.1-embed-amd64\python312._pth") -replace '#import site', 'import site' | Set-Content "python-3.12.1-embed-amd64\python312._pth"

# Download get-pip.py and install pip
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
.\python-3.12.1-embed-amd64\python.exe get-pip.py
```

### Step 2: Build XAI Package

```powershell
# From XAI root directory
cd ..\..
python -m build

# Create dist directory structure
New-Item -ItemType Directory -Force -Path "installers\windows\dist\xai"
Copy-Item -Recurse -Force "src\xai\*" "installers\windows\dist\xai\"
Copy-Item "pyproject.toml" "installers\windows\dist\xai\"
```

### Step 3: Prepare Configuration Files

```powershell
# Copy genesis file
Copy-Item "src\xai\genesis_testnet.json" "installers\windows\genesis.json"

# Create config directory (optional)
New-Item -ItemType Directory -Force -Path "installers\windows\config"
```

### Step 4: Build Installer with Inno Setup

```powershell
# Using Inno Setup GUI
# 1. Open Inno Setup Compiler
# 2. File -> Open -> setup.iss
# 3. Build -> Compile
# Output: installers\windows\output\xai-blockchain-0.2.0-setup.exe

# Using command line
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

### Step 5: Build Installer with NSIS (Alternative)

```powershell
# Using NSIS GUI
# 1. Right-click xai-nsis.nsi
# 2. Select "Compile NSIS Script"
# Output: installers\windows\output\xai-blockchain-0.2.0-installer.exe

# Using command line
"C:\Program Files (x86)\NSIS\makensis.exe" xai-nsis.nsi
```

## Installer Features

### Inno Setup Installer
- Modern wizard-style interface
- Custom installation directory
- Component selection
- Start Menu integration
- Desktop shortcuts (optional)
- PATH modification (optional)
- Auto-start on boot (optional)
- Automatic Python setup
- Clean uninstallation
- Preserves user data on uninstall (with confirmation)

### NSIS Installer
- Lightweight and fast
- Full customization options
- Multiple language support ready
- Component-based installation
- Registry integration
- Process termination on uninstall
- Detailed installation logging

## Installation Components

Both installers include:

1. **Core Files** (Required)
   - Python 3.12.1 embedded runtime
   - XAI Python package
   - All dependencies
   - Launcher batch scripts

2. **Start Menu Shortcuts**
   - XAI Node
   - XAI Wallet
   - XAI Console
   - Documentation
   - Uninstaller

3. **Desktop Shortcuts** (Optional)
   - Quick access to XAI Node

4. **PATH Integration** (Optional)
   - Adds XAI executables to system PATH
   - Allows running `xai-node`, `xai-wallet`, `xai-cli` from any terminal

5. **Auto-start** (Optional)
   - Starts XAI Node on Windows startup

## Launcher Scripts

### xai-node.bat
Starts the XAI blockchain node with:
- Automatic data directory creation
- Environment variable setup
- Error handling and logging
- Startup banner

### xai-wallet.bat
Launches the XAI wallet manager with:
- Wallet directory management
- Secure environment setup
- Interactive CLI interface

### xai-cli.bat
Command-line interface launcher with:
- Full CLI functionality
- Tool integration
- Developer utilities

## Data Locations

After installation:

- **Installation**: `C:\Program Files\XAI\`
- **Data**: `%APPDATA%\XAI\`
- **Blockchain**: `%APPDATA%\XAI\blockchain\`
- **Wallets**: `%APPDATA%\XAI\wallets\`
- **Config**: `%APPDATA%\XAI\config\`
- **Logs**: `%APPDATA%\XAI\logs\`

## Testing the Installer

### Manual Testing
```powershell
# Install
.\output\xai-blockchain-0.2.0-setup.exe /VERYSILENT /NORESTART

# Verify installation
& "C:\Program Files\XAI\xai-node.bat" --version
& "C:\Program Files\XAI\xai-wallet.bat" --help

# Uninstall
& "C:\Program Files\XAI\uninst.exe" /VERYSILENT /NORESTART
```

### Automated Testing Script
```powershell
# test-installer.ps1
$installer = ".\output\xai-blockchain-0.2.0-setup.exe"
$installPath = "C:\Program Files\XAI"

# Silent install
Start-Process -FilePath $installer -ArgumentList "/VERYSILENT","/NORESTART" -Wait

# Test executables
$tests = @(
    "xai-node.bat --version",
    "xai-wallet.bat --help",
    "xai-cli.bat --help"
)

foreach ($test in $tests) {
    $cmd = Join-Path $installPath $test.Split()[0]
    $result = & $cmd $test.Split()[1]
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ $test passed" -ForegroundColor Green
    } else {
        Write-Host "✗ $test failed" -ForegroundColor Red
    }
}

# Silent uninstall
Start-Process -FilePath "$installPath\uninst.exe" -ArgumentList "/VERYSILENT","/NORESTART" -Wait
```

## Code Signing (Optional)

Sign the installer for production:

```powershell
# Using signtool.exe from Windows SDK
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com output\xai-blockchain-0.2.0-setup.exe

# Using DigiCert certificate
signtool sign /sha1 THUMBPRINT /tr http://timestamp.digicert.com /td sha256 /fd sha256 output\xai-blockchain-0.2.0-setup.exe
```

## Distribution

### Checksum Generation
```powershell
# SHA256
Get-FileHash output\xai-blockchain-0.2.0-setup.exe -Algorithm SHA256 | Format-List

# Save to file
Get-FileHash output\xai-blockchain-0.2.0-setup.exe -Algorithm SHA256 | Select-Object Hash | Out-File output\xai-blockchain-0.2.0-setup.exe.sha256
```

### Upload to GitHub Releases
```powershell
# Using GitHub CLI
gh release create v0.2.0 `
  output\xai-blockchain-0.2.0-setup.exe `
  output\xai-blockchain-0.2.0-setup.exe.sha256 `
  --title "XAI Blockchain v0.2.0" `
  --notes "Windows installer for XAI Blockchain"
```

## Troubleshooting

### Python Not Found
- Ensure Python embedded distribution is in correct location
- Verify `python312._pth` has `import site` uncommented
- Check `python.exe` exists in `python-3.12.1-embed-amd64\`

### Build Fails
- Verify all file paths in .iss or .nsi are correct
- Check that dist\xai directory exists and has content
- Ensure launcher .bat files are present

### Installation Fails
- Run installer as Administrator
- Check Windows Event Viewer for errors
- Try with `/LOG="install.log"` parameter for Inno Setup

### Node Won't Start
- Check `%APPDATA%\XAI\logs\` for error messages
- Verify Python packages installed: `python -m pip list`
- Run `xai-node.bat` from command prompt to see errors

## Building from CI/CD

Example GitHub Actions workflow:

```yaml
name: Build Windows Installer

on:
  release:
    types: [created]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Download Python
        run: |
          Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.1/python-3.12.1-embed-amd64.zip" -OutFile "python.zip"
          Expand-Archive python.zip -DestinationPath installers/windows/python-3.12.1-embed-amd64

      - name: Install Inno Setup
        run: choco install innosetup -y

      - name: Build Package
        run: python -m build

      - name: Prepare Dist
        run: |
          New-Item -ItemType Directory -Force installers/windows/dist/xai
          Copy-Item -Recurse src/xai/* installers/windows/dist/xai/

      - name: Build Installer
        run: |
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installers/windows/setup.iss

      - name: Upload Release Asset
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./installers/windows/output/xai-blockchain-0.2.0-setup.exe
          asset_name: xai-blockchain-0.2.0-setup.exe
          asset_content_type: application/octet-stream
```

## License

MIT License - See LICENSE file for details
