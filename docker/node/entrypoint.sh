#!/bin/bash
# AIXN Node Entrypoint Script
# Handles initialization and startup of AIXN blockchain node

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
AIXN_ENV=${AIXN_ENV:-production}
AIXN_DATA_DIR=${AIXN_DATA_DIR:-/data}
AIXN_LOG_DIR=${AIXN_LOG_DIR:-/logs}
AIXN_CONFIG_DIR=${AIXN_CONFIG_DIR:-/config}
AIXN_NODE_PORT=${AIXN_NODE_PORT:-8333}
AIXN_API_PORT=${AIXN_API_PORT:-8080}

log_info "Starting AIXN Blockchain Node"
log_info "Environment: $AIXN_ENV"

# ============================================================================
# Pre-flight Checks
# ============================================================================

log_info "Running pre-flight checks..."

# Check if data directory exists and is writable
if [ ! -d "$AIXN_DATA_DIR" ]; then
    log_error "Data directory does not exist: $AIXN_DATA_DIR"
    exit 1
fi

if [ ! -w "$AIXN_DATA_DIR" ]; then
    log_error "Data directory is not writable: $AIXN_DATA_DIR"
    exit 1
fi

# Check if log directory exists and is writable
if [ ! -d "$AIXN_LOG_DIR" ]; then
    log_warn "Log directory does not exist, creating: $AIXN_LOG_DIR"
    mkdir -p "$AIXN_LOG_DIR"
fi

# Create necessary subdirectories
mkdir -p \
    "$AIXN_DATA_DIR/blockchain" \
    "$AIXN_DATA_DIR/wallets" \
    "$AIXN_DATA_DIR/state" \
    "$AIXN_DATA_DIR/crypto_deposits" \
    "$AIXN_LOG_DIR/node" \
    "$AIXN_LOG_DIR/api"

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
CONFIG_FILE="$AIXN_CONFIG_DIR/${AIXN_ENV}.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    log_warn "Environment config not found: $CONFIG_FILE"
    CONFIG_FILE="$AIXN_CONFIG_DIR/default.yaml"
fi

if [ -f "$CONFIG_FILE" ]; then
    log_info "Using configuration: $CONFIG_FILE"
    export AIXN_CONFIG_FILE="$CONFIG_FILE"
else
    log_warn "No configuration file found, using defaults"
fi

# ============================================================================
# Initialize Blockchain (if needed)
# ============================================================================

BLOCKCHAIN_DB="$AIXN_DATA_DIR/blockchain/blockchain.db"

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

log_info "Starting AIXN node..."
log_info "P2P Port: $AIXN_NODE_PORT"
log_info "API Port: $AIXN_API_PORT"

# Handle different startup modes
case "${1:-node}" in
    node)
        log_info "Starting as full node..."
        exec python -m src.aixn.core.node
        ;;

    miner)
        log_info "Starting as mining node..."
        export AIXN_ENABLE_MINING=true
        exec python -m src.aixn.core.node
        ;;

    api)
        log_info "Starting API server only..."
        exec python -m src.aixn.explorer
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
