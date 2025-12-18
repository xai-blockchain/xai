#!/bin/bash
# Test script for network policies
# Verifies egress restrictions and ingress allowances

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

echo "==================================="
echo "Network Policy Testing"
echo "==================================="
echo

# Test 1: DNS resolution (should work)
echo "[Test 1] DNS resolution to kube-system (should PASS)"
kubectl exec -n xai netpol-test -- nslookup kubernetes.default.svc.cluster.local > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ PASS: DNS resolution works"
else
    echo "✗ FAIL: DNS resolution blocked"
fi
echo

# Test 2: External network access (should be blocked)
echo "[Test 2] External network access (should FAIL/BLOCKED)"
timeout 5 kubectl exec -n xai netpol-test -- curl -s -m 3 http://www.google.com > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "✓ PASS: External network access blocked as expected"
else
    echo "✗ FAIL: External network access allowed (security issue!)"
fi
echo

# Test 3: Access to monitoring namespace (should work)
echo "[Test 3] Access to monitoring namespace (should PASS)"
PROM_IP=$(kubectl get pod -n monitoring -l app.kubernetes.io/name=prometheus -o jsonpath='{.items[0].status.podIP}')
if [ -n "$PROM_IP" ]; then
    timeout 5 kubectl exec -n xai netpol-test -- curl -s -m 3 http://$PROM_IP:9090/-/healthy > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ PASS: Monitoring namespace accessible"
    else
        echo "✗ FAIL: Monitoring namespace blocked"
    fi
else
    echo "⚠ SKIP: No Prometheus pod found in monitoring namespace"
fi
echo

# Test 4: Unauthorized port access (should be blocked)
echo "[Test 4] Access to unauthorized external port (should FAIL/BLOCKED)"
timeout 5 kubectl exec -n xai netpol-test -- curl -s -m 3 http://8.8.8.8:80 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "✓ PASS: Unauthorized egress blocked as expected"
else
    echo "✗ FAIL: Unauthorized egress allowed (security issue!)"
fi
echo

# Test 5: Verify policy count
echo "[Test 5] Network policy count verification"
POLICY_COUNT=$(kubectl get networkpolicies -n xai --no-headers | wc -l)
echo "Total network policies in xai namespace: $POLICY_COUNT"
if [ $POLICY_COUNT -ge 3 ]; then
    echo "✓ PASS: Expected policies present"
else
    echo "✗ FAIL: Missing policies"
fi
echo

echo "==================================="
echo "Test Summary Complete"
echo "==================================="
