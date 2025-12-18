#!/usr/bin/env bash
# ============================================================================
# XAI Blockchain - Universal Linux/macOS Installer
# ============================================================================
# One-click installation script for XAI blockchain node and tools
# Supports: Ubuntu/Debian, CentOS/RHEL/Fedora, Arch Linux, macOS
#
# Usage:
#   curl -fsSL https://install.xai-blockchain.io/install.sh | bash
#   ./install-xai.sh
#   ./install-xai.sh --venv     # Install in virtual environment
#   ./install-xai.sh --dev      # Install with dev dependencies
# ============================================================================

set -e
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
XAI_VERSION="0.2.0"
XAI_DATA_DIR="${HOME}/.xai"
XAI_CONFIG_DIR="${XAI_DATA_DIR}/config"
XAI_LOG_DIR="${XAI_DATA_DIR}/logs"
MIN_PYTHON_VERSION="3.10"
USE_VENV=false
INSTALL_DEV=false
GENESIS_URL="https://raw.githubusercontent.com/xai-blockchain/xai/main/genesis.json"

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  XAI Blockchain Installer v${XAI_VERSION}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

version_compare() {
    # Compare two version strings (e.g., "3.10" vs "3.11")
    printf '%s\n%s' "$1" "$2" | sort -V | head -n1
}

# ============================================================================
# System Detection
# ============================================================================

detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    elif [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS="linux"
        DISTRO="${ID}"
    else
        OS="unknown"
        DISTRO="unknown"
    fi

    print_info "Detected OS: ${OS} (${DISTRO})"
}

# ============================================================================
# Python Verification
# ============================================================================

check_python() {
    print_info "Checking Python installation..."

    # Try different Python commands
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if check_command "$cmd"; then
            PYTHON_CMD="$cmd"
            PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')

            # Extract major.minor version
            PYTHON_MAJOR_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f1,2)

            # Check if version meets minimum requirement
            if [[ "$(version_compare "$PYTHON_MAJOR_MINOR" "$MIN_PYTHON_VERSION")" == "$MIN_PYTHON_VERSION" ]]; then
                print_success "Found Python ${PYTHON_VERSION} at $(command -v "$cmd")"
                return 0
            fi
        fi
    done

    print_error "Python ${MIN_PYTHON_VERSION}+ is required but not found"
    print_info "Please install Python ${MIN_PYTHON_VERSION} or higher and try again"

    # Provide OS-specific installation instructions
    case "$DISTRO" in
        ubuntu|debian)
            echo "  sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip"
            ;;
        fedora|rhel|centos)
            echo "  sudo dnf install -y python3.12 python3-pip"
            ;;
        arch|manjaro)
            echo "  sudo pacman -S python python-pip"
            ;;
        macos)
            echo "  brew install python@3.12"
            ;;
    esac

    exit 1
}

# ============================================================================
# Dependency Installation
# ============================================================================

install_system_dependencies() {
    print_info "Installing system dependencies..."

    case "$DISTRO" in
        ubuntu|debian)
            if ! check_command sudo; then
                print_error "sudo is required but not found. Please run as root or install sudo."
                exit 1
            fi

            sudo apt-get update -qq
            sudo apt-get install -y -qq \
                build-essential \
                libssl-dev \
                libffi-dev \
                python3-dev \
                pkg-config \
                libsecp256k1-dev \
                libgmp-dev \
                git \
                curl \
                ca-certificates
            print_success "System dependencies installed"
            ;;

        fedora|rhel|centos)
            sudo dnf install -y \
                gcc \
                gcc-c++ \
                make \
                openssl-devel \
                libffi-devel \
                python3-devel \
                libsecp256k1-devel \
                gmp-devel \
                git \
                curl \
                ca-certificates
            print_success "System dependencies installed"
            ;;

        arch|manjaro)
            sudo pacman -S --noconfirm \
                base-devel \
                openssl \
                libffi \
                python \
                libsecp256k1 \
                gmp \
                git \
                curl \
                ca-certificates
            print_success "System dependencies installed"
            ;;

        macos)
            if ! check_command brew; then
                print_error "Homebrew is required on macOS. Install from https://brew.sh"
                exit 1
            fi

            brew install \
                openssl \
                libffi \
                libsecp256k1 \
                gmp \
                git \
                curl
            print_success "System dependencies installed"
            ;;

        *)
            print_warning "Unknown distribution. Skipping system dependency installation."
            print_warning "Please ensure you have: gcc, make, openssl-dev, libffi-dev, libsecp256k1-dev, gmp-dev"
            ;;
    esac
}

