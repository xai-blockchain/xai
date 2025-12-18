# XAI Blockchain Installers - Complete File Index

Complete reference for all installation files and their purposes.

## Directory Structure

```
installers/
├── debian/                      # Debian package specifications
│   ├── changelog               # Package version history
│   ├── control                 # Package metadata and dependencies
│   ├── copyright               # License information
│   ├── postinst                # Post-installation script
│   ├── rules                   # Build rules (Makefile)
│   └── xai-node.service        # systemd service unit
├── docker-install.sh           # Docker one-click installer
├── .gitignore                  # Git ignore patterns
├── INDEX.md                    # This file
├── INSTALL.md                  # Complete installation guide
├── install-xai.ps1             # Windows PowerShell installer
├── install-xai.sh              # Universal Linux/macOS installer
├── Makefile                    # Build system for all packages
├── QUICKSTART.md               # Quick start guide
├── README.md                   # Installer documentation
├── SUMMARY.md                  # Project summary and metrics
├── verify-installation.sh      # Post-install verification
├── xai.rb                      # Homebrew formula
└── xai.spec                    # RPM package specification
```

**Total:** 20 files across 2 directories

## File Purposes

### Installation Scripts

#### `install-xai.sh` (519 lines)
**Purpose:** Universal installer for Linux and macOS
**Usage:**
```bash
./install-xai.sh              # Standard install
./install-xai.sh --venv       # Virtual environment
./install-xai.sh --dev        # With dev dependencies
```

**Features:**
- OS detection (Ubuntu, Debian, Fedora, CentOS, RHEL, Arch, macOS)
- Python version check (3.10+)
- System dependency installation
- Data directory creation
- Genesis file download
- Shell integration

**Supported Platforms:**
- Ubuntu 20.04, 22.04, 24.04
- Debian 11, 12
- CentOS Stream 8, 9
- Fedora 38, 39, 40
- RHEL 8, 9
- Arch Linux
- macOS 11+

---

#### `install-xai.ps1` (384 lines)
**Purpose:** Windows PowerShell installer
**Usage:**
```powershell
.\install-xai.ps1             # Standard install
.\install-xai.ps1 -Venv       # Virtual environment
.\install-xai.ps1 -Dev        # With dev tools
.\install-xai.ps1 -NoShortcuts # Skip shortcuts
```

**Features:**
- Python detection
- PATH configuration
- Desktop shortcut creation
- Virtual environment support
- Colored output

**Requirements:**
- Windows 10/11
- PowerShell 5.1+ or PowerShell Core
- Python 3.10+

---

#### `docker-install.sh` (409 lines)
**Purpose:** One-liner Docker deployment
**Usage:**
```bash
./docker-install.sh                     # Testnet
./docker-install.sh --mainnet           # Mainnet
./docker-install.sh --mine ADDR         # Enable mining
./docker-install.sh --data-dir /path    # Custom data dir
./docker-install.sh --foreground        # Interactive
```

**Features:**
- Docker verification
- Image pull/build
- Persistent volumes
- Port mapping
- Auto-restart
- Log streaming

**Platforms:** Any OS with Docker

---

### Package Specifications

#### `xai.rb` (156 lines)
**Purpose:** Homebrew formula for macOS
**Usage:**
```bash
brew tap xai-blockchain/tap
brew install xai
brew services start xai
```

**Features:**
- Virtualenv installation
- Dependency management
- Service integration
- Auto-updates

**Platform:** macOS 11+

---

#### `xai.spec` (203 lines)
**Purpose:** RPM package specification
**Usage:**
```bash
rpmbuild -ba xai.spec
sudo rpm -ivh xai-blockchain-0.2.0-1.noarch.rpm
```

**Packages:**
- xai-blockchain (main)
- xai-blockchain-devel (dev tools)
- xai-blockchain-doc (documentation)

**Platforms:** CentOS, Fedora, RHEL

---

#### `debian/control` (94 lines)
**Purpose:** Debian package metadata
**Defines:**
- Package dependencies
- Build dependencies
- Package descriptions
- Relationships

**Packages:**
- xai-blockchain (main)
- xai-blockchain-dev (dev tools)
- xai-blockchain-doc (documentation)

---

#### `debian/rules` (37 lines)
**Purpose:** Debian build rules
**Function:** Makefile for building .deb package
**Used By:** dpkg-buildpackage

---

#### `debian/postinst` (68 lines)
**Purpose:** Post-installation script
**Tasks:**
- Create xai user/group
- Set directory permissions
- Create default config
- Reload systemd
- Display next steps

---

#### `debian/changelog` (19 lines)
**Purpose:** Package version history
**Format:** Debian changelog format
**Tracks:** Version changes and updates

---

#### `debian/copyright` (28 lines)
**Purpose:** License and copyright information
**License:** MIT
**Format:** DEP-5 machine-readable format

---

#### `debian/xai-node.service` (41 lines)
**Purpose:** systemd service unit
**Service:** xai-node daemon
**Features:**
- Auto-restart on failure
- Resource limits
- Security hardening

---

### Build and Automation

#### `Makefile` (287 lines)
**Purpose:** Build system for all packages
**Targets:**

**Build:**
- `make all` - Build everything
- `make debian` - Build .deb package
- `make rpm` - Build .rpm package
- `make docker` - Build Docker image
- `make homebrew` - Validate formula

