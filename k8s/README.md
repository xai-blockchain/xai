# XAI Blockchain Kubernetes Deployment Guide

## Overview

This directory contains complete Kubernetes manifests for deploying the XAI blockchain in a production-ready configuration. The deployment includes:

- **3 StatefulSet Replicas** for high availability
- **Persistent Storage** (100Gi per node) for blockchain data
- **Load Balanced Services** for P2P, RPC, and WebSocket endpoints
- **TLS/SSL Termination** via Ingress with Let's Encrypt
- **Horizontal Pod Autoscaling** based on metrics
- **Comprehensive Monitoring** with Prometheus and Grafana
- **Network Policies** for security
- **RBAC Configuration** for access control

## File Structure

```
k8s/
├── README.md                 # This file
├── namespace.yaml            # Kubernetes namespace definition
├── configmap.yaml            # Application configuration
├── secret.yaml               # Secrets template (API keys, etc.)
├── pv.yaml                   # PersistentVolume and StorageClass definitions
├── statefulset.yaml          # StatefulSet for blockchain nodes
├── service.yaml              # Services for P2P, RPC, WebSocket
├── ingress.yaml              # Ingress with TLS and NetworkPolicy
├── hpa.yaml                  # Horizontal Pod Autoscaler
├── monitoring.yaml           # Prometheus monitoring setup
├── rbac.yaml                 # RBAC and security policies
└── docker/                   # Docker build artifacts (if needed)
    └── Dockerfile            # Container image definition
```

## Prerequisites

### Cluster Requirements

- **Kubernetes Version**: 1.20+ (1.24+ recommended)
- **Nodes**: 3+ with at least:
  - 4 CPUs per node
  - 8Gi memory per node
  - 200Gi storage per node
- **Network**: Stable network connectivity between nodes
- **DNS**: Working cluster DNS (CoreDNS)

### Required Tools

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (optional but recommended)

# Install kubectx (optional but useful)
sudo ln -s /opt/kubectx/kubectx /usr/local/bin/kubectx
```

### Cluster Addons Required

```bash
# Verify ingress-nginx is installed
kubectl get ns ingress-nginx

# Install if missing
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace

# Install cert-manager for TLS
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --version v1.13.0

# Install Prometheus Operator (for monitoring)
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

## Deployment Steps

### 1. Prepare Secrets

Before deploying, update the secrets with real values:

```bash
# Generate private keys for blockchain nodes
# Each node needs a unique private key for signing transactions

# Generate ECDSA private key
openssl ecparam -name secp256k1 -genkey -noout -out private-key.pem
openssl pkeyutl -sigfile <file-to-sign> -inkey private-key.pem

# Create TLS certificate (or use Let's Encrypt via cert-manager)
openssl req -x509 -newkey rsa:4096 -keyout tls.key -out tls.crt -days 365 -nodes

# Encode to base64 for secrets
cat private-key.pem | base64
cat tls.key | base64
cat tls.crt | base64

# Update secret.yaml with the encoded values
nano k8s/secret.yaml
```

### 2. Update Configuration

Review and update `configmap.yaml` with your network settings:

```bash
# Key configuration values to verify:
# - NODE_PORT: P2P port (default 8545)
# - RPC_PORT: JSON-RPC port (default 8546)
# - WS_PORT: WebSocket port (default 8547)
# - BLOCKCHAIN_DIFFICULTY: Mining difficulty
# - MAX_PEERS: Maximum peer connections
```

### 3. Prepare Persistent Volumes

For cloud deployments, update `pv.yaml` to use your cloud storage provider:

```yaml
# For AWS EBS
storageClassName: gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: 3000
  throughput: 125

# For GCP Persistent Disk
storageClassName: standard-rwo
provisioner: pd.csi.storage.gke.io

# For Azure Disk
storageClassName: managed-premium
provisioner: disk.csi.azure.com
```

### 4. Update Ingress Settings

Edit `ingress.yaml` to configure your domain:

```yaml
# Update these hostnames to your domains
- host: rpc.xai.network
- host: ws.xai.network
- host: api.xai.network

# Update email for Let's Encrypt certificate generation
email: admin+xai-blockchain@xai.network

# Configure DNS validation (if using Route53)
hostedZoneID: Z1234567890ABC  # Your Route53 zone ID
region: us-east-1
```

### 5. Build and Push Docker Image

