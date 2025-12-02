# Local Kubernetes Cluster (Kind) - Agent Instructions

This document provides instructions for agents working on XAI blockchain deployment and monitoring tasks that require Kubernetes access.

## Current Cluster Status

**Cluster Name:** `xai-monitoring-dev`
**Context:** `kind-xai-monitoring-dev`
**Namespace:** `xai-blockchain`
**Created:** 2025-11-30

## Prerequisites

The following tools must be installed (already present on this system):

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 29.1.0+ | Container runtime for Kind nodes |
| kubectl | v1.33+ | Kubernetes CLI |
| kind | v0.24.0+ | Kubernetes in Docker |

## Quick Reference Commands

### Check Cluster Status

```bash
# Verify cluster is running
kind get clusters
# Expected output: xai-monitoring-dev

# Check nodes
kubectl get nodes --context kind-xai-monitoring-dev

# Check namespace exists
kubectl get ns xai-blockchain --context kind-xai-monitoring-dev
```

### If Cluster Is Not Running

If the cluster does not exist or was deleted, recreate it:

```bash
cd /home/decri/blockchain-projects/xai

# Create cluster
kind create cluster --config k8s/kind/dev-cluster.yaml

# Set context
kubectl config use-context kind-xai-monitoring-dev

# Create namespace
kubectl create namespace xai-blockchain
```

### Cluster Architecture

```
Kind Cluster: xai-monitoring-dev
├── Control Plane Node (xai-monitoring-dev-control-plane)
│   └── Kubernetes API, etcd, scheduler, controller-manager
└── Worker Node (xai-monitoring-dev-worker)
    └── Runs workload pods

Port Mappings (host → container):
├── 30090 → Prometheus
├── 30093 → Alertmanager
├── 30443 → Grafana
└── 30000 → RPC/API testing
```

## Running Monitoring Overlay Tests

The primary use case for this cluster is testing the monitoring overlays:

```bash
cd /home/decri/blockchain-projects/xai

# Apply monitoring overlays
./k8s/apply-monitoring-overlays.sh xai-blockchain

# Verify overlays
./k8s/verify-monitoring-overlays.sh --namespace=xai-blockchain

# Full smoke test (includes mock SIEM webhook)
CLUSTER_NAME=xai-monitoring-dev NAMESPACE=xai-blockchain scripts/ci/kind_monitoring_smoke.sh
```

## Deploying XAI Node to Local Cluster

To test full deployment locally:

```bash
cd /home/decri/blockchain-projects/xai/k8s

# Build Docker image and load into Kind
docker build -t xai-blockchain:local -f Dockerfile ..
kind load docker-image xai-blockchain:local --name xai-monitoring-dev

# Apply manifests (update image in statefulset.yaml first)
kubectl apply -f namespace.yaml --context kind-xai-monitoring-dev
kubectl apply -f configmap.yaml --context kind-xai-monitoring-dev
kubectl apply -f secret.yaml --context kind-xai-monitoring-dev  # Use test secrets only!
kubectl apply -f statefulset.yaml --context kind-xai-monitoring-dev
kubectl apply -f service.yaml --context kind-xai-monitoring-dev

# Watch pods
kubectl get pods -n xai-blockchain -w --context kind-xai-monitoring-dev
```

## Accessing Services

### Port Forwarding

```bash
# Prometheus (if deployed)
kubectl port-forward -n xai-blockchain svc/prometheus 9090:9090

# Grafana (if deployed)
kubectl port-forward -n xai-blockchain svc/grafana 3000:3000

# XAI Node RPC
kubectl port-forward -n xai-blockchain svc/xai-blockchain-rpc 8546:8546
```

### NodePort Access

Services exposed via NodePort are accessible at:
- Prometheus: http://localhost:30090
- Alertmanager: http://localhost:30093
- Grafana: http://localhost:30443

## Cleanup

### Delete Specific Resources

```bash
# Delete all resources in namespace
kubectl delete all --all -n xai-blockchain --context kind-xai-monitoring-dev

# Delete namespace
kubectl delete namespace xai-blockchain --context kind-xai-monitoring-dev
```

### Delete Entire Cluster

```bash
kind delete cluster --name xai-monitoring-dev
```

### Recreate Fresh Cluster

```bash
kind delete cluster --name xai-monitoring-dev
kind create cluster --config k8s/kind/dev-cluster.yaml
kubectl create namespace xai-blockchain
```

## Troubleshooting

### Cluster Not Found

```bash
# Check if cluster exists
kind get clusters

# If not listed, create it
kind create cluster --config k8s/kind/dev-cluster.yaml
```

### kubectl Context Issues

```bash
# List available contexts
kubectl config get-contexts

# Switch to Kind context
kubectl config use-context kind-xai-monitoring-dev

# Verify current context
kubectl config current-context
```

### Docker Issues

```bash
# Ensure Docker is running
docker ps

# If Kind nodes are stopped, restart Docker or recreate cluster
docker restart xai-monitoring-dev-control-plane xai-monitoring-dev-worker
```

### Resource Constraints

Kind clusters run entirely in Docker. If you experience issues:

```bash
# Check Docker resource usage
docker stats

# Reduce replicas in statefulset if needed
kubectl scale statefulset xai-blockchain-node --replicas=1 -n xai-blockchain
```

## Agent Notes

1. **Always verify cluster status** before attempting k8s operations
2. **Use `--context kind-xai-monitoring-dev`** to ensure you're targeting the local cluster
3. **Never use production secrets** in the local cluster - use test values only
4. **The cluster persists** across terminal sessions but is deleted if Docker restarts
5. **Check ROADMAP_PRODUCTION.md** for the blocked staging/prod task once local testing passes

## Related Documentation

- `k8s/kind/README.md` - Kind cluster configuration details
- `k8s/00-START-HERE.md` - Full k8s deployment guide
- `k8s/README.md` - Comprehensive deployment documentation
- `ROADMAP_PRODUCTION.md` - Production roadmap with blocked tasks
