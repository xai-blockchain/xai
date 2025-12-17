# Runbook: Block Production Below Target

## Triggers
- Alert: `BlockProductionSlow` (block_production_rate_per_minute < 0.2 for 10m)

## Immediate Checks
1. Node health: `curl http://localhost:12001/health`
2. Mining status: `curl http://localhost:12001/mining/status`
3. Difficulty trend: Grafana Mempool/Blockchain dashboards (`xai_block_difficulty`, `xai_block_production_rate_per_minute`).

## Mitigation Steps
1. Restart/enable mining on validators:
   - `curl -X POST -H "X-API-Key: $API_KEY" http://localhost:12001/auto-mine/start`
2. Verify pending transactions exist:
   - `curl http://localhost:12001/transactions?limit=5`
3. Check for consensus errors in logs (`logs/`).

## Validation
- Block height increasing steadily.
- `xai_block_production_rate_per_minute` rising above threshold.
- Alerts clear in Prometheus/Grafana.

## Escalation
- If multiple validators stall, escalate to consensus/on-call; collect metrics + logs from all nodes.
