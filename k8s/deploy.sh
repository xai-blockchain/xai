#!/bin/bash

################################################################################
# XAI Blockchain Kubernetes Deployment Script
#
# Usage: ./deploy.sh [options]
# Options:
#   --namespace      Kubernetes namespace (default: xai-blockchain)
#   --image          Docker image URL (default: xai-blockchain:latest)
#   --replicas       Number of replicas (default: 3, min: 3, max: 10)
#   --help          Show this help message
################################################################################

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="xai-blockchain"
IMAGE="xai-blockchain:latest"
REPLICAS=3
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    grep "^# " "$0" | sed 's/^# //'
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    log_success "kubectl found: $(kubectl version --client --short)"

    # Check Kubernetes cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster."
        exit 1
    fi
    log_success "Connected to Kubernetes cluster"

    # Check required namespaces/addons
    if ! kubectl get ns ingress-nginx &> /dev/null; then
        log_warning "ingress-nginx namespace not found. Installing ingress-nginx..."
        install_ingress_nginx
    else
        log_success "ingress-nginx addon found"
    fi

    # Check cert-manager
    if ! kubectl get ns cert-manager &> /dev/null; then
        log_warning "cert-manager not found. Installing cert-manager..."
        install_cert_manager
    else
        log_success "cert-manager addon found"
    fi
}

install_ingress_nginx() {
    log_info "Installing ingress-nginx..."

    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install helm first."
        exit 1
    fi

    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    helm repo update
    helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
        -n ingress-nginx --create-namespace \
        --set controller.service.type=LoadBalancer \
        --wait

    log_success "ingress-nginx installed"
}

install_cert_manager() {
    log_info "Installing cert-manager..."

    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Please install helm first."
        exit 1
    fi

    helm repo add jetstack https://charts.jetstack.io
    helm repo update
    helm upgrade --install cert-manager jetstack/cert-manager \
        -n cert-manager --create-namespace \
        --set installCRDs=true \
        --wait

    log_success "cert-manager installed"
}

validate_configuration() {
    log_info "Validating configuration..."

    # Validate image
    if [ -z "$IMAGE" ]; then
        log_error "Docker image not specified"
        exit 1
    fi
    log_success "Image: $IMAGE"

    # Validate replicas
    if [ "$REPLICAS" -lt 3 ] || [ "$REPLICAS" -gt 10 ]; then
        log_error "Replicas must be between 3 and 10 (got: $REPLICAS)"
        exit 1
    fi
    log_success "Replicas: $REPLICAS"

    # Check required manifests
    local required_files=(
        "namespace.yaml"
        "rbac.yaml"
        "pv.yaml"
        "configmap.yaml"
        "secret.yaml"
        "statefulset.yaml"
        "service.yaml"
        "ingress.yaml"
        "monitoring.yaml"
        "hpa.yaml"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$SCRIPT_DIR/$file" ]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    log_success "All required manifest files found"
}

create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    kubectl apply -f "$SCRIPT_DIR/namespace.yaml"

    # Wait for namespace
    kubectl wait --for=condition=active namespace/$NAMESPACE --timeout=30s 2>/dev/null || true
    log_success "Namespace created"
}

deploy_security() {
    log_info "Deploying RBAC and security policies..."
    kubectl apply -f "$SCRIPT_DIR/rbac.yaml"
    kubectl wait --for=condition=ready pod -l app=xai-blockchain --namespace=$NAMESPACE --timeout=60s 2>/dev/null || true
    log_success "Security policies deployed"
}

deploy_storage() {
    log_info "Deploying persistent storage..."
    kubectl apply -f "$SCRIPT_DIR/pv.yaml"
    log_success "Storage configured"
}

deploy_configuration() {
    log_info "Deploying configuration..."
    kubectl apply -f "$SCRIPT_DIR/configmap.yaml"
    log_success "Configuration deployed"
}

deploy_secrets() {
    log_info "Deploying secrets..."

    if ! kubectl get secret xai-blockchain-secrets -n $NAMESPACE &> /dev/null; then
        log_warning "Creating secrets from template (IMPORTANT: Update with real values!)"
        kubectl apply -f "$SCRIPT_DIR/secret.yaml"
    else
        log_info "Secrets already exist"
    fi

    log_success "Secrets configured"
}

update_image_in_manifest() {
    log_info "Updating Docker image in manifests..."

    # Create temporary file with updated image
    local temp_file=$(mktemp)
    sed "s|image: xai-blockchain:latest|image: $IMAGE|g" "$SCRIPT_DIR/statefulset.yaml" > "$temp_file"

    # Compare and show changes
    if ! diff -q "$SCRIPT_DIR/statefulset.yaml" "$temp_file" > /dev/null 2>&1; then
        log_info "Image updated to: $IMAGE"
    fi

    rm "$temp_file"
}

