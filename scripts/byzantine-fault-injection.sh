#!/bin/bash
# Byzantine Fault Injection Testing for XAI Validators
# Tests validator resilience under various Byzantine failure modes

set -e

KUBECONFIG_PATH="/etc/rancher/k3s/k3s.yaml"
NAMESPACE="xai"
KUBECTL="sudo kubectl --kubeconfig=$KUBECONFIG_PATH"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for pod to be ready
wait_for_pod() {
    local pod_name=$1
    local timeout=${2:-120}

    log_info "Waiting for $pod_name to be ready (timeout: ${timeout}s)..."
    $KUBECTL wait --for=condition=ready pod/$pod_name -n $NAMESPACE --timeout=${timeout}s
}

# Check cluster health
check_cluster_health() {
    log_info "Checking cluster health..."
    $KUBECTL get pods -n $NAMESPACE -o wide
    $KUBECTL get statefulset -n $NAMESPACE
}

# Test 1: Crash Loop Injection
test_crash_loop() {
    log_info "========== TEST 1: Crash Loop Injection =========="

    local target_pod="xai-validator-0"
    log_info "Simulating crash loop on $target_pod..."

    # Kill pod 3 times in succession
    for i in {1..3}; do
        log_warn "Crash iteration $i/3"
        $KUBECTL delete pod $target_pod -n $NAMESPACE --grace-period=0 --force
        sleep 5

        # Check if other validator is still running
        local other_pod="xai-validator-1"
        if $KUBECTL get pod $other_pod -n $NAMESPACE &>/dev/null; then
            log_info "$other_pod is still running during crash of $target_pod"
        else
            log_error "$other_pod is down!"
        fi

        sleep 10
    done

    # Wait for recovery
    log_info "Waiting for $target_pod to recover..."
    wait_for_pod $target_pod 120

    log_info "Crash loop test complete. Final state:"
    check_cluster_health
}

# Test 2: Resource Starvation
test_resource_starvation() {
    log_info "========== TEST 2: Resource Starvation =========="

    local target_pod="xai-validator-1"
    log_info "Applying severe CPU throttling to $target_pod..."

    # Create temporary patch to limit CPU to 1m (near-zero)
    cat > /tmp/cpu-starve-patch.yaml <<EOF
spec:
  template:
    spec:
      containers:
      - name: validator
        resources:
          limits:
            cpu: 1m
            memory: 128Mi
          requests:
            cpu: 1m
            memory: 64Mi
EOF

    # Apply patch
    $KUBECTL patch statefulset xai-validator -n $NAMESPACE --patch-file=/tmp/cpu-starve-patch.yaml

    log_info "Waiting for StatefulSet to update..."
    sleep 5

    # Delete pod to force recreation with new limits
    $KUBECTL delete pod $target_pod -n $NAMESPACE --grace-period=0 --force

    log_info "Monitoring pod behavior under CPU starvation (60s)..."
    for i in {1..12}; do
        sleep 5
        $KUBECTL get pod $target_pod -n $NAMESPACE 2>/dev/null || log_warn "Pod not ready yet"
    done

    # Check other validator
    local other_pod="xai-validator-0"
    if $KUBECTL get pod $other_pod -n $NAMESPACE | grep -q "Running"; then
        log_info "$other_pod continues operating normally"
    fi

    # Restore normal resources
    log_info "Restoring normal resource limits..."
    cat > /tmp/cpu-restore-patch.yaml <<EOF
spec:
  template:
    spec:
      containers:
      - name: validator
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
EOF

    $KUBECTL patch statefulset xai-validator -n $NAMESPACE --patch-file=/tmp/cpu-restore-patch.yaml
    $KUBECTL delete pod $target_pod -n $NAMESPACE --grace-period=0 --force

    wait_for_pod $target_pod 120

    log_info "Resource starvation test complete. Final state:"
    check_cluster_health

    rm -f /tmp/cpu-starve-patch.yaml /tmp/cpu-restore-patch.yaml
}

