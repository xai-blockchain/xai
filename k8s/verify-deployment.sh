#!/bin/bash

################################################################################
# XAI Blockchain Kubernetes Deployment Verification Script
#
# This script verifies the deployment is working correctly
# Usage: ./verify-deployment.sh [--namespace=xai-blockchain]
################################################################################

set -e

# Configuration
NAMESPACE="${1:--n xai-blockchain}"
NAMESPACE="${NAMESPACE#*=}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

# Test functions
test_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

test_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

test_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN++))
}

test_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Verification tests
verify_namespace() {
    test_info "Verifying namespace..."

    if kubectl get ns $NAMESPACE &> /dev/null; then
        test_pass "Namespace $NAMESPACE exists"
    else
        test_fail "Namespace $NAMESPACE does not exist"
        return 1
    fi
}

verify_statefulset() {
    test_info "Verifying StatefulSet..."

    local ss=$(kubectl get statefulset -n $NAMESPACE xai-blockchain-node 2>/dev/null)
    if [ -z "$ss" ]; then
        test_fail "StatefulSet xai-blockchain-node not found"
        return 1
    fi

    test_pass "StatefulSet xai-blockchain-node exists"

    local replicas=$(kubectl get statefulset -n $NAMESPACE xai-blockchain-node -o jsonpath='{.spec.replicas}')
    local ready=$(kubectl get statefulset -n $NAMESPACE xai-blockchain-node -o jsonpath='{.status.readyReplicas}')

    if [ "$ready" = "$replicas" ]; then
        test_pass "All replicas are ready ($ready/$replicas)"
    else
        test_warn "Not all replicas are ready ($ready/$replicas)"
    fi
}

verify_pods() {
    test_info "Verifying Pods..."

    local running=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase=Running --no-headers | wc -l)
    local total=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --no-headers | wc -l)

    if [ "$running" -gt 0 ]; then
        test_pass "$running out of $total pods are running"
    else
        test_fail "No pods are running"
        return 1
    fi

    # Check pod health
    local unhealthy=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase!=Running --no-headers | wc -l)
    if [ "$unhealthy" -gt 0 ]; then
        test_warn "$unhealthy pods are not in Running state"
        kubectl get pods -n $NAMESPACE -l app=xai-blockchain
    fi
}

verify_services() {
    test_info "Verifying Services..."

    local services=("xai-blockchain-headless" "xai-blockchain-p2p" "xai-blockchain-rpc" "xai-blockchain-ws" "xai-blockchain-metrics")

    for service in "${services[@]}"; do
        if kubectl get svc $service -n $NAMESPACE &> /dev/null; then
            test_pass "Service $service exists"
        else
            test_fail "Service $service not found"
        fi
    done
}