deploy_application() {
    log_info "Deploying XAI Blockchain StatefulSet..."

    # Create temporary manifest with updated image and replicas
    local temp_file=$(mktemp)
    sed "s|image: xai-blockchain:latest|image: $IMAGE|g; s|replicas: 3|replicas: $REPLICAS|g" \
        "$SCRIPT_DIR/statefulset.yaml" > "$temp_file"

    kubectl apply -f "$temp_file"
    rm "$temp_file"

    log_success "StatefulSet deployed"
}

deploy_services() {
    log_info "Deploying services..."
    kubectl apply -f "$SCRIPT_DIR/service.yaml"
    log_success "Services deployed"
}

deploy_ingress() {
    log_info "Deploying ingress..."
    kubectl apply -f "$SCRIPT_DIR/ingress.yaml"
    log_success "Ingress deployed"
}

deploy_monitoring() {
    log_info "Deploying monitoring..."
    kubectl apply -f "$SCRIPT_DIR/monitoring.yaml"
    log_success "Monitoring deployed"
}

deploy_autoscaling() {
    log_info "Deploying horizontal pod autoscaler..."
    kubectl apply -f "$SCRIPT_DIR/hpa.yaml"
    log_success "Autoscaler deployed"
}

wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."

    local timeout=300
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        local ready=$(kubectl get statefulset xai-blockchain-node -n $NAMESPACE -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo 0)
        local desired=$(kubectl get statefulset xai-blockchain-node -n $NAMESPACE -o jsonpath='{.spec.replicas}' 2>/dev/null || echo 0)

        if [ "$ready" = "$desired" ] && [ "$ready" -gt 0 ]; then
            log_success "All replicas are ready ($ready/$desired)"
            return 0
        fi

        echo -ne "\r${BLUE}[INFO]${NC} Waiting for pods to be ready... ($ready/$desired) - ${elapsed}s/${timeout}s"
        sleep 5
        elapsed=$((elapsed + 5))
    done

    log_warning "Deployment did not reach ready state within timeout"
    return 1
}

print_deployment_info() {
    log_success "Deployment completed!"
    echo ""
    echo -e "${BLUE}=== XAI Blockchain Deployment Info ===${NC}"
    echo ""

    echo -e "${BLUE}Namespace:${NC} $NAMESPACE"
    echo -e "${BLUE}Replicas:${NC} $REPLICAS"
    echo -e "${BLUE}Image:${NC} $IMAGE"
    echo ""

    echo -e "${BLUE}=== Services ===${NC}"
    kubectl get svc -n $NAMESPACE
    echo ""

    echo -e "${BLUE}=== Pods ===${NC}"
    kubectl get pods -n $NAMESPACE
    echo ""

    echo -e "${BLUE}=== Ingress ===${NC}"
    kubectl get ingress -n $NAMESPACE
    echo ""

    echo -e "${BLUE}=== Useful Commands ===${NC}"
    echo "View logs:          kubectl logs -n $NAMESPACE xai-blockchain-node-0"
    echo "Describe pod:       kubectl describe pod -n $NAMESPACE xai-blockchain-node-0"
    echo "Port-forward RPC:   kubectl port-forward -n $NAMESPACE svc/xai-blockchain-rpc 8546:8546"
    echo "Port-forward P2P:   kubectl port-forward -n $NAMESPACE svc/xai-blockchain-p2p 30303:30303"
    echo "Watch pods:         kubectl get pods -n $NAMESPACE --watch"
    echo "Check HPA status:   kubectl get hpa -n $NAMESPACE"
    echo "View metrics:       kubectl top pods -n $NAMESPACE"
    echo ""
}

# Main deployment flow
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --image)
                IMAGE="$2"
                shift 2
                ;;
            --replicas)
                REPLICAS="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_info "Starting XAI Blockchain Kubernetes deployment..."
    echo ""

    check_prerequisites
    validate_configuration

    echo ""
    log_info "Deploying to namespace: $NAMESPACE"
    echo ""

    create_namespace
    deploy_security
    deploy_storage
    deploy_configuration
    deploy_secrets
    deploy_application
    deploy_services
    deploy_ingress
    deploy_monitoring
    deploy_autoscaling

    echo ""
    wait_for_deployment
    echo ""

    print_deployment_info
}

# Run main function
main "$@"
