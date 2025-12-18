# XAI Node - Kubernetes Deployment

Deploy XAI blockchain node on any Kubernetes cluster.

## Quick Start

### Option 1: Direct YAML

```bash
kubectl apply -f https://raw.githubusercontent.com/xai-blockchain/xai/main/deploy/kubernetes/deployment.yaml
```

### Option 2: Helm Chart

```bash
helm repo add xai https://xai-blockchain.github.io/helm-charts
helm install xai-node xai/xai-blockchain
```

### Option 3: Local Helm

```bash
cd deploy/kubernetes/helm
helm install xai-node . --namespace xai-blockchain --create-namespace
```

## Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- 100GB+ storage available
- LoadBalancer support (or use NodePort/Ingress)

## Resources Created

- Namespace: xai-blockchain
- Deployments: xai-node, redis, xai-explorer
- StatefulSet: postgres
- PVCs: xai-data (100GB), postgres-data (50GB)
- Services: LoadBalancer for node and explorer
- ConfigMaps and Secrets

## Access

```bash
# Get external IPs
kubectl get svc -n xai-blockchain

# API
curl http://<xai-node-external-ip>:8080/health

# Explorer
http://<xai-explorer-external-ip>
```

## Configuration

### Edit ConfigMap

```bash
kubectl edit configmap xai-config -n xai-blockchain
```

### Update Secrets

```bash
kubectl create secret generic xai-secrets \
  --from-literal=POSTGRES_PASSWORD='your-secure-password' \
  --dry-run=client -o yaml | kubectl apply -n xai-blockchain -f -
```

### Helm Values

```bash
helm install xai-node ./helm \
  --set network.mode=mainnet \
  --set node.storage.size=200Gi \
  --set postgresql.auth.password=securepass
```

## Monitoring

```bash
# View logs
kubectl logs -f deployment/xai-node -n xai-blockchain

# Check status
kubectl get pods -n xai-blockchain

# Resource usage
kubectl top pods -n xai-blockchain
```

## Scaling

```bash
# Scale node (not recommended for blockchain)
kubectl scale deployment xai-node --replicas=2 -n xai-blockchain

# Scale explorer
kubectl scale deployment xai-explorer --replicas=3 -n xai-blockchain
```

## Persistence

Data persists in PVCs. To backup:

```bash
# Backup blockchain data
kubectl exec -n xai-blockchain deployment/xai-node -- tar czf - /data | \
  gzip > xai-backup-$(date +%Y%m%d).tar.gz
```

## Cleanup

```bash
# Helm
helm uninstall xai-node -n xai-blockchain

# Direct YAML
kubectl delete namespace xai-blockchain

# Note: PVCs persist by default for safety
kubectl delete pvc -n xai-blockchain --all
```

## Cluster-Specific Notes

### GKE (Google Kubernetes Engine)

```bash
gcloud container clusters create xai-cluster \
  --num-nodes=3 \
  --machine-type=n1-standard-2 \
  --disk-size=100

helm install xai-node ./helm
```

### EKS (Amazon Elastic Kubernetes)

```bash
eksctl create cluster --name xai-cluster --nodes 3 --node-type t3.large

helm install xai-node ./helm
```

### AKS (Azure Kubernetes Service)

```bash
az aks create --resource-group xai-rg --name xai-cluster \
  --node-count 3 --node-vm-size Standard_D2s_v3

helm install xai-node ./helm
```

### DigitalOcean Kubernetes

```bash
doctl kubernetes cluster create xai-cluster \
  --count 3 --size s-2vcpu-4gb

helm install xai-node ./helm
```

## Production Considerations

- Use dedicated node pools for blockchain workloads
- Enable autoscaling for explorer/API components
- Configure Ingress with TLS for HTTPS
- Enable monitoring with Prometheus/Grafana
- Set up automated backups
- Use regional persistent disks for HA
