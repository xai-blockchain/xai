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
