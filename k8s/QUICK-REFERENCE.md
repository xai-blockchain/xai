# XAI Blockchain Kubernetes Deployment - Quick Reference

## Quick Start

```bash
# 1. Make scripts executable
chmod +x k8s/deploy.sh k8s/verify-deployment.sh

# 2. Deploy the cluster
cd k8s
./deploy.sh --namespace xai-blockchain --image your-registry/xai-blockchain:latest

# 3. Verify deployment
./verify-deployment.sh

# 4. Get status
kubectl get all -n xai-blockchain
```

## Common kubectl Commands

### View Resources
```bash
# Get all resources
kubectl get all -n xai-blockchain

# Get pods with details
kubectl get pods -n xai-blockchain -o wide

# Get services
kubectl get svc -n xai-blockchain

# Get persistent volumes
kubectl get pv,pvc -n xai-blockchain

# Get ingress
kubectl get ingress -n xai-blockchain

# Get network policies
kubectl get networkpolicy -n xai-blockchain
```

### Pod Management
```bash
# View logs
kubectl logs -n xai-blockchain xai-blockchain-node-0

# Follow logs
kubectl logs -f -n xai-blockchain xai-blockchain-node-0

# View last 50 lines
kubectl logs -n xai-blockchain xai-blockchain-node-0 --tail=50

# View logs from previous pod (if restarted)
kubectl logs -n xai-blockchain xai-blockchain-node-0 --previous

# Describe pod
kubectl describe pod -n xai-blockchain xai-blockchain-node-0

# Execute command in pod
kubectl exec -it -n xai-blockchain xai-blockchain-node-0 -- bash

# Port-forward to pod
kubectl port-forward -n xai-blockchain xai-blockchain-node-0 8546:8546
```

### Scaling
```bash
# Scale to specific number of replicas
kubectl scale statefulset xai-blockchain-node -n xai-blockchain --replicas=5

# Watch rollout status
kubectl rollout status statefulset/xai-blockchain-node -n xai-blockchain

# Check HPA status
kubectl get hpa -n xai-blockchain

# Describe HPA for detailed metrics
kubectl describe hpa xai-blockchain-hpa -n xai-blockchain
```

### Updates and Rollouts
```bash
# Update image
kubectl set image statefulset/xai-blockchain-node \
  xai-blockchain=your-registry/xai-blockchain:v1.1.0 \
  -n xai-blockchain

# Check rollout history
kubectl rollout history statefulset/xai-blockchain-node -n xai-blockchain

# Rollback to previous version
kubectl rollout undo statefulset/xai-blockchain-node -n xai-blockchain

# Restart pods
kubectl rollout restart statefulset/xai-blockchain-node -n xai-blockchain
```

### Configuration Management
```bash
# View ConfigMap
kubectl get configmap xai-blockchain-config -n xai-blockchain -o yaml

# Edit ConfigMap
kubectl edit configmap xai-blockchain-config -n xai-blockchain

# View Secret (encoded)
kubectl get secret xai-blockchain-secrets -n xai-blockchain -o yaml

# Update ConfigMap
kubectl set env configmap/xai-blockchain-config \
  BLOCKCHAIN_DIFFICULTY=5 \
  -n xai-blockchain
```

### Networking
```bash
# Get service endpoints
kubectl get endpoints -n xai-blockchain

# Test DNS resolution
kubectl run -it --rm debug --image=busybox -- nslookup xai-blockchain-headless.xai-blockchain

# Port-forward to service
kubectl port-forward -n xai-blockchain svc/xai-blockchain-rpc 8546:8546

# Get ingress details
kubectl describe ingress xai-blockchain-ingress -n xai-blockchain
```

### Monitoring and Metrics
```bash
# View resource usage
kubectl top nodes
kubectl top pods -n xai-blockchain

# Get HPA metrics
kubectl get hpa xai-blockchain-hpa -n xai-blockchain -o yaml | grep -A 20 "status"

# Port-forward to Prometheus
kubectl port-forward -n xai-blockchain svc/xai-blockchain-metrics 9090:9090

# Port-forward to Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

### Debugging
```bash
# Get node info
kubectl get nodes -o wide

# Describe node
kubectl describe node <node-name>

# Check resource quotas
kubectl get resourcequota -n xai-blockchain

# Check limit ranges
kubectl get limitrange -n xai-blockchain

# View events
kubectl get events -n xai-blockchain

# Check pod events
kubectl describe pod -n xai-blockchain xai-blockchain-node-0 | grep Events -A 20
```

### RBAC and Security
```bash
# Check RBAC permissions
kubectl auth can-i get pods --as=system:serviceaccount:xai-blockchain:xai-blockchain-sa

# List service accounts
kubectl get sa -n xai-blockchain

# Describe service account
kubectl describe sa xai-blockchain-sa -n xai-blockchain

# Check network policies
kubectl get networkpolicy -n xai-blockchain -o yaml
```

## Useful Shortcuts

```bash
# Set default namespace
kubectl config set-context --current --namespace=xai-blockchain

