# Kubernetes Upgrade Migration Testing

## Overview
Tested rolling upgrades of XAI blockchain nodes without network halt.

## Test Setup
- **Cluster**: k3s v1.33.6 (2 nodes: bcpc-staging, wsl2-worker)
- **Namespace**: xai (PSS restricted)
- **StatefulSet**: 2 replicas with anti-affinity

## Images
- v1: xai-node:v1 (version 0.1.0)
- v2: xai-node:v2 (version 0.2.0)

## Test Results

| Metric | Result |
|--------|--------|
| Pre-upgrade height | 93 blocks |
| Post-upgrade height | 101 blocks (node-0) |
| Downtime | 0 (rolling update) |
| Data preserved | Yes |
| Health after upgrade | Both nodes healthy |

## Rolling Upgrade Command
```bash
kubectl set image statefulset/xai-node xai-node=xai-node:v2 -n xai
kubectl rollout status statefulset/xai-node -n xai
```

## Key Findings
1. StatefulSet updates pods in reverse order (1 → 0)
2. PVC data persists across upgrades
3. Block production continues during upgrade
4. Health probes validate each pod before proceeding

## Rollback
```bash
kubectl rollout undo statefulset/xai-node -n xai
```

## Status
✅ PASS - Chain upgrades without network halt verified
