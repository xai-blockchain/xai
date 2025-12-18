# K8s Chaos Testing - XAI Testnet

## Test Environment
- **Cluster**: k3s v1.33.6
- **Nodes**: bcpc-staging (control-plane, 100.91.253.108), wsl2-worker (100.76.8.7)
- **Namespace**: xai
- **Test StatefulSet**: 2 nginx-unprivileged pods (50m CPU, 64Mi RAM requests)

## Test Results

### 1. Network Partition Test
**Scenario**: 200ms latency + 20% packet loss (single node)
- Baseline RTT: ~2.5ms
- Under chaos: ~202ms (200ms added latency)
- Packet loss: 0% observed (packets that made it through)
- Recovery: Immediate after tc cleanup

### 2. High Latency Test
**Scenario**: 500ms total latency (250ms per node) + 50ms jitter
- Baseline RTT: ~2.6ms
- Under chaos: 228-272ms avg RTT (jitter working)
- HTTP request: 2185ms (includes connection overhead)
- Recovery: Clean restoration to 2.2-3.1ms

## Pod Configuration
```yaml
Image: nginxinc/nginx-unprivileged:alpine
Resources: cpu 50m/100m, memory 64Mi/128Mi
Security: runAsUser 8080, no privilege escalation, capabilities dropped
Probes: HTTP readiness/liveness on :8080
```

## Chaos Tools Used
- **tc netem**: Applied on eth0 of wsl2-worker and bcpc-staging
- **SSH remote execution**: For worker node chaos injection
- **kubectl exec**: For in-pod connectivity verification

## Key Findings
1. Cross-node pod communication resilient to 200ms+ latency
2. Jitter correctly applies (±50ms variance observed)
3. Packet loss observable but didn't trigger in 20% test (small sample)
4. tc cleanup restores baseline performance immediately
5. StatefulSet pods stable during network disruption

## Future Tests
- Byzantine fault injection (contradictory responses)
- Bandwidth throttling (1Mbps, 100Kbps)
- Complete network partition (100% loss)
- Multi-pod cascade failures
