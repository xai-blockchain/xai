# XAI Public Testnet Endpoints

## Chain ID

- `xai-testnet-1`

## Live Endpoints

| Service | URL |
|---------|-----|
| **RPC API** | https://testnet-rpc.xaiblockchain.com |
| **Faucet** | https://testnet-faucet.xaiblockchain.com |
| **Explorer** | https://testnet-explorer.xaiblockchain.com |
| **Monitoring** | https://monitoring.xaiblockchain.com |
| **Snapshots** | https://snapshots.xaiblockchain.com |
| **Security Console** | https://console.xaiblockchain.com |

### Direct Server Access (Development)

| Service | Address |
|---------|---------|
| Server IP | 54.39.129.11 |
| VPN IP | 10.10.0.3 |
| RPC | http://54.39.129.11:8545 |

## Get Test Tokens

1. Create a wallet:
   ```bash
   xai-wallet generate-address
   ```

2. Request tokens from the faucet:
   - Visit https://testnet-faucet.xaiblockchain.com
   - Or use the API:
     ```bash
     curl -X POST https://testnet-faucet.xaiblockchain.com/claim \
       -H "Content-Type: application/json" \
       -d '{"address": "TXAI_YOUR_ADDRESS"}'
     ```

3. Check your balance:
   ```bash
   xai-wallet balance --address TXAI_YOUR_ADDRESS
   ```

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

## Network Parameters

| Parameter | Value |
|-----------|-------|
| Network ID | 0xABCD |
| Port | 18545 |
| RPC Port | 18546 |
| Address Prefix | TXAI |
| Block Time | 2 minutes |
| Max Supply | 121,000,000 XAI |

## Status

- **Network**: Active
- **Last Updated**: 2026-01-01
