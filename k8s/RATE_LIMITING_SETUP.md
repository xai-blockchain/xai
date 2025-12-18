# Rate Limiting for XAI Blockchain RPC Endpoints

## Overview
Implemented nginx-ingress rate limiting for XAI blockchain RPC endpoints to protect against DDoS attacks and ensure fair resource usage.

## Configuration

**Rate Limits**:
- Requests per second: 10 RPS
- Maximum concurrent connections: 5
- Burst multiplier: 1

**Files**:
- `/home/hudson/blockchain-projects/xai/k8s/rate-limit-test-deployment.yaml` - Complete deployment with rate limiting

## Resources Created

1. **ConfigMap**: `nginx-rate-limit-config` - Placeholder for rate limit configuration
2. **Deployment**: `rate-limit-test` - nginx:alpine test server with security context
3. **Service**: `rate-limit-test-service` - ClusterIP service on port 80
4. **Ingress**: `rate-limit-test-ingress` - nginx-ingress with rate limiting annotations

## Ingress Annotations

```yaml
nginx.ingress.kubernetes.io/limit-rps: "10"
nginx.ingress.kubernetes.io/limit-connections: "5"
nginx.ingress.kubernetes.io/limit-burst-multiplier: "1"
```

## Resource Limits

All pods include CPU/memory requests and limits to satisfy namespace quota:

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "200m"
    memory: "256Mi"
```

## Security Context

Pods comply with PSS "restricted" standard:
- runAsNonRoot: true
- allowPrivilegeEscalation: false
- capabilities: drop ALL
- seccompProfile: RuntimeDefault

## Network Policy

Port 8080 added to `allow-ingress-nginx` NetworkPolicy to allow ingress controller access.

## Testing

**Test Results**:
- Burst test (20 requests): 13 successful (200), 7 rate-limited (503)
- Rate limit reset: Works after 3s cooldown
- Connection limit: Enforced correctly

**Test Scripts**:
- `/tmp/test-rate-limit.sh` - Basic rate limiting test
- `/tmp/comprehensive-rate-limit-test.sh` - Full test suite

## Access

**URL**: http://localhost:30080/ (with Host header: rpc-test.xai.local)

**Example**:
```bash
curl -H "Host: rpc-test.xai.local" http://localhost:30080/
```

## Production Usage

For production RPC endpoints, apply these annotations to your Ingress resource:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: xai-rpc-ingress
  namespace: xai
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/limit-connections: "50"
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"
spec:
  ingressClassName: nginx
  rules:
  - host: rpc.xai.network
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: xai-rpc-service
            port:
              number: 8545
```

Adjust limits based on expected traffic and server capacity.
