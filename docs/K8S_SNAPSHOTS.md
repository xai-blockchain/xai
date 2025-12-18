# Kubernetes Volume Snapshots for XAI

## Status: PARTIAL (Requires CSI Driver Upgrade)

### Limitations
- local-path provisioner does NOT support CSI snapshots
- Only K3s etcd snapshots available (cluster-level, not volume-level)

### Working Solution: Manual Backup
```bash
# Backup XAI namespace + PVCs
~/blockchain-projects/scripts/k8s-backup.sh backup xai

# Restore
~/blockchain-projects/scripts/k8s-backup.sh restore ~/blockchain-projects/k8s-backups/xai_20251218_231900 xai
```

Backs up: StatefulSets, ConfigMaps, Secrets, Services, PVC data (tar archives), pod logs

### Production: Upgrade Storage Driver

**Longhorn (Recommended):**
```bash
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.7.2/deploy/longhorn.yaml
```

**Then install snapshot CRDs:**
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshots.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotcontents.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes-csi/external-snapshotter/master/client/config/crd/snapshot.storage.k8s.io_volumesnapshotclasses.yaml
```

### Recommendation
Manual backup script for dev. Longhorn for production snapshots + replication.
