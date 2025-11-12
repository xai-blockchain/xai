# Prometheus + Grafana Metrics

We expose `/metrics` alongside trade/mine counters so you can scrape desired values:

| Metric | Meaning |
|---|---|
| `xai_trade_orders_total` | Total POST `/wallet-trades/orders` (automatically increments). |
| `xai_trade_matches_total` | Orders that immediately matched (`status != pending`). |
| `xai_trade_secrets_revealed_total` | Secrets successfully revealed for settlement. |
| `xai_walletconnect_sessions_total` | WalletConnect handshakes initiated. |
| `xai_miner_active_count` | Number of miners currently running via `/mining/start`. |

1. Point Prometheus at `http://<node>:8545/metrics` or whichever port you’re using.
2. Create Grafana panels:
   * **Trade volume**: graph `xai_trade_orders_total` (per minute) and overlay `xai_trade_matches_total`.  
   * **Settlement rate**: alert if `xai_trade_secrets_revealed_total` drops to zero for >5 min.  
   * **Miner activity**: display `xai_miner_active_count` and use status panel for on/off toggles.
3. Combine with WebSocket dashboards (channel `wallet-trades`) if you need low-latency alerts.