**Test:**
- `make test` - Test all installers
- `make test-debian` - Test .deb in container
- `make test-rpm` - Test .rpm in container
- `make test-docker` - Test Docker installer
- `make test-script` - Test shell script

**Release:**
- `make checksums` - Generate SHA256
- `make sign` - GPG sign packages
- `make release` - Create release artifacts
- `make github-release` - Upload to GitHub

**Cleanup:**
- `make clean` - Remove build artifacts
- `make distclean` - Complete cleanup

**Usage:**
```bash
make help           # Show all targets
make all            # Build all packages
make test           # Test everything
make release        # Create release
```

---

#### `verify-installation.sh` (399 lines)
**Purpose:** Post-installation verification
**Usage:**
```bash
./verify-installation.sh           # Standard
./verify-installation.sh --verbose # Detailed
```

**Checks:**
- Python version
- XAI commands
- Directories
- Configuration
- Python packages
- System service
- Docker container
- Network connectivity
- Wallet functionality

**Output:** Pass/fail summary with diagnostics

---

### Documentation

#### `INSTALL.md` (647 lines)
**Purpose:** Complete installation guide
**Sections:**
- System requirements
- Installation methods (8 methods)
- Post-installation setup
- Configuration
- Troubleshooting
- Upgrading
- Uninstallation

**Platforms:** All supported platforms

---

#### `QUICKSTART.md` (397 lines)
**Purpose:** 5-minute quick start guide
**Sections:**
- Quick install paths
- First steps
- Common commands
- Configuration
- Troubleshooting
- Network info
- Upgrading

**Target:** New users wanting immediate results

---

#### `README.md` (433 lines)
**Purpose:** Installer documentation
**Sections:**
- Installer overview
- Feature descriptions
- Building packages
- Testing procedures
- CI/CD integration
- Distribution channels
- Troubleshooting

**Target:** Developers and package maintainers

---

#### `SUMMARY.md` (500+ lines)
**Purpose:** Project summary and metrics
**Contents:**
- Complete file list
- Feature descriptions
- Testing matrix
- Distribution channels
- Usage examples
- Metrics and statistics

**Target:** Project overview

---

#### `INDEX.md` (This file)
**Purpose:** Complete file index and reference
**Contents:**
- Directory structure
- File purposes
- Usage examples
- Quick reference

---

### Configuration

#### `.gitignore` (28 lines)
**Purpose:** Git ignore patterns
**Ignores:**
- Build artifacts (*.deb, *.rpm)
- Build directories
- Checksums
- Temporary files

---

## Quick Reference

### Common Tasks

**Install on Linux/macOS:**
```bash
./install-xai.sh
```

**Install on Windows:**
```powershell
.\install-xai.ps1
```

**Install with Docker:**
```bash
./docker-install.sh
```

**Verify Installation:**
```bash
./verify-installation.sh
```

**Build Debian Package:**
```bash
make debian
```

**Build RPM Package:**
```bash
make rpm
```

**Test All Installers:**
```bash
make test
```

**Create Release:**
```bash
make release
```

---

## File Statistics

| Category | Files | Lines |
|----------|-------|-------|
| Installation Scripts | 3 | 1,312 |
| Package Specs | 8 | 687 |
| Documentation | 5 | 2,474 |
| Build/Test | 2 | 686 |
| **Total** | **20** | **~4,750** |

---

## Platform Coverage

| Platform | Installer | Package | Service |
|----------|-----------|---------|---------|
| Ubuntu 20.04+ | install-xai.sh | .deb | systemd |
| Debian 11+ | install-xai.sh | .deb | systemd |
| CentOS Stream | install-xai.sh | .rpm | systemd |
| Fedora 38+ | install-xai.sh | .rpm | systemd |
| RHEL 8+ | install-xai.sh | .rpm | systemd |
| Arch Linux | install-xai.sh | - | manual |
| macOS 11+ | install-xai.sh | .rb | launchd |
| Windows 10+ | install-xai.ps1 | - | manual |
| Docker | docker-install.sh | image | container |

**Total:** 9+ platforms with native support

---

## Installation Methods

1. **One-Click Script** - Linux/macOS automated
2. **PowerShell** - Windows automated
3. **Docker** - Containerized deployment
4. **Homebrew** - macOS package manager
5. **APT** - Debian/Ubuntu package manager
6. **YUM/DNF** - CentOS/Fedora/RHEL package manager
7. **pip** - Python package manager
8. **Source** - Manual build

---

## Distribution Checklist

- [x] Linux/macOS installer script
- [x] Windows PowerShell installer
- [x] Docker one-liner
- [x] Homebrew formula
- [x] Debian package (.deb)
- [x] RPM package (.rpm)
- [x] Build automation (Makefile)
- [x] Verification script
- [x] Complete documentation
- [x] Quick start guide
- [x] Troubleshooting guide
- [x] Testing procedures

**Status:** All items complete

---

## Support

- **Installation Help:** See [INSTALL.md](INSTALL.md)
- **Quick Start:** See [QUICKSTART.md](QUICKSTART.md)
- **Build Help:** See [README.md](README.md)
- **Verification:** Run `verify-installation.sh`

---

## License

All installer files are released under the MIT License.
See [../LICENSE](../LICENSE) for full text.

---

**Last Updated:** December 18, 2024
**Version:** 0.2.0
**Status:** Production Ready
