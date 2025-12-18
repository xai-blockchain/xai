#!/usr/bin/env bash
#
# XAI Node Setup Wizard - Bash Wrapper
#
# This script checks for Python and launches the interactive setup wizard.
# Can be run with: curl -sSL https://xai.example.com/install | bash
#

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Disable colors if not in terminal
if [ ! -t 1 ]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
    NC=''
fi

# Print functions
print_header() {
    echo -e "\n${BLUE}${BOLD}================================${NC}"
    echo -e "${BLUE}${BOLD}$1${NC}"
    echo -e "${BLUE}${BOLD}================================${NC}\n"
}

print_info() {
    echo -e "${CYAN}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓ ${NC}$1"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1"
}

print_error() {
    echo -e "${RED}✗ ${NC}$1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    local python_cmd=""

    # Try python3 first
    if command_exists python3; then
        python_cmd="python3"
    elif command_exists python; then
        python_cmd="python"
    else
        print_error "Python is not installed!"
        echo ""
        echo "Please install Python 3.8 or higher:"
        echo ""
        echo "  Ubuntu/Debian:  sudo apt update && sudo apt install python3 python3-pip"
        echo "  Fedora/RHEL:    sudo dnf install python3 python3-pip"
        echo "  macOS:          brew install python3"
        echo "  Windows:        Download from https://python.org"
        echo ""
        return 1
    fi

    # Check Python version
    local version=$($python_cmd -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    local major=$($python_cmd -c 'import sys; print(sys.version_info.major)')
    local minor=$($python_cmd -c 'import sys; print(sys.version_info.minor)')

    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        print_error "Python 3.8 or higher is required (found Python $version)"
        echo ""
        echo "Please upgrade your Python installation:"
        echo "  Ubuntu/Debian:  sudo apt update && sudo apt install python3.8"
        echo "  Fedora/RHEL:    sudo dnf install python38"
        echo "  macOS:          brew upgrade python3"
        echo ""
        return 1
    fi

    print_success "Python $version detected" >&2
    echo "$python_cmd"
    return 0
}

# Check required Python modules
check_python_modules() {
    local python_cmd="$1"

    print_info "Checking Python dependencies..."

    # Test a simple Python script that imports what we need
    # All modules are Python standard library and should always be available
    local test_result
    test_result=$($python_cmd -c "import socket, json, pathlib, secrets, hashlib, sys, os, shutil; print('OK')" 2>&1)

    if [ "$test_result" != "OK" ]; then
        print_error "Python installation appears incomplete: $test_result"
        print_error "Please reinstall Python 3.8 or higher"
        return 1
    fi

    print_success "All Python dependencies satisfied"
    return 0
}

# Detect script location
get_script_dir() {
    # If script is downloaded via curl, use current directory
    if [ ! -f "$0" ] || [ "$0" = "bash" ]; then
        echo "."
        return 0
    fi

    # Get directory of this script
    local dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    echo "$dir"
}

# Download setup wizard if not present
download_wizard() {
    local script_dir="$1"
    local wizard_path="$script_dir/setup_wizard.py"

    if [ -f "$wizard_path" ]; then
        return 0
    fi

    print_info "Downloading setup wizard..."

    # URL would be the raw GitHub URL or your hosting
    local wizard_url="https://raw.githubusercontent.com/xai-network/xai/main/scripts/setup_wizard.py"

    if command_exists curl; then
        if curl -fsSL "$wizard_url" -o "$wizard_path"; then
            print_success "Setup wizard downloaded"
            chmod +x "$wizard_path"
            return 0
        fi
    elif command_exists wget; then
        if wget -q "$wizard_url" -O "$wizard_path"; then
            print_success "Setup wizard downloaded"
            chmod +x "$wizard_path"
            return 0
        fi
    fi

    print_error "Failed to download setup wizard"
    print_error "Please download manually from: $wizard_url"
    return 1
}

# Main execution
main() {
    print_header "XAI Node Setup"

    print_info "Checking system requirements..."
    echo ""

    # Check Python
    local python_cmd
    if ! python_cmd=$(check_python); then
        exit 1
    fi

    # Check Python modules
    if ! check_python_modules "$python_cmd"; then
        exit 1
    fi

    echo ""

    # Determine script directory
    local script_dir
    script_dir=$(get_script_dir)

    # Check if setup_wizard.py exists
    local wizard_path="$script_dir/setup_wizard.py"

    if [ ! -f "$wizard_path" ]; then
        print_warning "Setup wizard not found at: $wizard_path"

        # Try to find it in parent directory (if running from project root)
        if [ -f "$script_dir/../setup_wizard.py" ]; then
            wizard_path="$script_dir/../setup_wizard.py"
            print_info "Found wizard at: $wizard_path"
        else
            # Ask to download
            echo ""
            read -p "$(echo -e ${CYAN}Would you like to download the setup wizard? [Y/n]: ${NC})" -n 1 -r
            echo ""

            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                if ! download_wizard "$script_dir"; then
                    exit 1
                fi
            else
                print_error "Cannot continue without setup wizard"
                exit 1
            fi
        fi
    fi

    print_success "Setup wizard found: $wizard_path"
    echo ""

    # Check if running as root (not recommended)
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root is not recommended for node operation"
        echo ""
        read -p "$(echo -e ${CYAN}Continue anyway? [y/N]: ${NC})" -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Setup cancelled"
            exit 0
        fi
    fi

    # Launch the Python wizard
    print_info "Launching setup wizard..."
    echo ""

    exec "$python_cmd" "$wizard_path" "$@"
}

# Trap Ctrl+C
trap 'echo -e "\n${YELLOW}Setup cancelled by user${NC}"; exit 130' INT

# Run main
main "$@"
