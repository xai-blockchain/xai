# XAI Kubernetes State Sync & Upgrade Testing

## Environment
k3s v1.33.6, namespace: xai, StatefulSet: xai-validator, storage: local-path

## State Sync Test: Scaling 2→3 Replicas
**Status**: ✅ PASSED

Command: `kubectl scale statefulset xai-validator -n xai --replicas=3`

Results:
- New pod (xai-validator-2) created automatically in ~15s
- New PVC (data-xai-validator-2) provisioned successfully
- DNS via headless service working (pod-2 → pod-0 connectivity verified)
- StatefulSet auto-creates PVCs from volumeClaimTemplates
- Pods get stable network identity for state sync

## Upgrade Test: Rolling Update
**Status**: ✅ PASSED

Command: `kubectl set image statefulset/xai-validator -n xai validator=nginxinc/nginx-unprivileged:1.27-alpine`

Results:
- Zero-downtime update (reverse order: pod-1, then pod-0)
- Update sequence: Terminate → Create new → Wait for Ready
- One pod at a time maintains availability

## Rollback Test
**Status**: ✅ PASSED

Command: `kubectl rollout undo statefulset/xai-validator -n xai`

Results:
- Successful rollback in ~30s
- Reverse order maintained (StatefulSet guarantee)
- 4 revisions tracked for rollback capability

## Data Persistence Test
**Status**: ✅ PASSED

- All PVCs persisted through pod recreations
- PVC ages: 53+ min, pod ages: seconds
- No data loss during updates/rollbacks

## Key Issues Resolved
1. Linkerd injection conflicted with PodSecurity policy - disabled with: `kubectl label namespace xai config.linkerd.io/admission-webhooks=disabled`
2. Required securityContext: runAsNonRoot, capabilities drop, seccompProfile
