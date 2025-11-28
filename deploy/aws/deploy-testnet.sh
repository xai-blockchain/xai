#!/bin/bash
# XAI Blockchain Testnet Deployment Script
# Deploys the complete testnet infrastructure to AWS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found. Please install: https://www.terraform.io/downloads"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi

    log_info "Prerequisites check passed ✓"
}

# Initialize Terraform
init_terraform() {
    log_info "Initializing Terraform..."
    cd terraform
    terraform init
    cd ..
}

# Plan deployment
plan_deployment() {
    log_info "Planning deployment..."
    cd terraform
    terraform plan -out=tfplan
    cd ..

    log_warn "Review the plan above. Press Enter to continue or Ctrl+C to cancel..."
    read
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure..."
    cd terraform
    terraform apply tfplan
    cd ..

    log_info "Infrastructure deployed successfully ✓"
}

# Get deployment outputs
get_outputs() {
    log_info "Retrieving deployment information..."
    cd terraform

    API_ENDPOINT=$(terraform output -raw api_endpoint)
    echo ""
    echo "========================================="
    echo "XAI TESTNET DEPLOYMENT COMPLETE"
    echo "========================================="
    echo ""
    echo "API Endpoint:    $API_ENDPOINT"
    echo "Block Explorer:  $API_ENDPOINT/explorer"
    echo "Faucet:          $API_ENDPOINT/faucet"
    echo "Metrics:         $API_ENDPOINT/metrics"
    echo ""
    echo "========================================="
    echo ""

    # Save outputs to file
    terraform output -json > ../deployment-info.json
    cd ..

    log_info "Deployment info saved to: deployment-info.json"
}

# Wait for nodes to be healthy
wait_for_nodes() {
    log_info "Waiting for nodes to become healthy..."

    cd terraform
    API_ENDPOINT=$(terraform output -raw api_endpoint)
    cd ..

    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s "$API_ENDPOINT/health" | grep -q "healthy"; then
            log_info "Nodes are healthy ✓"
            return 0
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_info "Waiting for nodes... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 10
    done

    log_warn "Nodes took longer than expected to become healthy"
    log_warn "Check CloudWatch logs for details"
}

# Run smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."

    cd terraform
    API_ENDPOINT=$(terraform output -raw api_endpoint)
    cd ..

    # Test API health
    log_info "Testing API health endpoint..."
    curl -s "$API_ENDPOINT/health" | jq .

    # Test blockchain info
    log_info "Testing blockchain info endpoint..."
    curl -s "$API_ENDPOINT/blockchain/info" | jq .

    # Test wallet creation
    log_info "Testing wallet creation..."
    curl -s -X POST "$API_ENDPOINT/wallet/create" | jq .

    log_info "Smoke tests completed ✓"
}

# Main deployment flow
main() {
    echo ""
    echo "========================================="
    echo "XAI BLOCKCHAIN TESTNET DEPLOYMENT"
    echo "========================================="
    echo ""

    check_prerequisites
    init_terraform
    plan_deployment
    deploy_infrastructure
    get_outputs
    wait_for_nodes
    run_smoke_tests

    echo ""
    echo "========================================="
    echo "DEPLOYMENT SUCCESSFUL!"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "1. Access block explorer: $(cd terraform && terraform output -raw api_endpoint)/explorer"
    echo "2. Request test tokens from faucet"
    echo "3. Review monitoring dashboards"
    echo "4. Read testnet documentation: ../docs/TESTNET_GUIDE.md"
    echo ""
}

# Run main function
main