```bash
# Build the Docker image
docker build -f docker/Dockerfile -t xai-blockchain:latest .

# Tag for your registry
docker tag xai-blockchain:latest your-registry.azurecr.io/xai-blockchain:latest

# Push to registry
docker push your-registry.azurecr.io/xai-blockchain:latest

# Update statefulset.yaml with your image
sed -i 's|xai-blockchain:latest|your-registry.azurecr.io/xai-blockchain:latest|g' k8s/statefulset.yaml
```

### 6. Deploy to Kubernetes

```bash
# Create the namespace
kubectl apply -f k8s/namespace.yaml

# Verify namespace
kubectl get ns xai-blockchain

# Apply RBAC and security policies
kubectl apply -f k8s/rbac.yaml

# Create PersistentVolumes
kubectl apply -f k8s/pv.yaml

# Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# Create Secrets
kubectl apply -f k8s/secret.yaml

# Deploy StatefulSet
kubectl apply -f k8s/statefulset.yaml

# Create Services
kubectl apply -f k8s/service.yaml

# Deploy Ingress
kubectl apply -f k8s/ingress.yaml

# Configure monitoring
kubectl apply -f k8s/monitoring.yaml

# Deploy HPA
kubectl apply -f k8s/hpa.yaml
```

### 7. Verify Deployment

```bash
# Check namespace
kubectl get all -n xai-blockchain

# Check pods
kubectl get pods -n xai-blockchain

# Check StatefulSet
kubectl get statefulset -n xai-blockchain

# Check PVCs
kubectl get pvc -n xai-blockchain

# Check services
kubectl get svc -n xai-blockchain

# Check ingress
kubectl get ingress -n xai-blockchain

# View pod logs
kubectl logs -n xai-blockchain xai-blockchain-node-0

# Describe a pod (for troubleshooting)
kubectl describe pod -n xai-blockchain xai-blockchain-node-0
```

## Configuration

### Network Settings

The deployment exposes multiple endpoints:

| Port | Service | Purpose | Access |
|------|---------|---------|--------|
| 8545 | P2P Network | Peer-to-peer communication | Internal/LoadBalancer |
| 8546 | JSON-RPC | Blockchain interaction | Internal/LoadBalancer |
| 8547 | WebSocket | Real-time events | Internal/LoadBalancer |
| 9090 | Metrics | Prometheus metrics | Internal/Ingress |

### Resource Requests and Limits

```yaml
requests:
  cpu: 1000m (1 core)
  memory: 2Gi

limits:
  cpu: 2000m (2 cores)
  memory: 4Gi
```

Adjust based on your node capabilities and traffic expectations.

### Storage Configuration

- **Data Directory**: `/data/blockchain`
- **Storage Size**: 100Gi per node (configurable)
- **Storage Class**: `xai-blockchain-storage`
- **Retention Policy**: `Retain` (data persists after pod deletion)

## Monitoring and Alerting

### Access Prometheus

```bash
# Port-forward to Prometheus
kubectl port-forward -n xai-blockchain svc/xai-blockchain-metrics 9090:9090

# Access at http://localhost:9090
```

### Access Grafana

```bash
# Get Grafana service
kubectl get svc -n monitoring

# Port-forward to Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Access at http://localhost:3000
# Default credentials: admin/prom-operator
```

### Available Metrics

The deployment includes metrics for:

- Node health and availability
- Memory and CPU usage
- Disk usage and I/O
- Network connectivity (peer count)
- Block production rate
- Transaction processing rate
- Block sync lag
- Mining difficulty
- Consensus status

### Alerting Rules

Critical alerts include:

- Node down (3 minutes)
- Low peer count (< 2 peers)
- No blocks produced (10 minutes)
- High memory/CPU usage (>90%)
- High disk usage (>85%)
- Network partition detection
- Consensus failures

## Security

### Pod Security

- Runs as non-root user (UID 1000)
- Read-only filesystem where possible
- No privilege escalation
- Minimal Linux capabilities

### Network Security

- NetworkPolicies restrict traffic
- TLS/SSL termination at Ingress
- API authentication via JWT/Basic Auth
- Rate limiting (100 RPS default)

### Secrets Management

Secrets should be managed via:

1. **HashiCorp Vault** (recommended)
2. **AWS Secrets Manager**
3. **Azure Key Vault**
4. **Sealed Secrets** (for GitOps)

Update `secret.yaml` to use ExternalSecrets Operator:

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

## Scaling

### Horizontal Scaling

The HPA automatically scales nodes based on:

- CPU utilization (70% threshold)
- Memory utilization (75% threshold)
- Connected peer count (< 45 peers)
- Block sync lag (> 10 blocks)
- Transaction pool size (> 500 txs)

