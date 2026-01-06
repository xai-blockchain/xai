# XAI Project

## Repository Separation

**This repo (`xai/`)** → github:xai-blockchain/xai (source code)
**Testnet repo (`xai-testnets/`)** → github:xai-blockchain/testnets (network config)

### Save HERE (xai/)
- Python source code, blockchain modules
- Tests, requirements.txt, setup.py
- Dockerfiles, docker-compose files
- General docs (README, CONTRIBUTING)

### Save to TESTNET REPO (xai-testnets/xai-testnet-1/)
- config.json, network_info.json
- peers.txt, seeds.txt
- config/.env.example
- SNAPSHOTS.md, README.md

## Testnet Public Endpoints (Cloudflare A Records)

**IMPORTANT**: Always use these registered URLs. Never use raw IPs or localhost.

| Service | URL |
|---------|-----|
| RPC | https://testnet-rpc.xaiblockchain.com |
| REST API | https://testnet-api.xaiblockchain.com |
| WebSocket | wss://testnet-ws.xaiblockchain.com |
| Explorer | https://testnet-explorer.xaiblockchain.com |
| Faucet | https://testnet-faucet.xaiblockchain.com |
| Monitoring | https://monitoring.xaiblockchain.com |
| Status | https://status.xaiblockchain.com |
| Snapshots | https://snapshots.xaiblockchain.com |
| Artifacts | https://artifacts.xaiblockchain.com |

## Testnet SSH Access
```bash
ssh xai-testnet  # 54.39.129.11
```

## Chain Info
- Type: Python blockchain
- Home: `~/xai`
- API: http://localhost:8545

## Health Check
Run `./deploy/scripts/health-check.sh` for XAI-specific health check.

## ⚠️ ACTUAL Port Configuration (XAI-Specific)

**XAI runs multiple Python services on different ports:**

| Service | Port | Bind Address | Notes |
|---------|------|--------------|-------|
| RPC API | 8545 | 0.0.0.0 | Main JSON-RPC endpoint |
| P2P | 8333 | 0.0.0.0 | Node-to-node communication |
| Explorer | 8082 | 0.0.0.0 | Web block explorer |
| Indexer | 8084 | 0.0.0.0 | Transaction indexer API |
| WebSocket | 8766 | 0.0.0.0 | Real-time updates |
| Faucet | 8081 | 0.0.0.0 | Testnet token faucet |

### Internal Access (when SSH'd to xai-testnet)
- RPC: http://127.0.0.1:8545
- Explorer: http://127.0.0.1:8082
- Indexer: http://127.0.0.1:8084
- WebSocket: ws://127.0.0.1:8766
- Faucet: http://127.0.0.1:8081

### Source of Truth
See `~/blockchain-sites/testnet-registry/xai-testnet/chain.json` (on WSL2/decri)

## Services Server (services-testnet / 139.99.149.160 / 10.10.0.4)

Secondary nodes for redundancy, indexers, and shared infrastructure.

```bash
ssh services-testnet  # 139.99.149.160
```

### Secondary Node Ports (on services-testnet)
| Chain | RPC | gRPC | REST | P2P |
|-------|-----|------|------|-----|
| XAI | 8546 | - | - | 8766 |

### Indexers & WebSocket Proxies
| Service | Port |
|---------|------|
| XAI WS Proxy | 4203 |