# ============================================================================
# XAI Installation
# ============================================================================

create_directories() {
    print_info "Creating XAI directories..."

    mkdir -p "${XAI_DATA_DIR}"/{blockchain,wallets,state}
    mkdir -p "${XAI_CONFIG_DIR}"
    mkdir -p "${XAI_LOG_DIR}"

    print_success "Created directories in ${XAI_DATA_DIR}"
}

install_xai_venv() {
    print_info "Installing XAI in virtual environment..."

    VENV_DIR="${XAI_DATA_DIR}/venv"

    # Create virtual environment
    $PYTHON_CMD -m venv "$VENV_DIR"

    # Activate virtual environment
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

    # Upgrade pip
    pip install --quiet --upgrade pip setuptools wheel

    # Install XAI
    if [[ "$INSTALL_DEV" == true ]]; then
        pip install --quiet "xai-blockchain[dev]==${XAI_VERSION}"
    else
        pip install --quiet "xai-blockchain==${XAI_VERSION}"
    fi

    print_success "XAI installed in virtual environment"

    # Create activation wrapper
    cat > "${XAI_DATA_DIR}/activate" <<EOF
#!/usr/bin/env bash
# XAI virtual environment activation
source "${VENV_DIR}/bin/activate"
echo "XAI environment activated (${XAI_VERSION})"
echo "Run 'xai --help' to get started"
EOF
    chmod +x "${XAI_DATA_DIR}/activate"

    print_info "To activate XAI environment: source ${XAI_DATA_DIR}/activate"
}

install_xai_system() {
    print_info "Installing XAI system-wide..."

    # Install with pip
    if [[ "$INSTALL_DEV" == true ]]; then
        $PYTHON_CMD -m pip install --user --quiet "xai-blockchain[dev]==${XAI_VERSION}"
    else
        $PYTHON_CMD -m pip install --user --quiet "xai-blockchain==${XAI_VERSION}"
    fi

    print_success "XAI installed system-wide"
}

# ============================================================================
# Configuration Setup
# ============================================================================

download_genesis() {
    print_info "Downloading genesis file..."

    # Try to download genesis file
    if check_command curl; then
        if curl -fsSL "${GENESIS_URL}" -o "${XAI_CONFIG_DIR}/genesis.json" 2>/dev/null; then
            print_success "Genesis file downloaded"
            return 0
        fi
    elif check_command wget; then
        if wget -q "${GENESIS_URL}" -O "${XAI_CONFIG_DIR}/genesis.json" 2>/dev/null; then
            print_success "Genesis file downloaded"
            return 0
        fi
    fi

    # Create default genesis if download fails
    print_warning "Could not download genesis file, creating default configuration"
    cat > "${XAI_CONFIG_DIR}/genesis.json" <<'EOF'
{
  "chain_id": "xai-testnet-1",
  "genesis_time": "2025-01-01T00:00:00Z",
  "initial_difficulty": 4,
  "max_supply": 121000000,
  "block_time": 120,
  "network_id": "0xABCD"
}
EOF
    print_success "Created default genesis configuration"
}

create_config() {
    print_info "Creating default configuration..."

    cat > "${XAI_CONFIG_DIR}/node.yaml" <<EOF
# XAI Node Configuration
# Generated by installer on $(date)

network:
  name: testnet
  port: 18545
  rpc_port: 18546

data:
  dir: ${XAI_DATA_DIR}/blockchain
  wallets_dir: ${XAI_DATA_DIR}/wallets
  state_dir: ${XAI_DATA_DIR}/state

logging:
  level: INFO
  dir: ${XAI_LOG_DIR}

node:
  enable_mining: false
  max_peers: 50
  checkpoint_sync: true
EOF

    print_success "Created node configuration"
}

