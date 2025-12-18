#!/usr/bin/env bash
# ============================================================================
# XAI Blockchain - Installation Verification Script
# ============================================================================
# Verify that XAI blockchain is correctly installed and functional
#
# Usage:
#   ./verify-installation.sh
#   ./verify-installation.sh --verbose
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

VERBOSE=false
CHECKS_PASSED=0
CHECKS_FAILED=0

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  XAI Blockchain - Installation Verification${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}ℹ${NC} $1"
    fi
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

# ============================================================================
# Verification Checks
# ============================================================================

check_python() {
    echo ""
    echo "Checking Python..."

    if check_command python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python installed: ${PYTHON_VERSION}"
        print_info "Location: $(command -v python3)"

        # Check version
        MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

        if [[ "$MAJOR" -ge 3 ]] && [[ "$MINOR" -ge 10 ]]; then
            print_success "Python version meets requirements (>=3.10)"
        else
            print_error "Python version too old (need >=3.10, got ${PYTHON_VERSION})"
        fi
    else
        print_error "Python 3 not found"
    fi
}

check_xai_commands() {
    echo ""
    echo "Checking XAI commands..."

    # Check xai CLI
    if check_command xai; then
        print_success "xai command found"
        print_info "Location: $(command -v xai)"

        # Check version
        if xai --version >/dev/null 2>&1; then
            VERSION=$(xai --version 2>&1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
            print_success "xai version: ${VERSION}"
        else
            print_warning "Could not determine xai version"
        fi
    else
        print_error "xai command not found"
    fi

    # Check xai-node
    if check_command xai-node; then
        print_success "xai-node command found"
        print_info "Location: $(command -v xai-node)"
    else
        print_error "xai-node command not found"
    fi

    # Check xai-wallet
    if check_command xai-wallet; then
        print_success "xai-wallet command found"
        print_info "Location: $(command -v xai-wallet)"
    else
        print_error "xai-wallet command not found"
    fi
}

check_directories() {
    echo ""
    echo "Checking directories..."

    XAI_DIR="${HOME}/.xai"
    SYSTEM_DIR="/var/lib/xai"

    # Check user directory
    if [[ -d "$XAI_DIR" ]]; then
        print_success "User data directory exists: ${XAI_DIR}"

        # Check subdirectories
        for subdir in blockchain wallets state config logs; do
            if [[ -d "${XAI_DIR}/${subdir}" ]]; then
                print_info "  ✓ ${subdir}/ exists"
            else
                print_warning "  ${subdir}/ not found"
            fi
        done
    elif [[ -d "$SYSTEM_DIR" ]]; then
        print_success "System data directory exists: ${SYSTEM_DIR}"
        print_info "Running as system service"
    else
        print_error "No data directory found (${XAI_DIR} or ${SYSTEM_DIR})"
    fi
}

check_configuration() {
    echo ""
    echo "Checking configuration..."

    CONFIG_USER="${HOME}/.xai/config/node.yaml"
    CONFIG_SYSTEM="/etc/xai/node.yaml"

    if [[ -f "$CONFIG_USER" ]]; then
        print_success "Configuration file exists: ${CONFIG_USER}"
        print_info "$(wc -l < "$CONFIG_USER") lines"
    elif [[ -f "$CONFIG_SYSTEM" ]]; then
        print_success "System configuration exists: ${CONFIG_SYSTEM}"
    else
        print_warning "No configuration file found"
        print_info "A default configuration will be created on first run"
    fi

    # Check genesis file
    GENESIS_USER="${HOME}/.xai/config/genesis.json"
    GENESIS_SYSTEM="/etc/xai/genesis.json"

    if [[ -f "$GENESIS_USER" ]]; then
        print_success "Genesis file exists: ${GENESIS_USER}"
    elif [[ -f "$GENESIS_SYSTEM" ]]; then
        print_success "System genesis file exists: ${GENESIS_SYSTEM}"
    else
        print_warning "Genesis file not found"
    fi
}

check_python_packages() {
    echo ""
    echo "Checking Python packages..."

    # Try to import xai module
    if python3 -c "import xai" 2>/dev/null; then
        print_success "XAI Python package installed"

        # Get installed version
        VERSION=$(python3 -c "import pkg_resources; print(pkg_resources.get_distribution('xai-blockchain').version)" 2>/dev/null || echo "unknown")
        print_info "Package version: ${VERSION}"
    else
        print_error "XAI Python package not found"
    fi

    # Check key dependencies
    DEPENDENCIES=(
        "flask"
        "cryptography"
        "requests"
        "yaml"
        "prometheus_client"
        "websockets"
        "click"
    )

    local missing=0
    for dep in "${DEPENDENCIES[@]}"; do
        if python3 -c "import ${dep}" 2>/dev/null; then
            print_info "  ✓ ${dep}"
        else
            print_warning "  Missing: ${dep}"
            ((missing++))
        fi
    done

    if [[ $missing -eq 0 ]]; then
        print_success "All dependencies installed"
    else
        print_warning "${missing} dependencies missing"
    fi
}

check_system_service() {
    echo ""
    echo "Checking system service..."

    if check_command systemctl; then
        if systemctl is-enabled xai-node >/dev/null 2>&1; then
            print_success "xai-node service is enabled"

            if systemctl is-active xai-node >/dev/null 2>&1; then
                print_success "xai-node service is running"
            else
                print_warning "xai-node service is not running"
                print_info "Start with: sudo systemctl start xai-node"
            fi
        else
            print_info "xai-node service not configured (manual installation)"
        fi
    else
        print_info "systemd not available (manual installation or Docker)"
    fi
}

check_docker() {
    echo ""
    echo "Checking Docker installation..."

    if check_command docker; then
        print_success "Docker installed"

        # Check if XAI container exists
        if docker ps -a --format '{{.Names}}' | grep -q "^xai-node$"; then
            print_success "XAI Docker container exists"

            if docker ps --format '{{.Names}}' | grep -q "^xai-node$"; then
                print_success "XAI container is running"
            else
                print_warning "XAI container is stopped"
                print_info "Start with: docker start xai-node"
            fi
        else
            print_info "No XAI Docker container found"
        fi
    else
        print_info "Docker not installed (manual installation)"
    fi
}

check_network_connectivity() {
    echo ""
    echo "Checking network connectivity..."

    # Check if node is accessible
    if curl -f http://localhost:18546/health >/dev/null 2>&1; then
        print_success "Node RPC is accessible on port 18546"
    elif curl -f http://localhost:8546/health >/dev/null 2>&1; then
        print_success "Node RPC is accessible on port 8546 (mainnet)"
    else
        print_warning "Node RPC not accessible (node may not be running)"
        print_info "Start node with: xai-node --network testnet"
    fi
}

test_wallet_functionality() {
    echo ""
    echo "Testing wallet functionality..."

    # Try to generate a test address
    if check_command xai-wallet; then
        print_info "Testing wallet address generation..."
        if xai-wallet generate-address --test >/dev/null 2>&1; then
            print_success "Wallet generation works"
        else
            print_warning "Could not test wallet (--test flag may not be supported)"
        fi
    fi
}

# ============================================================================
# Summary
# ============================================================================

print_summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Verification Summary${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    TOTAL=$((CHECKS_PASSED + CHECKS_FAILED))

    echo -e "  ${GREEN}Passed:${NC} ${CHECKS_PASSED}/${TOTAL}"
    if [[ $CHECKS_FAILED -gt 0 ]]; then
        echo -e "  ${RED}Failed:${NC} ${CHECKS_FAILED}/${TOTAL}"
    fi

    echo ""

    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ Installation verified successfully!${NC}"
        echo ""
        echo "Next steps:"
        echo "  1. Generate wallet: xai-wallet generate-address"
        echo "  2. Start node: xai-node --network testnet"
        echo "  3. Get test coins: xai-wallet request-faucet --address ADDR"
    else
        echo -e "${YELLOW}⚠ Some checks failed${NC}"
        echo ""
        echo "Troubleshooting:"
        echo "  - Check installation logs"
        echo "  - Verify Python version (>=3.10)"
        echo "  - Ensure PATH is configured correctly"
        echo "  - See INSTALL.md for detailed instructions"
    fi

    echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
    if [[ "$1" == "--verbose" ]] || [[ "$1" == "-v" ]]; then
        VERBOSE=true
    fi

    if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
        echo "XAI Blockchain Installation Verification"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --verbose, -v    Show detailed information"
        echo "  --help, -h       Show this help message"
        exit 0
    fi

    print_header
    echo ""

    check_python
    check_xai_commands
    check_directories
    check_configuration
    check_python_packages
    check_system_service
    check_docker
    check_network_connectivity
    test_wallet_functionality

    print_summary

    if [[ $CHECKS_FAILED -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
