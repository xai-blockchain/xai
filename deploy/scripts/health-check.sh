#!/bin/bash
# ============================================================================
# XAI Blockchain - Health Check Script
# ============================================================================
# This script performs comprehensive health checks on the XAI blockchain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
HEALTH_LOG="${PROJECT_ROOT}/health-check.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BLOCKCHAIN_HOST="${BLOCKCHAIN_HOST:-localhost}"
BLOCKCHAIN_PORT="${BLOCKCHAIN_PORT:-8080}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-xai}"
DB_NAME="${DB_NAME:-xai_blockchain}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

CHECKS_PASSED=0
CHECKS_FAILED=0

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$HEALTH_LOG"
}

log_success() {
    echo -e "${GREEN}✓ $*${NC}" | tee -a "$HEALTH_LOG"
    ((CHECKS_PASSED++))
}

log_failed() {
    echo -e "${RED}✗ $*${NC}" | tee -a "$HEALTH_LOG"
    ((CHECKS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}⚠ $*${NC}" | tee -a "$HEALTH_LOG"
}

# ============================================================================
# System Checks
# ============================================================================

check_disk_space() {
    log "Checking disk space..."
    
    local available=$(df /var | awk 'NR==2 {print $4}')
    if [ "$available" -lt 5242880 ]; then  # 5GB
        log_failed "Insufficient disk space: ${available}KB available"
        return 1
    fi
    
    log_success "Disk space: ${available}KB available"
}

check_memory() {
    log "Checking memory availability..."
    
    local available=$(free -m | awk 'NR==2 {print $7}')
    if [ "$available" -lt 512 ]; then
        log_failed "Low memory: ${available}MB available"
        return 1
    fi
    
    log_success "Memory: ${available}MB available"
}

check_cpu() {
    log "Checking CPU load..."
    
    local load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
    local cores=$(nproc)
    local threshold=$(echo "scale=2; $cores * 0.8" | bc)
    
    if (( $(echo "$load > $threshold" | bc -l) )); then
        log_warning "High CPU load: $load (cores: $cores)"
    else
        log_success "CPU load: $load (cores: $cores)"
    fi
}

# ============================================================================
# Service Checks
# ============================================================================

check_blockchain_node() {
    log "Checking blockchain node..."
    
    if ! curl -sf "http://${BLOCKCHAIN_HOST}:${BLOCKCHAIN_PORT}/health" &>/dev/null; then
        log_failed "Blockchain node is not responding"
        return 1
    fi
    
    log_success "Blockchain node is running"
}

check_api_endpoint() {
    log "Checking API endpoint..."
    
    local response=$(curl -s "http://${BLOCKCHAIN_HOST}:${BLOCKCHAIN_PORT}/api/v1/network/info" \
        --max-time 5)
    
    if [ -z "$response" ]; then
        log_failed "API endpoint not responding"
        return 1
    fi
    
    # Verify JSON response
    if echo "$response" | jq . &>/dev/null; then
        log_success "API endpoint is responding with valid JSON"
    else
        log_failed "API endpoint returned invalid JSON"
        return 1
    fi
}

check_websocket() {
    log "Checking WebSocket endpoint..."
    
    if ! nc -zv "${BLOCKCHAIN_HOST}" 8081 &>/dev/null; then
        log_failed "WebSocket port 8081 is not accessible"
        return 1
    fi
    
    log_success "WebSocket port is accessible"
}

check_metrics() {
    log "Checking metrics endpoint..."
    
    if ! curl -sf "http://${BLOCKCHAIN_HOST}:9090/metrics" &>/dev/null; then
        log_failed "Metrics endpoint not responding"
        return 1
    fi
    
    log_success "Metrics endpoint is responding"
}

# ============================================================================
# Database Checks
# ============================================================================

check_database() {
    log "Checking database connectivity..."
    
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" &>/dev/null; then
        log_failed "Cannot connect to PostgreSQL database"
        return 1
    fi
    
    log_success "PostgreSQL database is accessible"
}

check_database_tables() {
    log "Checking database tables..."
    
    local count=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
    
    if [ "$count" -lt 5 ]; then
        log_failed "Database has only $count tables (expected >= 5)"
        return 1
    fi
    
    log_success "Database has $count tables"
}

check_database_size() {
    log "Checking database size..."
    
    local size=$(psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT pg_size_pretty(pg_database_size('$DB_NAME'))")
    
    log_success "Database size: $size"
}

# ============================================================================
# Cache Checks
# ============================================================================

check_redis() {
    log "Checking Redis connectivity..."
    
    if ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping &>/dev/null; then
        log_failed "Cannot connect to Redis"
        return 1
    fi
    
    log_success "Redis is accessible"
}

check_redis_memory() {
    log "Checking Redis memory usage..."
    
    local memory=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info memory | \
        grep "used_memory_human" | cut -d: -f2)
    
    log_success "Redis memory usage: $memory"
}

# ============================================================================
# Blockchain Checks
# ============================================================================

check_blockchain_sync() {
    log "Checking blockchain sync status..."
    
    local response=$(curl -s "http://${BLOCKCHAIN_HOST}:${BLOCKCHAIN_PORT}/api/v1/blockchain/info")
    local is_synced=$(echo "$response" | jq -r '.is_synced // "unknown"')
    
    if [ "$is_synced" = "true" ]; then
        log_success "Blockchain is synchronized"
    elif [ "$is_synced" = "false" ]; then
        log_warning "Blockchain is synchronizing"
    else
        log_failed "Cannot determine blockchain sync status"
        return 1
    fi
}

check_block_height() {
    log "Checking block height..."
    
    local response=$(curl -s "http://${BLOCKCHAIN_HOST}:${BLOCKCHAIN_PORT}/api/v1/blockchain/info")
    local height=$(echo "$response" | jq -r '.block_height // "unknown"')
    
    if [ "$height" != "unknown" ]; then
        log_success "Current block height: $height"
    else
        log_failed "Cannot determine block height"
        return 1
    fi
}

check_peer_count() {
    log "Checking peer count..."
    
    local response=$(curl -s "http://${BLOCKCHAIN_HOST}:${BLOCKCHAIN_PORT}/api/v1/network/info")
    local peers=$(echo "$response" | jq -r '.peer_count // "unknown"')
    
    if [ "$peers" != "unknown" ]; then
        log_success "Connected peers: $peers"
    else
        log_warning "Cannot determine peer count"
    fi
}

# ============================================================================
# Service Status Checks
# ============================================================================

check_systemd_services() {
    log "Checking systemd services..."
    
    local services=("xai-node" "prometheus" "grafana-server")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_success "Service $service is running"
        else
            log_warning "Service $service is not running"
        fi
    done
}

check_docker_containers() {
    log "Checking Docker containers..."
    
    if ! command -v docker &>/dev/null; then
        log_warning "Docker not installed"
        return 0
    fi
    
    local running=$(docker ps --format "{{.Names}}" | wc -l)
    log_success "Docker containers running: $running"
    
    # Check for XAI containers
    if docker ps | grep -q xai; then
        log_success "XAI containers are running"
    else
        log_warning "No XAI containers found"
    fi
}

# ============================================================================
# Security Checks
# ============================================================================

check_ssl_certificate() {
    log "Checking SSL certificate..."
    
    if [ -f "/etc/ssl/certs/xai.crt" ]; then
        local expiry=$(openssl x509 -enddate -noout -in /etc/ssl/certs/xai.crt | cut -d= -f2)
        log_success "SSL certificate found, expires: $expiry"
    else
        log_warning "SSL certificate not found"
    fi
}

check_firewall() {
    log "Checking firewall status..."
    
    if command -v ufw &>/dev/null; then
        if ufw status | grep -q "Status: active"; then
            log_success "Firewall is enabled"
        else
            log_warning "Firewall is not enabled"
        fi
    else
        log_warning "UFW not installed"
    fi
}

# ============================================================================
# Report Generation
# ============================================================================

generate_report() {
    log ""
    log "=========================================="
    log "Health Check Summary"
    log "=========================================="
    log "Timestamp: $(date)"
    log "Hostname: $(hostname)"
    log "Kernel: $(uname -r)"
    log "Uptime: $(uptime -p)"
    log ""
    log "Results:"
    log "  Passed: ${GREEN}${CHECKS_PASSED}${NC}"
    log "  Failed: ${RED}${CHECKS_FAILED}${NC}"
    log "=========================================="
    
    if [ $CHECKS_FAILED -eq 0 ]; then
        log_success "All health checks passed!"
        return 0
    else
        log_failed "$CHECKS_FAILED health checks failed"
        return 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "XAI Blockchain Health Check Started"
    log "=========================================="
    
    # System checks
    check_disk_space || true
    check_memory || true
    check_cpu || true
    
    # Service checks
    check_blockchain_node || true
    check_api_endpoint || true
    check_websocket || true
    check_metrics || true
    
    # Database checks
    check_database || true
    check_database_tables || true
    check_database_size || true
    
    # Cache checks
    check_redis || true
    check_redis_memory || true
    
    # Blockchain checks
    check_blockchain_sync || true
    check_block_height || true
    check_peer_count || true
    
    # Service status
    check_systemd_services || true
    check_docker_containers || true
    
    # Security checks
    check_ssl_certificate || true
    check_firewall || true
    
    # Generate report
    generate_report
}

main "$@"
