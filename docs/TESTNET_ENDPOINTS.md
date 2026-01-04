# XAI Public Testnet Endpoints

## Chain ID

`xai-testnet-1`

## Network Status

- **Status**: Active
- **Last Updated**: 2026-01-04

---

## Public Endpoints

| Service | URL |
|---------|-----|
| RPC | https://testnet-rpc.xaiblockchain.com |
| REST API | https://testnet-api.xaiblockchain.com |
| WebSocket | wss://testnet-ws.xaiblockchain.com |
| GraphQL | https://testnet-graphql.xaiblockchain.com/graphql |

---

## Resources

| Resource | URL |
|----------|-----|
| Explorer | https://testnet-explorer.xaiblockchain.com |
| Faucet | https://testnet-faucet.xaiblockchain.com |
| Documentation | https://testnet-docs.xaiblockchain.com |
| Status | https://status.xaiblockchain.com |
| Stats | https://stats.xaiblockchain.com |
| Snapshots | https://snapshots.xaiblockchain.com |
| Artifacts | https://artifacts.xaiblockchain.com |

---

## Monitoring

| Resource | URL |
|----------|-----|
| Grafana | https://monitoring.xaiblockchain.com |

---

## Artifacts

Download testnet configuration files from https://artifacts.xaiblockchain.com:

| File | Description |
|------|-------------|
| [config.json](https://artifacts.xaiblockchain.com/config.json) | Sample node configuration |
| [peers.txt](https://artifacts.xaiblockchain.com/peers.txt) | P2P peer list |
| [network_info.json](https://artifacts.xaiblockchain.com/network_info.json) | Network metadata |

---

## Get Test Tokens

1. Create a wallet:
   ```bash
   xai-wallet generate-address
   ```

2. Request tokens from the faucet:
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
| Address Prefix | TXAI |
| Block Time | 2 minutes |
| Max Supply | 121,000,000 XAI |

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
