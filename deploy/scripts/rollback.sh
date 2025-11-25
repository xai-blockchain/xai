#!/bin/bash
# ============================================================================
# XAI Blockchain - Rollback Script
# ============================================================================
# This script safely rolls back a deployment to the previous version

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
ROLLBACK_LOG="${PROJECT_ROOT}/rollback.log"
BACKUP_DIR="${1:-/var/backups/pre-deployment}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$ROLLBACK_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$ROLLBACK_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$ROLLBACK_LOG"
}

confirm_rollback() {
    echo -e "${YELLOW}WARNING: This will rollback the deployment to the previous version${NC}"
    read -p "Are you sure you want to continue? (yes/no): " response
    if [ "$response" != "yes" ]; then
        log "Rollback cancelled"
        exit 0
    fi
}

stop_services() {
    log "Stopping services..."
    
    systemctl stop xai-node || true
    systemctl stop xai-explorer || true
    systemctl stop prometheus || true
    systemctl stop grafana-server || true
    
    log_success "Services stopped"
}

restore_database() {
    log "Restoring database from backup..."
    
    if [ ! -f "$BACKUP_DIR/database-"*.sql.gz ]; then
        log_error "No database backup found"
        return 1
    fi
    
    local latest_backup=$(ls -t "$BACKUP_DIR"/database-*.sql.gz | head -1)
    log "Restoring from: $latest_backup"
    
    gunzip -c "$latest_backup" | psql -h "${POSTGRES_HOST:-localhost}" \
        -U "${POSTGRES_USER:-xai}" "${POSTGRES_DB:-xai_blockchain}" || {
        log_error "Database restore failed"
        return 1
    }
    
    log_success "Database restored"
}

restore_blockchain() {
    log "Restoring blockchain data..."
    
    if [ ! -f "$BACKUP_DIR/blockchain-"*.tar.gz ]; then
        log_error "No blockchain backup found"
        return 1
    fi
    
    local latest_backup=$(ls -t "$BACKUP_DIR"/blockchain-*.tar.gz | head -1)
    log "Restoring from: $latest_backup"
    
    tar -xzf "$latest_backup" -C / || {
        log_error "Blockchain restore failed"
        return 1
    }
    
    log_success "Blockchain data restored"
}

restore_configuration() {
    log "Restoring configuration files..."
    
    if [ ! -f "$BACKUP_DIR/config-"*.tar.gz ]; then
        log_error "No configuration backup found"
        return 1
    fi
    
    local latest_backup=$(ls -t "$BACKUP_DIR"/config-*.tar.gz | head -1)
    log "Restoring from: $latest_backup"
    
    tar -xzf "$latest_backup" -C / || {
        log_error "Configuration restore failed"
        return 1
    }
    
    log_success "Configuration restored"
}

restore_docker_images() {
    log "Restoring previous Docker images..."
    
    # List available images
    local images=$(docker images | grep xai | awk '{print $1 ":" $2}')
    
    if [ -z "$images" ]; then
        log_error "No previous Docker images found"
        return 1
    fi
    
    log "Available images:"
    echo "$images"
    
    log_success "Docker images available for rollback"
}

start_services() {
    log "Starting services..."
    
    systemctl start xai-node || {
        log_error "Failed to start blockchain node"
        return 1
    }
    
    sleep 5
    
    systemctl start xai-explorer || {
        log_error "Failed to start block explorer"
        return 1
    }
    
    systemctl start prometheus || {
        log_error "Failed to start Prometheus"
        return 1
    }
    
    systemctl start grafana-server || {
        log_error "Failed to start Grafana"
        return 1
    }
    
    log_success "Services started"
}

verify_rollback() {
    log "Verifying rollback..."
    
    # Wait for services to stabilize
    sleep 10
    
    # Check blockchain node health
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8080/health &>/dev/null; then
            log_success "Blockchain node is healthy"
            break
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log_error "Blockchain node health check failed"
        return 1
    fi
    
    # Verify API
    if curl -sf http://localhost:8080/api/v1/network/info &>/dev/null; then
        log_success "API is responding"
    else
        log_error "API is not responding"
        return 1
    fi
    
    log_success "Rollback verification passed"
}

main() {
    log "=========================================="
    log "Rollback Process Started"
    log "=========================================="
    log "Backup Directory: $BACKUP_DIR"
    log "Timestamp: $(date)"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    confirm_rollback
    
    stop_services || {
        log_error "Failed to stop services"
        exit 1
    }
    
    restore_configuration || {
        log_error "Failed to restore configuration"
        exit 1
    }
    
    restore_database || {
        log_error "Failed to restore database"
        exit 1
    }
    
    restore_blockchain || {
        log_error "Failed to restore blockchain"
        exit 1
    }
    
    restore_docker_images
    
    start_services || {
        log_error "Failed to start services"
        exit 1
    }
    
    verify_rollback || {
        log_error "Rollback verification failed"
        exit 1
    }
    
    log_success "=========================================="
    log_success "Rollback completed successfully!"
    log_success "=========================================="
}

main "$@"
