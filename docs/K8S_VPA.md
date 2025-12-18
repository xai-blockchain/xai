# Vertical Pod Autoscaler (VPA) on k3s

## Overview
VPA automatically analyzes resource usage and provides right-sizing recommendations for pods.

## Installation Status
- **VPA Version**: 1.5.1
- **Components**: Recommender, Updater, Admission Controller (all running)
- **Namespace**: kube-system
- **Metrics Source**: metrics-server

## Components
- **vpa-recommender**: Analyzes resource usage and generates recommendations
- **vpa-updater**: Evicts pods when updateMode is "Auto" or "Recreate"
- **vpa-admission-controller**: Applies VPA recommendations to new pods

## VPA for xai-validator
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: xai-validator-vpa
  namespace: xai
spec:
  targetRef:
    apiVersion: apps/v1
    kind: StatefulSet
    name: xai-validator
  updateMode: "Off"  # Recommendations only
```

## Viewing Recommendations
```bash
kubectl get vpa -n xai
kubectl describe vpa xai-validator-vpa -n xai
```

## Update Modes
- **Off**: Recommendations only, no changes
- **Initial**: Applied only at pod creation
- **Recreate**: VPA evicts pods to apply new recommendations
- **Auto**: VPA updates running pods in-place (requires feature gate)
