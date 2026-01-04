# XAI Public Testnet Endpoints

## Chain ID

- `xai-testnet-1`

---

## Public Endpoints (Updated 2026-01-03)

| Service | URL | Status |
|---------|-----|--------|
| **RPC** | https://testnet-rpc.xaiblockchain.com | OK |
| **REST API** | https://testnet-api.xaiblockchain.com | OK |
| **gRPC** | https://testnet-grpc.xaiblockchain.com | OK |
| **WebSocket** | wss://testnet-ws.xaiblockchain.com | OK |
| **GraphQL** | https://testnet-graphql.xaiblockchain.com/graphql | OK |
| **Explorer** | https://testnet-explorer.xaiblockchain.com | OK |
| **Faucet** | https://testnet-faucet.xaiblockchain.com | OK |
| **Archive RPC** | https://testnet-archive.xaiblockchain.com | OK |
| **Docs** | https://testnet-docs.xaiblockchain.com | OK |
| **Monitoring** | https://monitoring.xaiblockchain.com | OK |
| **Status** | https://status.xaiblockchain.com | OK |
| **Stats** | https://stats.xaiblockchain.com | OK |
| **Console** | https://console.xaiblockchain.com | OK |
| **Snapshots** | https://snapshots.xaiblockchain.com | OK |
| **Artifacts** | https://artifacts.xaiblockchain.com | OK |

---

## Public Artifacts

Download testnet configuration files from https://artifacts.xaiblockchain.com:

| File | URL | Description |
|------|-----|-------------|
| config.json | [Download](https://artifacts.xaiblockchain.com/config.json) | Sample node configuration |
| peers.txt | [Download](https://artifacts.xaiblockchain.com/peers.txt) | P2P peer list |
| network_info.json | [Download](https://artifacts.xaiblockchain.com/network_info.json) | Network metadata |

---

### Direct Server Access (Operators)

| Service | Address |
|---------|---------|
| Server IP | 54.39.129.11 |
| VPN IP | 10.10.0.3 |
| RPC (node1) | http://127.0.0.1:8545 |
| RPC (node2) | http://127.0.0.1:8555 |
| WebSocket | ws://127.0.0.1:8765 |
| GraphQL | http://127.0.0.1:4102/graphql |

---

## Get Test Tokens

1. Create a wallet:
   ```bash
   xai-wallet generate-address
   ```

2. Request tokens from the faucet:
   - Visit https://testnet-faucet.xaiblockchain.com
   - Or use the CLI:
     ```bash
     xai-wallet request-faucet \
       --address TXAI_YOUR_ADDRESS \
       --base-url https://testnet-faucet.xaiblockchain.com
     ```
   - Or use the API:
     ```bash
     curl -X POST https://testnet-faucet.xaiblockchain.com/faucet/claim \
       -H "Content-Type: application/json" \
       -d '{"address": "TXAI_YOUR_ADDRESS"}'
     ```

3. Check your balance:
   ```bash
   xai-wallet balance --address TXAI_YOUR_ADDRESS --base-url https://testnet-rpc.xaiblockchain.com
   ```

---

## Quick Commands

```bash
# Check node status
curl -s https://testnet-rpc.xaiblockchain.com/stats | jq

# Get latest blocks
curl -s https://testnet-rpc.xaiblockchain.com/blocks | jq

# Get specific block
curl -s https://testnet-rpc.xaiblockchain.com/blocks/0 | jq

# Check balance
curl -s https://testnet-rpc.xaiblockchain.com/balance/TXAI_YOUR_ADDRESS | jq
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats` | GET | Blockchain statistics |
| `/health` | GET | Health check |
| `/blocks` | GET | List blocks |
| `/blocks/{id}` | GET | Get block by index/hash |
| `/transactions` | GET | Pending transactions |
| `/transaction/{hash}` | GET | Get transaction |
| `/balance/{address}` | GET | Get balance |
| `/peers` | GET | Connected peers |

---

## Network Parameters

| Parameter | Value |
|-----------|-------|
| Network ID | 0xABCD |
| Port | 18545 |
| RPC Port | 18546 |
| Address Prefix | TXAI |
| Block Time | 2 minutes |
| Max Supply | 121,000,000 XAI |

---

## Status

- **Network**: Active (public endpoints partially degraded)
- **Last Updated**: 2026-01-03
