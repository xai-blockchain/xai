# XAI 24-Hour Soak Test

## Current Test
- **Started**: 2025-12-19 02:11:27 UTC
- **Ends**: 2025-12-20 ~02:11 UTC
- **Log**: `/home/hudson/blockchain-projects/xai/soak-test-results/soak-20251219-021127.log`

## Check Status
```bash
# View latest metrics
tail -30 ~/blockchain-projects/xai/soak-test-results/soak-20251219-021127.log

# Watch live
tail -f ~/blockchain-projects/xai/soak-test-results/soak-20251219-021127.log

# Check process running
ps aux | grep soak-test

# Quick health check
kubectl get pods -n xai -l app=xai-node -o wide
```

## What It Monitors (every 5 min)
- Block height progression
- Node health status
- Peer connections
- Pending transactions
- CPU/memory usage
- Pod restarts

## After 24h
Summary at: `~/blockchain-projects/xai/soak-test-results/summary.txt`

## Success Criteria
- ✅ Zero restarts
- ✅ Memory stable (no leaks)
- ✅ Block height increasing
- ✅ Nodes remain healthy