verify_ingress() {
    test_info "Verifying Ingress..."

    if kubectl get ingress xai-blockchain-ingress -n $NAMESPACE &> /dev/null; then
        test_pass "Ingress xai-blockchain-ingress exists"

        local ingress_ip=$(kubectl get ingress xai-blockchain-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
        if [ "$ingress_ip" != "pending" ] && [ ! -z "$ingress_ip" ]; then
            test_pass "Ingress has external IP: $ingress_ip"
        else
            test_warn "Ingress does not have external IP assigned yet (this is normal if using DNS)"
        fi
    else
        test_fail "Ingress xai-blockchain-ingress not found"
    fi
}

verify_storage() {
    test_info "Verifying Persistent Storage..."

    # Check PVCs
    local pvcs=$(kubectl get pvc -n $NAMESPACE -l app=xai-blockchain --no-headers 2>/dev/null | wc -l)
    if [ "$pvcs" -gt 0 ]; then
        test_pass "$pvcs PersistentVolumeClaims exist"

        # Check PVC binding
        local bound=$(kubectl get pvc -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase=Bound --no-headers 2>/dev/null | wc -l)
        if [ "$bound" = "$pvcs" ]; then
            test_pass "All PVCs are bound"
        else
            test_warn "$bound out of $pvcs PVCs are bound"
        fi

        # Check PVC usage
        test_info "Storage usage:"
        kubectl exec -it xai-blockchain-node-0 -n $NAMESPACE -- df -h /data/blockchain 2>/dev/null || test_warn "Cannot check storage usage"
    else
        test_fail "No PersistentVolumeClaims found"
    fi
}

verify_configmap() {
    test_info "Verifying ConfigMap..."

    if kubectl get configmap xai-blockchain-config -n $NAMESPACE &> /dev/null; then
        test_pass "ConfigMap xai-blockchain-config exists"
    else
        test_fail "ConfigMap xai-blockchain-config not found"
    fi
}

verify_secrets() {
    test_info "Verifying Secrets..."

    if kubectl get secret xai-blockchain-secrets -n $NAMESPACE &> /dev/null; then
        test_pass "Secret xai-blockchain-secrets exists"
    else
        test_fail "Secret xai-blockchain-secrets not found"
    fi

    if kubectl get secret xai-blockchain-tls -n $NAMESPACE &> /dev/null; then
        test_pass "Secret xai-blockchain-tls exists"
    else
        test_warn "Secret xai-blockchain-tls not found (using cert-manager?)"
    fi
}

verify_monitoring() {
    test_info "Verifying Monitoring..."

    if kubectl get servicemonitor -n $NAMESPACE &> /dev/null; then
        test_pass "ServiceMonitor exists"
    else
        test_warn "ServiceMonitor not found"
    fi

    if kubectl get prometheusrule -n $NAMESPACE &> /dev/null; then
        test_pass "PrometheusRule exists"
    else
        test_warn "PrometheusRule not found"
    fi
}

verify_p2p_metrics() {
    test_info "Verifying P2P security metrics exposure..."
    local pod
    pod=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [ -z "$pod" ]; then
        test_warn "No pods available to check metrics"
        return
    fi
    if kubectl exec -n $NAMESPACE "$pod" -- sh -c "curl -s http://localhost:9090/metrics | grep xai_p2p_nonce_replay_total" >/dev/null 2>&1; then
        test_pass "P2P metrics exposed on /metrics (nonce replay counter present)"
    else
        test_warn "P2P metrics not found on /metrics; check metrics configuration"
    fi
}

verify_siem_webhook() {
    test_info "Verifying SIEM webhook (if configured)..."
    local url
    url=$(kubectl get configmap xai-blockchain-config -n $NAMESPACE -o jsonpath='{.data.XAI_SECURITY_WEBHOOK_URL}' 2>/dev/null || echo "")
    if [ -z "$url" ]; then
        test_warn "XAI_SECURITY_WEBHOOK_URL not set in ConfigMap; skipping SIEM webhook probe"
        return
    fi

    if kubectl exec -n $NAMESPACE "$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain -o jsonpath='{.items[0].metadata.name}')" -- sh -c "curl -sf -m 5 -X POST -H 'Content-Type: application/json' -d '{\"event_type\":\"p2p.siem_probe\",\"severity\":\"WARNING\",\"details\":{\"probe\":\"verify-deployment\"}}' $url" >/dev/null 2>&1; then
        test_pass "SIEM webhook probe delivered successfully"
    else
        test_warn "SIEM webhook probe failed (check webhook URL/secret)"
    fi
}

verify_hpa() {
    test_info "Verifying Horizontal Pod Autoscaler..."

    if kubectl get hpa xai-blockchain-hpa -n $NAMESPACE &> /dev/null; then
        test_pass "HorizontalPodAutoscaler exists"

        # Check HPA status
        local desired=$(kubectl get hpa xai-blockchain-hpa -n $NAMESPACE -o jsonpath='{.status.desiredReplicas}' 2>/dev/null || echo "unknown")
        local current=$(kubectl get hpa xai-blockchain-hpa -n $NAMESPACE -o jsonpath='{.status.currentReplicas}' 2>/dev/null || echo "unknown")

        test_info "HPA status: current=$current, desired=$desired"
    else
        test_fail "HorizontalPodAutoscaler not found"
    fi
}

verify_rbac() {
    test_info "Verifying RBAC..."

    if kubectl get sa xai-blockchain-sa -n $NAMESPACE &> /dev/null; then
        test_pass "ServiceAccount xai-blockchain-sa exists"
    else
        test_fail "ServiceAccount xai-blockchain-sa not found"
    fi

    if kubectl get role xai-blockchain-role -n $NAMESPACE &> /dev/null; then
        test_pass "Role xai-blockchain-role exists"
    else
        test_fail "Role xai-blockchain-role not found"
    fi

    if kubectl get rolebinding xai-blockchain-rolebinding -n $NAMESPACE &> /dev/null; then
        test_pass "RoleBinding xai-blockchain-rolebinding exists"
    else
        test_fail "RoleBinding xai-blockchain-rolebinding not found"
    fi
}

verify_network_policies() {
    test_info "Verifying Network Policies..."

    local netpols=$(kubectl get networkpolicy -n $NAMESPACE -l app=xai-blockchain --no-headers 2>/dev/null | wc -l)
    if [ "$netpols" -gt 0 ]; then
        test_pass "$netpols NetworkPolicies exist"
    else
        test_warn "No NetworkPolicies found"
    fi
}

verify_pod_health() {
    test_info "Verifying Pod Health..."

    # Check for pod errors
    local pods=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null)

    for pod in $pods; do
        local restarts=$(kubectl get pod $pod -n $NAMESPACE -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo "0")
        if [ "$restarts" -gt 0 ]; then
            test_warn "Pod $pod has restarted $restarts times"
        else
            test_pass "Pod $pod is healthy (0 restarts)"
        fi
    done
}

