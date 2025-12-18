#!/usr/bin/env bash
# ============================================================================
# XAI Blockchain - Docker One-Click Installer
# ============================================================================
# Instantly run XAI blockchain node in Docker with persistent storage
#
# Usage:
#   curl -fsSL https://install.xai-blockchain.io/docker.sh | bash
#   ./docker-install.sh
#   ./docker-install.sh --mainnet
#   ./docker-install.sh --mine YOUR_ADDRESS
# ============================================================================

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
XAI_IMAGE="xai-blockchain/node:latest"
XAI_CONTAINER="xai-node"
XAI_NETWORK="testnet"
XAI_DATA_DIR="${HOME}/.xai/docker"
ENABLE_MINING=false
MINER_ADDRESS=""
DETACHED=true

# ============================================================================
# Utility Functions
# ============================================================================

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  XAI Blockchain - Docker Installer${NC}"
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

# ============================================================================
# Docker Verification
# ============================================================================

check_docker() {
    print_info "Checking Docker installation..."

    if ! check_command docker; then
        print_error "Docker is not installed"
        echo ""
        echo "Please install Docker first:"
        echo "  Linux:   curl -fsSL https://get.docker.com | sh"
        echo "  macOS:   brew install --cask docker"
        echo "  Windows: https://docs.docker.com/desktop/windows/install/"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        echo "Please start Docker and try again"
        exit 1
    fi

    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_success "Docker ${DOCKER_VERSION} is installed and running"
}

# ============================================================================
# Container Management
# ============================================================================

stop_existing_container() {
    if docker ps -a --format '{{.Names}}' | grep -q "^${XAI_CONTAINER}$"; then
        print_info "Stopping existing XAI container..."
        docker stop "${XAI_CONTAINER}" >/dev/null 2>&1 || true
        docker rm "${XAI_CONTAINER}" >/dev/null 2>&1 || true
        print_success "Removed existing container"
    fi
}

pull_image() {
    print_info "Pulling XAI blockchain image..."
    print_info "Image: ${XAI_IMAGE}"

    if docker pull "${XAI_IMAGE}" 2>&1; then
        print_success "Image pulled successfully"
    else
        print_warning "Could not pull from registry, checking local image..."
        if docker image inspect "${XAI_IMAGE}" >/dev/null 2>&1; then
            print_success "Using local image"
        else
            print_error "Image not found locally or remotely"
            print_info "Building image from source..."
            build_local_image
        fi
    fi
}

build_local_image() {
    # Check if we're in the XAI source directory
    if [[ -f "pyproject.toml" ]] && grep -q "xai-blockchain" pyproject.toml 2>/dev/null; then
        print_info "Building XAI image from local source..."
        docker build -t "${XAI_IMAGE}" -f docker/node/Dockerfile .
        print_success "Image built successfully"
    else
        print_error "Cannot build image: not in XAI source directory"
        print_info "Clone the repository first: git clone https://github.com/xai-blockchain/xai.git"
        exit 1
    fi
}

create_data_directory() {
    print_info "Creating data directory..."
    mkdir -p "${XAI_DATA_DIR}"/{blockchain,wallets,state,config,logs}
    print_success "Data directory: ${XAI_DATA_DIR}"
}

download_genesis() {
    if [[ ! -f "${XAI_DATA_DIR}/config/genesis.json" ]]; then
        print_info "Downloading genesis file..."
        if curl -fsSL "https://raw.githubusercontent.com/xai-blockchain/xai/main/genesis.json" \
                -o "${XAI_DATA_DIR}/config/genesis.json" 2>/dev/null; then
            print_success "Genesis file downloaded"
        else
            print_warning "Could not download genesis, will use default"
        fi
    fi
}

# ============================================================================
# Container Launch
# ============================================================================

