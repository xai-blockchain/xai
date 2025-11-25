#!/bin/bash
# XAI Node Entrypoint Script
# Handles initialization and startup of XAI blockchain node

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Environment variables with defaults
XAI_ENV=${XAI_ENV:-production}
XAI_DATA_DIR=${XAI_DATA_DIR:-/data}
XAI_LOG_DIR=${XAI_LOG_DIR:-/logs}
XAI_CONFIG_DIR=${XAI_CONFIG_DIR:-/config}
XAI_NODE_PORT=${XAI_NODE_PORT:-8333}
XAI_API_PORT=${XAI_API_PORT:-8080}

log_info "Starting XAI Blockchain Node"
log_info "Environment: $XAI_ENV"

# ============================================================================
# Pre-flight Checks
# ============================================================================

log_info "Running pre-flight checks..."

# Check if data directory exists and is writable
if [ ! -d "$XAI_DATA_DIR" ]; then
    log_error "Data directory does not exist: $XAI_DATA_DIR"
    exit 1
fi

if [ ! -w "$XAI_DATA_DIR" ]; then
    log_error "Data directory is not writable: $XAI_DATA_DIR"
    exit 1
fi

# Check if log directory exists and is writable
if [ ! -d "$XAI_LOG_DIR" ]; then
    log_warn "Log directory does not exist, creating: $XAI_LOG_DIR"
    mkdir -p "$XAI_LOG_DIR"
fi

# Create necessary subdirectories
mkdir -p \
    "$XAI_DATA_DIR/blockchain" \
    "$XAI_DATA_DIR/wallets" \
    "$XAI_DATA_DIR/state" \
    "$XAI_DATA_DIR/crypto_deposits" \
    "$XAI_LOG_DIR/node" \
    "$XAI_LOG_DIR/api"

log_info "Directory structure verified"

# ============================================================================
# Database Connection Check (if applicable)
# ============================================================================

if [ -n "$POSTGRES_HOST" ]; then
    log_info "Checking PostgreSQL connection..."

    # Wait for PostgreSQL to be ready
    for i in {1..30}; do
        if nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" > /dev/null 2>&1; then
            log_info "PostgreSQL is ready"
            break
        fi

        if [ $i -eq 30 ]; then
            log_error "PostgreSQL is not available after 30 attempts"
            exit 1
        fi

        log_warn "Waiting for PostgreSQL... (attempt $i/30)"
        sleep 2
    done
fi

# ============================================================================
# Redis Connection Check (if applicable)
# ============================================================================

if [ -n "$REDIS_HOST" ]; then
    log_info "Checking Redis connection..."

    # Wait for Redis to be ready
    for i in {1..30}; do
        if nc -z "$REDIS_HOST" "${REDIS_PORT:-6379}" > /dev/null 2>&1; then
            log_info "Redis is ready"
            break
        fi

        if [ $i -eq 30 ]; then
            log_error "Redis is not available after 30 attempts"
            exit 1
        fi

        log_warn "Waiting for Redis... (attempt $i/30)"
        sleep 2
    done
fi

# ============================================================================
# Configuration Check
# ============================================================================

log_info "Checking configuration..."

# Use environment-specific config if available
CONFIG_FILE="$XAI_CONFIG_DIR/${XAI_ENV}.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    log_warn "Environment config not found: $CONFIG_FILE"
    CONFIG_FILE="$XAI_CONFIG_DIR/default.yaml"
fi

if [ -f "$CONFIG_FILE" ]; then
    log_info "Using configuration: $CONFIG_FILE"
    export XAI_CONFIG_FILE="$CONFIG_FILE"
else
    log_warn "No configuration file found, using defaults"
fi

# ============================================================================
# Initialize Blockchain (if needed)
# ============================================================================

BLOCKCHAIN_DB="$XAI_DATA_DIR/blockchain/blockchain.db"

if [ ! -f "$BLOCKCHAIN_DB" ]; then
    log_info "Blockchain database not found, initializing..."

    # Check if initialization script exists
    if [ -f "/app/scripts/initialize_blockchain.py" ]; then
        python /app/scripts/initialize_blockchain.py
    else
        log_warn "Initialization script not found, blockchain will initialize on first run"
    fi
else
    log_info "Blockchain database found: $BLOCKCHAIN_DB"
fi

# ============================================================================
# Start Node
# ============================================================================

log_info "Starting XAI node..."
log_info "P2P Port: $XAI_NODE_PORT"
log_info "API Port: $XAI_API_PORT"

# Handle different startup modes
case "${1:-node}" in
    node)
        log_info "Starting as full node..."
        exec python -m xai.core.node
        ;;

    miner)
        log_info "Starting as mining node..."
        export XAI_ENABLE_MINING=true
        exec python -m xai.core.node
        ;;

    api)
        log_info "Starting API server only..."
        exec python -m xai.explorer
        ;;

    shell)
        log_info "Starting interactive shell..."
        exec /bin/bash
        ;;

    *)
        log_info "Executing custom command: $@"
        exec "$@"
        ;;
esac
