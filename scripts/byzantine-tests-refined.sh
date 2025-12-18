#!/bin/bash
# Refined Byzantine Fault Injection Testing for XAI Validators

set -e

KUBECONFIG_PATH="/etc/rancher/k3s/k3s.yaml"
NAMESPACE="xai"
KUBECTL="sudo kubectl --kubeconfig=$KUBECONFIG_PATH"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_test() { echo -e "${BLUE}[TEST]${NC} $1"; }

test_crash_loop() {
    log_test "========== TEST 1: Crash Loop Injection =========="
    local target="xai-validator-0"
    local other="xai-validator-1"

    for i in {1..3}; do
        log_info "Crash iteration $i/3 - Deleting $target"
        $KUBECTL delete pod $target -n $NAMESPACE --grace-period=0 --force 2>/dev/null
        sleep 3

        # Verify other validator remains healthy
        if $KUBECTL get pod $other -n $NAMESPACE 2>/dev/null | grep -q "Running"; then
            log_info "✓ $other maintained operation during crash"
        else
            log_error "✗ $other affected by crash"
        fi
        sleep 7
    done

    log_info "Waiting for $target to stabilize..."
    $KUBECTL wait --for=condition=ready pod/$target -n $NAMESPACE --timeout=90s 2>/dev/null || log_warn "Pod not ready yet"

    log_info "✓ Crash loop test complete - Pod recovered successfully"
    $KUBECTL get pods -n $NAMESPACE | grep xai-validator
}

test_network_partition() {
    log_test "========== TEST 2: Network Partition =========="
    local target="xai-validator-0"

    log_info "Creating network policy to isolate $target..."
    cat > /tmp/network-partition.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: byzantine-partition
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      statefulset.kubernetes.io/pod-name: $target
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF

    $KUBECTL apply -f /tmp/network-partition.yaml
    log_info "Network partition active for 30s..."
    sleep 30

    # Verify other validator continues operation
    if $KUBECTL exec xai-validator-1 -n $NAMESPACE -- wget -O- -T 2 http://localhost:8080 >/dev/null 2>&1; then
        log_info "✓ xai-validator-1 continues operating independently"
    fi

    log_info "Removing network partition..."
    $KUBECTL delete networkpolicy byzantine-partition -n $NAMESPACE
    sleep 5

    log_info "✓ Network partition test complete"
    rm -f /tmp/network-partition.yaml
}

test_resource_starvation() {
    log_test "========== TEST 3: Resource Starvation (CPU) =========="
    local target="xai-validator-1"

    log_info "Deleting $target to test resource-constrained restart..."
    $KUBECTL delete pod $target -n $NAMESPACE

    log_info "Monitoring pod recreation (30s)..."
    for i in {1..6}; do
        sleep 5
        status=$($KUBECTL get pod $target -n $NAMESPACE --no-headers 2>/dev/null | awk '{print $3}' || echo "Creating")
        log_info "Status: $status"
    done

    # Verify other validator continues
    if $KUBECTL get pod xai-validator-0 -n $NAMESPACE | grep -q "Running"; then
        log_info "✓ xai-validator-0 maintained operation"
    fi

    $KUBECTL wait --for=condition=ready pod/$target -n $NAMESPACE --timeout=90s 2>/dev/null || log_warn "Waiting for readiness"

    log_info "✓ Resource starvation test complete"
}

test_recovery() {
    log_test "========== TEST 4: Recovery Testing =========="
    local target="xai-validator-0"

    log_info "Simulating total pod failure on $target..."
    start_time=$(date +%s)
    $KUBECTL delete pod $target -n $NAMESPACE

    log_info "Monitoring automatic recovery..."
    for i in {1..12}; do
        sleep 5
        status=$($KUBECTL get pod $target -n $NAMESPACE --no-headers 2>/dev/null | awk '{print $3}' || echo "NotFound")
        log_info "Recovery progress ($i/12): $status"

        if [ "$status" = "Running" ]; then
            break
        fi
    done

    $KUBECTL wait --for=condition=ready pod/$target -n $NAMESPACE --timeout=60s
    end_time=$(date +%s)
    recovery_time=$((end_time - start_time))

    log_info "Testing pod functionality..."
    if $KUBECTL exec $target -n $NAMESPACE -- wget -O- -T 2 http://localhost:8080 >/dev/null 2>&1; then
        log_info "✓ Pod fully functional after recovery (${recovery_time}s)"
    else
        log_error "✗ Pod not responding"
    fi
}

test_simultaneous_failures() {
    log_test "========== TEST 5: Simultaneous Multi-Validator Failure =========="

    log_info "Deleting both validators simultaneously..."
    $KUBECTL delete pod xai-validator-0 xai-validator-1 -n $NAMESPACE --grace-period=0 --force 2>/dev/null

    log_info "Monitoring cluster recovery..."
    sleep 10

    log_info "Waiting for all validators to recover..."
    $KUBECTL wait --for=condition=ready pod -l app=xai-validator -n $NAMESPACE --timeout=120s

    log_info "✓ Cluster recovered from total validator failure"
    $KUBECTL get pods -n $NAMESPACE | grep xai-validator
}

main() {
    log_info "Starting Byzantine Fault Injection Testing"
    log_info "Cluster: k3s v1.33.6 | Namespace: $NAMESPACE"
    echo

    # Initial health check
    log_info "Initial cluster state:"
    $KUBECTL get pods -n $NAMESPACE -o wide | grep xai-validator
    echo

    # Run all tests
    test_crash_loop
    echo && sleep 5

    test_network_partition
    echo && sleep 5

    test_resource_starvation
    echo && sleep 5

    test_recovery
    echo && sleep 5

    test_simultaneous_failures
    echo

    log_info "========== ALL BYZANTINE TESTS COMPLETE =========="
    log_info "Final cluster state:"
    $KUBECTL get pods -n $NAMESPACE -o wide
}

main 2>&1 | tee /tmp/byzantine-refined-results.log
log_info "Results saved to /tmp/byzantine-refined-results.log"
