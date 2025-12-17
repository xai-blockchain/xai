# Runbook: Mempool Size High / Not Draining

## Triggers
- Alert: `MempoolGrowingUnbounded` (mempool > 2000 tx for 5m)
- Alert: `MempoolStalledThroughput` (confirmed tx rate <1/s and mempool >500 for 10m)

## Immediate Checks
1. Confirm node health:
   - `curl http://localhost:12001/health`
   - `curl http://localhost:12001/stats`
2. Inspect mempool size:
   - `curl http://localhost:12001/transactions?limit=1 | jq '.count'`
3. Check block production:
   - `curl "http://localhost:12001/block/latest?summary=1" | jq '.block_number'`

## Mitigation Steps
1. Ensure miners are active:
   - `curl -X POST -H "X-API-Key: $API_KEY" http://localhost:12001/auto-mine/start`
2. Raise fee threshold (optional):
   - Adjust fee policy in config/env (`TX_MIN_FEE`) and restart if necessary.
3. Purge malformed tx (last resort):
   - Restart node with `XAI_PURGE_PENDING=1` to clear stale mempool entries.

## Validation
- Mempool size trending down on Grafana Mempool dashboard.
- `rate(xai_transactions_total{status="confirmed"}[5m])` rising above alert threshold.
- Block production rate approaching target.

## Escalation
- If block production is stalled across all validators, engage consensus/on-call and capture logs from `logs/`.
