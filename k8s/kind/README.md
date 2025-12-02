# Local Development Cluster (Kind)

This directory contains the configuration used to spin up a lightweight Kubernetes cluster inside Docker for monitoring/overlay tests.

> **Note:** For comprehensive agent instructions, see `../LOCAL_CLUSTER.md`

## Prerequisites
- Docker Engine running locally (tested with 29.1.0)
- `kubectl` on your `$PATH`
- `kind` v0.24.0+ installed (`sudo install -m 0755 kind /usr/local/bin/kind`)

## Create the Cluster
```bash
cd ${REPO_ROOT:-/home/decri/blockchain-projects/xai}
kind create cluster --config k8s/kind/dev-cluster.yaml
kubectl config use-context kind-xai-monitoring-dev
kubectl get nodes -o wide
kubectl create namespace xai-blockchain
```

The Kind config provisions one control-plane and one worker node and pre-maps a few host ports so NodePorts/port-forwards can expose:
- 30090 → Prometheus
- 30093 → Alertmanager
- 30443 → Grafana
- 30000 → spare for RPC/API testing

## Apply Monitoring Overlays Locally
```bash
./k8s/apply-monitoring-overlays.sh xai-blockchain
./k8s/verify-monitoring-overlays.sh --namespace=xai-blockchain
```

Add your monitoring stack manifests/Helm charts and restart the relevant Deployments/StatefulSets so they pick up the configmaps created above.

## One-Command Smoke Test

Use the CI helper to spin up the Kind cluster, apply overlays, publish a mock SIEM webhook, and run the verifier with a probe:

```bash
CLUSTER_NAME=xai-monitoring-dev NAMESPACE=xai-blockchain scripts/ci/kind_monitoring_smoke.sh
```

Overrides:
- `CLUSTER_NAME` – Kind cluster name (default `xai-monitoring-dev`)
- `NAMESPACE` – monitoring namespace for overlay ConfigMaps (default `xai-blockchain`)
- `APP_NAMESPACE` – namespace hosting `xai-blockchain-config` and mock SIEM (defaults to `NAMESPACE`)
- `KEEP_CLUSTER=1` – skip teardown after the smoke test completes

## Tear Down
```bash
kind delete cluster --name xai-monitoring-dev
```
