# Kubernetes Backup and Restore

## Overview
Automated backup/restore for XAI K8s cluster (k3s). Backs up all namespace resources, PVC data, and pod logs.

## Backup Script
Location: `~/blockchain-projects/scripts/k8s-backup.sh`

## Quick Start

### Create Backup
```bash
~/blockchain-projects/scripts/k8s-backup.sh backup xai
# Default location: ~/blockchain-projects/k8s-backups/xai_TIMESTAMP/
```

### Restore from Backup
```bash
~/blockchain-projects/scripts/k8s-backup.sh restore /path/to/backup xai
```

## Backup Contents
```
xai_TIMESTAMP/
├── manifests/          # YAML exports of all resources
│   ├── deployments.yaml
│   ├── statefulsets.yaml
│   ├── services.yaml
│   ├── configmaps.yaml
│   ├── secrets.yaml
│   └── persistentvolumeclaims.yaml
├── pvcs/              # PVC data archives
│   └── pvc-name/
│       └── data.tar.gz
├── logs/              # Pod logs at backup time
│   └── pod-name.log
├── metadata.txt       # Backup metadata
└── RESTORE.md         # Restore instructions
```

## Restore Process
1. Applies manifests (StatefulSets create new PVCs)
2. Waits for pods to be ready
3. Extracts backed-up data into running pods via kubectl exec

## Tested Scenarios
- StatefulSet with PVC data restore
- Data integrity verification
- Cross-node PVC backup (multi-node k3s cluster)