# Use alias for shorter commands
alias k=kubectl
alias kn='kubectl config set-context --current --namespace'
alias kg='kubectl get'
alias kd='kubectl describe'
alias kl='kubectl logs'
alias ke='kubectl exec'

# Example usage with aliases
k get pods -n xai-blockchain
kg pods -n xai-blockchain
kl xai-blockchain-node-0 -n xai-blockchain
```

## Health Checks

### Check Cluster Health
```bash
# All core components running
kubectl get cs

# All nodes ready
kubectl get nodes

# All pods in cluster
kubectl get pods --all-namespaces

# Check API server
kubectl cluster-info
```

### Check Blockchain Node Health
```bash
# Get node status
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- curl http://localhost:12001/health

# Check logs for errors
kubectl logs xai-blockchain-node-0 -n xai-blockchain | grep -i error

# Check connected peers
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- curl http://localhost:12001/peers

# Check block height
kubectl exec -it xai-blockchain-node-0 -n xai-blockchain -- curl http://localhost:12001/block_height
```

### Monitor Resources
```bash
# Watch pod resource usage
kubectl top pods -n xai-blockchain --containers

# Monitor storage usage
kubectl exec xai-blockchain-node-0 -n xai-blockchain -- df -h /data

# Check PVC usage
kubectl exec xai-blockchain-node-0 -n xai-blockchain -- du -sh /data/blockchain

# Watch HPA scaling
kubectl get hpa -n xai-blockchain -w
```

## Common Troubleshooting

### Pod Won't Start
```bash
# Check pod status
kubectl describe pod xai-blockchain-node-0 -n xai-blockchain

# Check for image pull errors
kubectl describe pod xai-blockchain-node-0 -n xai-blockchain | grep -i "image"

# Check resource availability
kubectl describe nodes | grep -A 5 "Allocated resources"

# Check for PVC issues
kubectl describe pvc blockchain-data-0 -n xai-blockchain
```

### Network Issues
```bash
# Test DNS
kubectl run --rm -it busybox -- nslookup xai-blockchain-rpc

# Test service connectivity
kubectl run --rm -it busybox -- wget -O- http://xai-blockchain-rpc:8546

# Check network policies
kubectl describe networkpolicy -n xai-blockchain

# Check service endpoints
kubectl get endpoints -n xai-blockchain
```

### Storage Issues
```bash
# Check PV/PVC status
kubectl get pv,pvc -n xai-blockchain

# View PVC details
kubectl describe pvc blockchain-data-0 -n xai-blockchain

# Check available storage on nodes
df -h /data

# Check inside pod
kubectl exec xai-blockchain-node-0 -n xai-blockchain -- df -h /data
```

### Performance Issues
```bash
# Check CPU/memory usage
kubectl top pods -n xai-blockchain

# Check node capacity
kubectl top nodes

# Check HPA decisions
kubectl describe hpa xai-blockchain-hpa -n xai-blockchain

# Check for stuck pods
kubectl get pods -n xai-blockchain --field-selector=status.phase!=Running
```

## Important Notes

1. **Always backup data before major updates**
   ```bash
   kubectl exec xai-blockchain-node-0 -n xai-blockchain -- tar czf - /data/blockchain | gzip > backup.tar.gz
   ```

2. **Never delete StatefulSet without PVC cleanup understanding**
   - Set `persistentVolumeReclaimPolicy: Retain` to keep data

3. **Monitor resources regularly**
   ```bash
   kubectl top pods -n xai-blockchain --watch
   ```

4. **Keep logs for debugging**
   ```bash
   kubectl logs xai-blockchain-node-0 -n xai-blockchain > node-0.log
   ```

5. **Test changes in staging first**
   - Create a staging namespace
   - Apply changes there first
   - Verify before production deployment

## Getting Help

```bash
# Get kubectl command help
kubectl --help
kubectl get --help
kubectl logs --help

# Get API resource definitions
kubectl api-resources

# Get detailed API documentation
kubectl explain pods
kubectl explain statefulset.spec
```

## Performance Tips

1. **Increase HPA max replicas for high load**
   ```bash
   kubectl patch hpa xai-blockchain-hpa -p '{"spec":{"maxReplicas":15}}' -n xai-blockchain
   ```

2. **Adjust resource requests based on actual usage**
   ```bash
   # Check actual usage
   kubectl top pods -n xai-blockchain

   # Update resource requests
   kubectl set resources statefulset xai-blockchain-node \
     -c=xai-blockchain \
     --requests=cpu=2000m,memory=4Gi \
     -n xai-blockchain
   ```

3. **Use node affinity for better scheduling**
   - See `statefulset.yaml` for examples

4. **Enable metrics-server for HPA to function**
   ```bash
   ```

## Maintenance Windows

```bash
# Drain node for maintenance
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Cordon node (prevent new pods)
kubectl cordon <node-name>

# Uncordon node (allow new pods)
kubectl uncordon <node-name>
```