setup_shell_integration() {
    print_info "Setting up shell integration..."

    # Detect shell
    SHELL_RC=""
    if [[ -n "$BASH_VERSION" ]]; then
        SHELL_RC="${HOME}/.bashrc"
    elif [[ -n "$ZSH_VERSION" ]]; then
        SHELL_RC="${HOME}/.zshrc"
    fi

    if [[ -n "$SHELL_RC" ]] && [[ -f "$SHELL_RC" ]]; then
        # Add XAI to PATH if not in venv
        if [[ "$USE_VENV" == false ]]; then
            if ! grep -q "# XAI Blockchain" "$SHELL_RC"; then
                cat >> "$SHELL_RC" <<EOF

# XAI Blockchain
export XAI_DATA_DIR="${XAI_DATA_DIR}"
export PATH="\$HOME/.local/bin:\$PATH"

# XAI aliases
alias xai-node='xai-node'
alias xai-wallet='xai-wallet'
alias xai-start='xai-node --network testnet'
EOF
                print_success "Added XAI to ${SHELL_RC}"
            else
                print_info "XAI already configured in ${SHELL_RC}"
            fi
        fi
    fi
}

# ============================================================================
# Post-Installation
# ============================================================================

verify_installation() {
    print_info "Verifying installation..."

    if [[ "$USE_VENV" == true ]]; then
        # shellcheck disable=SC1091
        source "${XAI_DATA_DIR}/venv/bin/activate"
    fi

    # Check if xai commands are available
    if check_command xai; then
        XAI_INSTALLED_VERSION=$(xai --version 2>/dev/null | awk '{print $NF}' || echo "unknown")
        print_success "XAI CLI installed (version: ${XAI_INSTALLED_VERSION})"
    else
        print_warning "XAI CLI not found in PATH"
    fi

    if check_command xai-node; then
        print_success "XAI Node installed"
    else
        print_warning "XAI Node not found in PATH"
    fi

    if check_command xai-wallet; then
        print_success "XAI Wallet installed"
    else
        print_warning "XAI Wallet not found in PATH"
    fi
}

print_next_steps() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo ""

    if [[ "$USE_VENV" == true ]]; then
        echo -e "  1. Activate XAI environment:"
        echo -e "     ${YELLOW}source ${XAI_DATA_DIR}/activate${NC}"
        echo ""
    else
        echo -e "  1. Restart your shell or run:"
        echo -e "     ${YELLOW}source ~/.bashrc${NC}  # or ~/.zshrc"
        echo ""
    fi

    echo -e "  2. Generate a wallet:"
    echo -e "     ${YELLOW}xai-wallet generate-address${NC}"
    echo ""
    echo -e "  3. Start a node:"
    echo -e "     ${YELLOW}xai-node --network testnet${NC}"
    echo ""
    echo -e "  4. Get test coins:"
    echo -e "     ${YELLOW}xai-wallet request-faucet --address YOUR_ADDRESS${NC}"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo -e "  • Node configuration: ${XAI_CONFIG_DIR}/node.yaml"
    echo -e "  • Data directory: ${XAI_DATA_DIR}"
    echo -e "  • Logs: ${XAI_LOG_DIR}"
    echo -e "  • Online docs: https://docs.xai-blockchain.io"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  xai --help          Show all available commands"
    echo -e "  xai-node --help     Node management options"
    echo -e "  xai-wallet --help   Wallet operations"
    echo ""
}

# ============================================================================
# Main Installation Flow
# ============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --venv)
                USE_VENV=true
                shift
                ;;
            --dev)
                INSTALL_DEV=true
                shift
                ;;
            --help|-h)
                echo "XAI Blockchain Installer"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --venv    Install in virtual environment (isolated)"
                echo "  --dev     Install with development dependencies"
                echo "  --help    Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Run '$0 --help' for usage information"
                exit 1
                ;;
        esac
    done
}

main() {
    parse_args "$@"

    print_header
    echo ""

    # System checks
    detect_os
    check_python

    # Installation
    install_system_dependencies
    create_directories

    if [[ "$USE_VENV" == true ]]; then
        install_xai_venv
    else
        install_xai_system
    fi

    # Configuration
    download_genesis
    create_config
    setup_shell_integration

    # Verification
    verify_installation

    # Complete
    print_next_steps
}

# Run installer
main "$@"