start_container() {
    print_info "Starting XAI blockchain node..."
    print_info "Network: ${XAI_NETWORK}"

    # Build environment variables
    local env_vars=(
        -e "XAI_NETWORK=${XAI_NETWORK}"
        -e "PYTHONUNBUFFERED=1"
    )

    if [[ "$ENABLE_MINING" == true ]] && [[ -n "$MINER_ADDRESS" ]]; then
        env_vars+=(-e "MINER_ADDRESS=${MINER_ADDRESS}")
        print_info "Mining enabled: ${MINER_ADDRESS}"
    fi

    # Determine ports based on network
    local p2p_port=18545
    local rpc_port=18546
    local metrics_port=19090

    if [[ "$XAI_NETWORK" == "mainnet" ]]; then
        p2p_port=8545
        rpc_port=8546
        metrics_port=9090
    fi

    # Run container
    local docker_args=(
        run
        --name "${XAI_CONTAINER}"
        --hostname xai-node
        "${env_vars[@]}"
        -v "${XAI_DATA_DIR}/blockchain:/data/blockchain"
        -v "${XAI_DATA_DIR}/wallets:/data/wallets"
        -v "${XAI_DATA_DIR}/state:/data/state"
        -v "${XAI_DATA_DIR}/config:/config"
        -v "${XAI_DATA_DIR}/logs:/logs"
        -p "${p2p_port}:${p2p_port}"
        -p "${rpc_port}:${rpc_port}"
        -p "${metrics_port}:${metrics_port}"
        --restart unless-stopped
    )

    if [[ "$DETACHED" == true ]]; then
        docker_args+=(-d)
    fi

    docker_args+=("${XAI_IMAGE}")

    if docker "${docker_args[@]}"; then
        print_success "XAI node container started"
        echo ""
        print_info "Container: ${XAI_CONTAINER}"
        print_info "P2P Port: ${p2p_port}"
        print_info "RPC Port: ${rpc_port}"
        print_info "Metrics Port: ${metrics_port}"
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# ============================================================================
# Post-Installation
# ============================================================================

show_logs() {
    if [[ "$DETACHED" == true ]]; then
        echo ""
        print_info "Showing logs (Ctrl+C to exit)..."
        sleep 2
        docker logs -f "${XAI_CONTAINER}"
    fi
}

print_next_steps() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  XAI Node Running!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo ""
    echo -e "  ${YELLOW}docker logs -f ${XAI_CONTAINER}${NC}"
    echo -e "    View node logs in real-time"
    echo ""
    echo -e "  ${YELLOW}docker exec -it ${XAI_CONTAINER} xai-wallet generate-address${NC}"
    echo -e "    Generate a new wallet address"
    echo ""
    echo -e "  ${YELLOW}docker exec -it ${XAI_CONTAINER} xai-wallet balance --address ADDR${NC}"
    echo -e "    Check wallet balance"
    echo ""
    echo -e "  ${YELLOW}docker stop ${XAI_CONTAINER}${NC}"
    echo -e "    Stop the node"
    echo ""
    echo -e "  ${YELLOW}docker start ${XAI_CONTAINER}${NC}"
    echo -e "    Start the node again"
    echo ""
    echo -e "  ${YELLOW}docker restart ${XAI_CONTAINER}${NC}"
    echo -e "    Restart the node"
    echo ""
    echo -e "  ${YELLOW}docker rm -f ${XAI_CONTAINER}${NC}"
    echo -e "    Remove the container (data persists in ${XAI_DATA_DIR})"
    echo ""
    echo -e "${BLUE}Access Points:${NC}"
    echo -e "  RPC API:    http://localhost:${rpc_port:-18546}"
    echo -e "  Metrics:    http://localhost:${metrics_port:-19090}/metrics"
    echo -e "  Data:       ${XAI_DATA_DIR}"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo -e "  https://docs.xai-blockchain.io"
    echo ""
}

cleanup_on_error() {
    print_error "Installation failed"
    print_info "Cleaning up..."
    docker stop "${XAI_CONTAINER}" >/dev/null 2>&1 || true
    docker rm "${XAI_CONTAINER}" >/dev/null 2>&1 || true
}

# ============================================================================
# Argument Parsing
# ============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mainnet)
                XAI_NETWORK="mainnet"
                XAI_IMAGE="xai-blockchain/node:mainnet"
                shift
                ;;
            --testnet)
                XAI_NETWORK="testnet"
                shift
                ;;
            --mine)
                ENABLE_MINING=true
                MINER_ADDRESS="$2"
                shift 2
                ;;
            --image)
                XAI_IMAGE="$2"
                shift 2
                ;;
            --data-dir)
                XAI_DATA_DIR="$2"
                shift 2
                ;;
            --foreground|-f)
                DETACHED=false
                shift
                ;;
            --help|-h)
                echo "XAI Blockchain - Docker Installer"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --mainnet           Use mainnet (default: testnet)"
                echo "  --testnet           Use testnet (default)"
                echo "  --mine ADDRESS      Enable mining to specified address"
                echo "  --image IMAGE       Use custom Docker image"
                echo "  --data-dir DIR      Custom data directory (default: ~/.xai/docker)"
                echo "  --foreground, -f    Run in foreground (don't detach)"
                echo "  --help, -h          Show this help"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Run '$0 --help' for usage"
                exit 1
                ;;
        esac
    done
}

# ============================================================================
# Main
# ============================================================================

main() {
    parse_args "$@"

    trap cleanup_on_error ERR

    print_header
    echo ""

    check_docker
    stop_existing_container
    create_data_directory
    download_genesis
    pull_image
    start_container

    print_next_steps

    # Show logs if running in detached mode
    if [[ "$DETACHED" == true ]]; then
        echo -e "${YELLOW}Press Ctrl+C to exit log view (node will keep running)${NC}"
        echo ""
        sleep 2
        docker logs -f "${XAI_CONTAINER}" 2>&1 || true
    fi
}

main "$@"
