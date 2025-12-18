# Network Policies

Production-grade network policies for XAI blockchain Kubernetes cluster.

## Deployed Policies

### Egress Policies (per namespace: aura, paw, xai)
- **DNS**: Allow UDP/TCP port 53 to kube-system namespace
- **Monitoring**: Allow TCP 9090/9093 to monitoring namespace (Prometheus/Alertmanager)
- **Intra-namespace**: Allow all traffic within same project namespace
- **Default**: Deny all other egress (implicit)

### Ingress Policies (per namespace)
- **ingress-nginx**: Allow traffic from ingress-nginx namespace on blockchain ports
- **Monitoring**: Allow Prometheus scraping (TCP 9100/26660)
- **Intra-namespace**: Allow all traffic within same project namespace

## Files

- `egress-policy.yaml` - Egress restrictions for all project namespaces
- `ingress-nginx-policy.yaml` - Ingress allowances for external access
- `test-network-policies.sh` - Automated test suite
- `test-egress-block.yaml` - Test pod manifest (restricted PSS compliant)

## Testing

```bash
# Run automated test suite
./test-network-policies.sh

# Manual testing (requires test pod)
kubectl apply -f test-egress-block.yaml
kubectl exec -n xai netpol-test -- nslookup kubernetes.default  # Should work
kubectl exec -n xai netpol-test -- curl http://www.google.com   # Should fail
kubectl delete pod netpol-test -n xai
```

## Verification

All policies applied and tested successfully:
- ✅ DNS resolution works (kube-system access)
- ✅ External network blocked (unauthorized egress denied)
- ✅ Monitoring namespace accessible
- ✅ Unauthorized ports/IPs blocked
- ✅ ingress-nginx can reach project namespaces
