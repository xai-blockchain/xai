#!/bin/bash
# ============================================================================
# XAI Blockchain - Production Deployment Script
# ============================================================================
# This script handles the complete deployment of the XAI blockchain
# to production environments with comprehensive error handling and validation.

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DEPLOY_LOG="${PROJECT_ROOT}/deploy.log"
LOCK_FILE="/var/run/xai-deploy.lock"
BACKUP_DIR="/var/backups/pre-deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$DEPLOY_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$DEPLOY_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$DEPLOY_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$DEPLOY_LOG"
}

# ============================================================================
# Error Handling
# ============================================================================

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Deployment failed with exit code $exit_code"
        log_error "Rolling back changes..."
        rollback
    fi
    rm -f "$LOCK_FILE"
    exit $exit_code
}

trap cleanup EXIT

# ============================================================================
# Lock Management
# ============================================================================

acquire_lock() {
    if [ -f "$LOCK_FILE" ]; then
        log_error "Another deployment is already in progress"
        exit 1
    fi
    echo $$ > "$LOCK_FILE"
    log "Deployment lock acquired"
}

# ============================================================================
# Validation Functions
# ============================================================================

validate_environment() {
    log "Validating deployment environment..."
    
    # Check required tools
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check permissions
    if ! sudo -n true 2>/dev/null; then
        log_error "Sudo privileges required without password"
        exit 1
    fi
    
    # Check disk space
    local available_space=$(df /var | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # 5GB
        log_error "Insufficient disk space (minimum 5GB required)"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

validate_configuration() {
    log "Validating deployment configuration..."
    
    # Check configuration files
    if [ ! -f "$PROJECT_ROOT/.env.production" ]; then
        log_error "Production environment file not found: .env.production"
        exit 1
    fi
    
    # Validate Docker image
    local image="${DOCKER_IMAGE:-xai-blockchain:latest}"
    if ! docker image inspect "$image" &>/dev/null; then
        log_warning "Docker image not found locally: $image"
        log "Pulling Docker image..."
        docker pull "$image"
    fi
    
    log_success "Configuration validation passed"
}

# ============================================================================
# Pre-Deployment Tasks
# ============================================================================

create_backup() {
    log "Creating pre-deployment backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if command -v pg_dump &>/dev/null; then
        log "Backing up PostgreSQL database..."
        pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" \
            | gzip > "$BACKUP_DIR/database-$(date +%s).sql.gz"
    fi
    
    # Backup blockchain data
    if [ -d "/var/lib/xai/blockchain" ]; then
        log "Backing up blockchain data..."
        tar -czf "$BACKUP_DIR/blockchain-$(date +%s).tar.gz" /var/lib/xai/blockchain
    fi
    
    # Backup configuration
    if [ -d "/etc/xai" ]; then
        log "Backing up configuration..."
        tar -czf "$BACKUP_DIR/config-$(date +%s).tar.gz" /etc/xai
    fi
    
    log_success "Backups created in $BACKUP_DIR"
}

run_health_checks_before() {
    log "Running pre-deployment health checks..."
    
    # Check Docker daemon
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check current services
    if systemctl is-active --quiet xai-node 2>/dev/null; then
        log "Current blockchain node status: running"
    fi
    
    # Test connectivity
    if ! ping -c 1 "$(getent hosts ${POSTGRES_HOST:-localhost} | awk '{print $1}')" &>/dev/null; then
        log_warning "Could not reach database host"
    fi
    
    log_success "Pre-deployment health checks passed"
}

# ============================================================================
# Deployment Tasks
# ============================================================================

deploy_infrastructure() {
    log "Deploying infrastructure with Terraform..."
    
    cd "$PROJECT_ROOT/deploy/terraform"
    
    # Initialize Terraform
    terraform init -upgrade
    
    # Plan deployment
    log "Planning infrastructure changes..."
    terraform plan -var-file="environments/${ENVIRONMENT:-production}.tfvars" \
                   -out=tfplan
    
    # Apply deployment
    log "Applying infrastructure changes..."
    terraform apply tfplan
    
    # Export outputs
    terraform output -json > "$BACKUP_DIR/terraform-outputs.json"
    
    log_success "Infrastructure deployment completed"
}

deploy_ansible() {
    log "Running Ansible deployment..."
    
    cd "$PROJECT_ROOT/deploy/ansible"
    
    # Validate playbook syntax
    log "Validating Ansible playbook..."
    ansible-playbook --syntax-check site.yml
    
    # Run playbook
    log "Executing Ansible playbook..."
    ansible-playbook -i "inventory/${ENVIRONMENT:-production}.yml" \
                     site.yml \
                     --extra-vars "deployment_version=$DEPLOYMENT_VERSION" \
                     --extra-vars "environment=$ENVIRONMENT" \
                     -v
    
    log_success "Ansible deployment completed"
}

build_docker_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build blockchain node image
    log "Building blockchain node image..."
    docker build \
        --tag "xai-blockchain:$DEPLOYMENT_VERSION" \
        --tag "xai-blockchain:latest" \
        -f Dockerfile.prod \
        .
    
    # Build explorer image
    if [ -f "docker/explorer/Dockerfile" ]; then
        log "Building block explorer image..."
        docker build \
            --tag "xai-explorer:$DEPLOYMENT_VERSION" \
            --tag "xai-explorer:latest" \
            -f docker/explorer/Dockerfile \
            .
    fi
    
    log_success "Docker images built successfully"
}

# ============================================================================
# Post-Deployment Tasks
# ============================================================================

run_health_checks_after() {
    log "Running post-deployment health checks..."
    
    # Wait for services to stabilize
    sleep 10
    
    # Check blockchain node health
    log "Checking blockchain node health..."
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
        exit 1
    fi
    
    # Check API connectivity
    log "Checking API connectivity..."
    if curl -sf http://localhost:8080/api/v1/network/info &>/dev/null; then
        log_success "API is responding"
    else
        log_error "API is not responding"
        exit 1
    fi
    
    # Check database connectivity
    log "Checking database connectivity..."
    if pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER" &>/dev/null; then
        log_success "Database is accessible"
    else
        log_warning "Database connectivity check failed"
    fi
    
    log_success "Post-deployment health checks passed"
}

run_smoke_tests() {
    log "Running smoke tests..."
    
    # Test API endpoints
    local endpoints=(
        "/health"
        "/api/v1/network/info"
        "/api/v1/blockchain/info"
    )
    
    for endpoint in "${endpoints[@]}"; do
        log "Testing endpoint: $endpoint"
        if ! curl -sf "http://localhost:8080$endpoint" &>/dev/null; then
            log_error "Endpoint test failed: $endpoint"
            exit 1
        fi
    done
    
    log_success "Smoke tests passed"
}

# ============================================================================
# Rollback Function
# ============================================================================

rollback() {
    log_warning "Initiating deployment rollback..."
    
    if [ -f "$BACKUP_DIR/terraform-outputs.json" ]; then
        log "Rolling back Terraform changes..."
        cd "$PROJECT_ROOT/deploy/terraform"
        terraform destroy -auto-approve -var-file="environments/${ENVIRONMENT:-production}.tfvars" || true
    fi
    
    if [ -f "$BACKUP_DIR/database-"*.sql.gz ]; then
        log "Restoring database backup..."
        latest_backup=$(ls -t "$BACKUP_DIR"/database-*.sql.gz | head -1)
        gunzip -c "$latest_backup" | psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" || true
    fi
    
    log_success "Rollback completed"
}

# ============================================================================
# Deployment Summary
# ============================================================================

generate_summary() {
    log "Generating deployment summary..."
    
    local summary_file="$BACKUP_DIR/deployment-summary.txt"
    cat > "$summary_file" << EOF
XAI Blockchain Deployment Summary
==================================
Deployment Date: $(date)
Environment: ${ENVIRONMENT:-production}
Version: $DEPLOYMENT_VERSION
Deployment User: $USER

Services Deployed:
- Blockchain Node (Port: 8333)
- REST API (Port: 8080)
- WebSocket API (Port: 8081)
- Metrics (Port: 9090)
- Block Explorer (Port: 8082)
- Prometheus (Port: 9091)
- Grafana (Port: 3000)

Database:
- Host: $POSTGRES_HOST
- Database: $POSTGRES_DB

Backups:
- Location: $BACKUP_DIR
- Retention: 30 days

Logs:
- Deployment Log: $DEPLOY_LOG

Status: SUCCESS
EOF
    
    cat "$summary_file" | tee -a "$DEPLOY_LOG"
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log "=========================================="
    log "XAI Blockchain Deployment Started"
    log "=========================================="
    log "Environment: ${ENVIRONMENT:-production}"
    log "Version: ${DEPLOYMENT_VERSION:-latest}"
    log "User: $USER"
    log "Timestamp: $(date)"
    
    acquire_lock
    
    # Pre-deployment
    validate_environment
    validate_configuration
    create_backup
    run_health_checks_before
    
    # Deployment
    build_docker_images
    deploy_infrastructure
    deploy_ansible
    
    # Post-deployment
    run_health_checks_after
    run_smoke_tests
    
    # Summary
    generate_summary
    
    log_success "=========================================="
    log_success "Deployment completed successfully!"
    log_success "=========================================="
}

# ============================================================================
# Script Entry Point
# ============================================================================

ENVIRONMENT="${1:-production}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_USER="${POSTGRES_USER:-xai}"
POSTGRES_DB="${POSTGRES_DB:-xai_blockchain}"

main "$@"