# Test 3: Network Partition
test_network_partition() {
    log_info "========== TEST 3: Network Partition =========="

    local target_pod="xai-validator-0"
    log_info "Creating network policy to isolate $target_pod..."

    # Create deny-all network policy for target pod
    cat > /tmp/network-partition.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: byzantine-partition
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      statefulset.kubernetes.io/pod-name: $target_pod
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF

    $KUBECTL apply -f /tmp/network-partition.yaml

    log_info "Network partition applied. Testing connectivity (30s)..."
    sleep 30

    # Try to curl from validator-1 to validator-0 (should fail)
    log_info "Testing inter-validator connectivity..."
    $KUBECTL exec xai-validator-1 -n $NAMESPACE -- timeout 5 wget -O- http://xai-validator-0.xai-validator.xai.svc.cluster.local:8080 2>&1 || log_warn "Connection blocked as expected"

    # Check that validator-1 is still healthy
    if $KUBECTL get pod xai-validator-1 -n $NAMESPACE | grep -q "Running"; then
        log_info "xai-validator-1 continues operating despite partition"
    fi

    # Remove partition
    log_info "Removing network partition..."
    $KUBECTL delete networkpolicy byzantine-partition -n $NAMESPACE

    sleep 10

    log_info "Network partition test complete. Final state:"
    check_cluster_health

    rm -f /tmp/network-partition.yaml
}

# Test 4: Recovery Testing
test_recovery() {
    log_info "========== TEST 4: Recovery Testing =========="

    local target_pod="xai-validator-1"
    log_info "Simulating complete node failure on $target_pod..."

    # Delete pod and wait for automatic recreation
    $KUBECTL delete pod $target_pod -n $NAMESPACE

    log_info "Monitoring recovery process..."
    sleep 5

    # Monitor recovery in real-time
    for i in {1..24}; do
        sleep 5
        status=$($KUBECTL get pod $target_pod -n $NAMESPACE --no-headers 2>/dev/null | awk '{print $3}' || echo "NotFound")
        log_info "Recovery status ($i/24): $status"

        if [ "$status" = "Running" ]; then
            break
        fi
    done

    wait_for_pod $target_pod 60

    log_info "Testing pod functionality after recovery..."
    $KUBECTL exec $target_pod -n $NAMESPACE -- wget -O- http://localhost:8080 >/dev/null 2>&1 && log_info "Pod is functional" || log_error "Pod is not responding"

    log_info "Recovery test complete. Final state:"
    check_cluster_health
}

# Test 5: Clock Skew Simulation (via pod restart with delay)
test_clock_skew() {
    log_info "========== TEST 5: Clock Skew Simulation =========="
    log_warn "Note: True clock skew requires container runtime manipulation"
    log_info "Simulating via graceful pod restart with delayed startup..."

    local target_pod="xai-validator-0"

    # Get current pod start time
    original_start=$($KUBECTL get pod $target_pod -n $NAMESPACE -o jsonpath='{.status.startTime}')
    log_info "Original start time: $original_start"

    # Delete and monitor restart
    $KUBECTL delete pod $target_pod -n $NAMESPACE

    log_info "Pod restarting - this creates temporal divergence..."
    sleep 20

    wait_for_pod $target_pod 120

    new_start=$($KUBECTL get pod $target_pod -n $NAMESPACE -o jsonpath='{.status.startTime}')
    log_info "New start time: $new_start"

    # Verify other pod was unaffected
    if $KUBECTL get pod xai-validator-1 -n $NAMESPACE | grep -q "Running"; then
        log_info "xai-validator-1 maintained continuous operation"
    fi

    log_info "Clock skew simulation complete. Final state:"
    check_cluster_health
}

# Main execution
main() {
    log_info "Starting Byzantine Fault Injection Testing for XAI Validators"
    log_info "Cluster: k3s v1.33.6"
    log_info "Namespace: $NAMESPACE"
    echo

    # Initial health check
    check_cluster_health
    echo

    # Run all tests
    test_crash_loop
    echo
    sleep 10

    test_resource_starvation
    echo
    sleep 10

    test_network_partition
    echo
    sleep 10

    test_recovery
    echo
    sleep 10

    test_clock_skew
    echo

    log_info "========== ALL TESTS COMPLETE =========="
    log_info "Final cluster state:"
    check_cluster_health
}

# Run tests
main 2>&1 | tee /tmp/byzantine-test-results.log

log_info "Test results saved to /tmp/byzantine-test-results.log"