Min replicas: 3
Max replicas: 10

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale statefulset xai-blockchain-node -n xai-blockchain --replicas=5

# Watch scaling progress
kubectl rollout status statefulset/xai-blockchain-node -n xai-blockchain
```

## Upgrades

### Rolling Updates

The deployment uses rolling update strategy with no partition:

```bash
# Update StatefulSet image
kubectl set image statefulset/xai-blockchain-node \
  xai-blockchain=your-registry.azurecr.io/xai-blockchain:v1.1.0 \
  -n xai-blockchain

# Monitor rollout
kubectl rollout status statefulset/xai-blockchain-node -n xai-blockchain

# Check history
kubectl rollout history statefulset/xai-blockchain-node -n xai-blockchain

# Rollback if needed
kubectl rollout undo statefulset/xai-blockchain-node -n xai-blockchain
```

### ConfigMap Updates

```bash
# Update configuration
kubectl set env configmap/xai-blockchain-config \
  BLOCKCHAIN_DIFFICULTY=5 \
  -n xai-blockchain

# Restart pods to pick up changes
kubectl rollout restart statefulset/xai-blockchain-node -n xai-blockchain
```

## Troubleshooting

### Pod Won't Start

```bash
# Check pod events
kubectl describe pod xai-blockchain-node-0 -n xai-blockchain

# Check pod logs
kubectl logs xai-blockchain-node-0 -n xai-blockchain

# Check resource availability
kubectl top nodes
kubectl top pod -n xai-blockchain

# Check PVC binding
kubectl get pvc -n xai-blockchain
```

### Network Connectivity Issues

```bash
# Test DNS resolution
kubectl run -it --rm debug --image=busybox -- nslookup xai-blockchain-headless.xai-blockchain

# Test connectivity between pods
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- ping xai-blockchain-node-1.xai-blockchain-headless

# Check services and endpoints
kubectl get endpoints -n xai-blockchain
kubectl get svc -n xai-blockchain
```

### Storage Issues

```bash
# Check PV and PVC status
kubectl get pv
kubectl get pvc -n xai-blockchain

# Check disk usage
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- df -h /data

# Resize PVC (if storage class supports expansion)
kubectl patch pvc blockchain-data-0 -n xai-blockchain -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
```

### Monitoring Issues

```bash
# Check Prometheus scraping targets
kubectl port-forward -n xai-blockchain svc/xai-blockchain-metrics 9090:9090
# Visit http://localhost:9090/targets

# Check ServiceMonitor
kubectl get servicemonitor -n xai-blockchain

# Check PrometheusRule
kubectl get prometheusrule -n xai-blockchain
```

## Backup and Recovery

### Backup Blockchain Data

```bash
# Create backup from PVC
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- tar czf - /data/blockchain | \
  gzip > blockchain-backup-$(date +%Y%m%d).tar.gz

# Backup to cloud storage
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- \
  aws s3 cp /data/blockchain s3://xai-backups/ --recursive
```

### Recovery from Backup

```bash
# Restore from backup
kubectl cp blockchain-backup-20231119.tar.gz xai-blockchain/xai-blockchain-node-0:/tmp/
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- \
  tar xzf /tmp/blockchain-backup-20231119.tar.gz -C /

# Restart pod
kubectl delete pod xai-blockchain-node-0 -n xai-blockchain
```

## Production Checklist

- [ ] All secrets updated with real values
- [ ] Ingress domains configured
- [ ] TLS certificates obtained
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented
- [ ] Security policies reviewed
- [ ] Resource limits appropriate
- [ ] Network policies tested
- [ ] RBAC properly configured
- [ ] Load testing completed
- [ ] Disaster recovery plan documented
- [ ] On-call rotation established

## Support and Troubleshooting

For issues, check:

1. Pod logs: `kubectl logs -n xai-blockchain <pod-name>`
2. Events: `kubectl describe pod -n xai-blockchain <pod-name>`
3. Metrics: Access Prometheus dashboard
4. Network policies: `kubectl get networkpolicy -n xai-blockchain`
5. RBAC: `kubectl auth can-i <verb> <resource> --as=system:serviceaccount:xai-blockchain:xai-blockchain-sa`

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [StatefulSet Patterns](https://kubernetes.io/docs/tutorials/stateful-application/)
- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [RBAC Authorization](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Prometheus Operator](https://prometheus-operator.dev/)

## License

These manifests are part of the XAI Blockchain project.