verify_connectivity() {
    test_info "Verifying Connectivity..."

    # Test DNS resolution
    if kubectl run --rm -it --image=busybox --restart=Never -- nslookup xai-blockchain-headless.xai-blockchain &> /dev/null; then
        test_pass "DNS resolution working"
    else
        test_warn "Cannot verify DNS resolution"
    fi

    # Test inter-pod connectivity
    local ready_pods=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase=Running -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null | wc -l)
    if [ "$ready_pods" -ge 2 ]; then
        local pod1=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        local pod2=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase=Running -o jsonpath='{.items[1].metadata.name}' 2>/dev/null)

        if [ ! -z "$pod1" ] && [ ! -z "$pod2" ]; then
            test_info "Testing connectivity between pods..."
            # This is a basic test - may not work depending on network policies
        fi
    fi
}

verify_resource_usage() {
    test_info "Verifying Resource Usage..."

    # Check CPU and memory usage
    if kubectl top pods -n $NAMESPACE &> /dev/null; then
        echo ""
        kubectl top pods -n $NAMESPACE -l app=xai-blockchain 2>/dev/null | grep -v "NAME" | while read line; do
            test_info "$line"
        done
    else
        test_warn "Metrics server not available (install metrics-server)"
    fi
}

verify_logs() {
    test_info "Verifying Logs..."

    # Check for errors in logs
    local pod=$(kubectl get pods -n $NAMESPACE -l app=xai-blockchain --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ ! -z "$pod" ]; then
        local errors=$(kubectl logs $pod -n $NAMESPACE --tail=100 2>/dev/null | grep -i error | wc -l)

        if [ "$errors" -gt 0 ]; then
            test_warn "Found $errors error messages in recent logs"
        else
            test_pass "No errors found in recent logs"
        fi
    fi
}

# Summary
print_summary() {
    echo ""
    echo -e "${BLUE}=== Verification Summary ===${NC}"
    echo -e "Passed:  ${GREEN}$PASS${NC}"
    echo -e "Failed:  ${RED}$FAIL${NC}"
    echo -e "Warned:  ${YELLOW}$WARN${NC}"
    echo ""

    if [ $FAIL -eq 0 ]; then
        echo -e "${GREEN}All critical checks passed!${NC}"
        return 0
    else
        echo -e "${RED}Some critical checks failed. Please review the output above.${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}=== XAI Blockchain Kubernetes Deployment Verification ===${NC}"
    echo ""
    echo "Namespace: $NAMESPACE"
    echo ""

    # Verify cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        test_fail "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    test_pass "Connected to Kubernetes cluster"
    echo ""

    # Run verification tests
    verify_namespace
    echo ""
    verify_statefulset
    echo ""
    verify_pods
    echo ""
    verify_services
    echo ""
    verify_ingress
    echo ""
    verify_storage
    echo ""
    verify_configmap
    echo ""
    verify_secrets
    echo ""
    verify_monitoring
    echo ""
    verify_hpa
    echo ""
    verify_rbac
    echo ""
    verify_network_policies
    echo ""
    verify_pod_health
    echo ""
    verify_connectivity
    echo ""
    verify_resource_usage
    echo ""
    verify_logs
    echo ""

    print_summary
}

# Run main
main "$@"
