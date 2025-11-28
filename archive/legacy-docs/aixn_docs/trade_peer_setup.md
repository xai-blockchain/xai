## Wallet-Trade Peer Configuration

To enable gossip/snapshot replication children across nodes:

1. **Set peer secrets** via environment:
   ```
   export XAI_WALLET_TRADE_PEER_SECRET=your-shared-secret
   export XAI_WALLET_TRADE_PEERS=http://node1:8545,http://node2:8545
   ```
2. **Restart each node** so the new peers register via `/wallet-trades/peers/register`. The API will accept a JSON `{ "host": "http://peer:8545", "secret": "..." }`.
3. **Verify gossip** by calling `/wallet-trades/snapshot` from each node to ensure orders/matches align.
4. **Optional helper**: run `python scripts/register_trade_peer.py http://peer:8545` to send the registration payload automatically.

The nodes now call `/wallet-trades/gossip` on every trade to propagate orders. If a node restarts, it replays `wallet_trades/orderbook_snapshot.json` and begins gossiping again.
