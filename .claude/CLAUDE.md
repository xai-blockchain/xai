# XAI Blockchain

## R2 Artifacts
- **Bucket**: `xai-testnet-artifacts`
- **URL**: https://artifacts.xaiblockchain.com
- **Account ID**: `069b2e071fe1c5bea116a29786f2074c`

### Upload Artifacts
```bash
# Env vars pre-configured in ~/.bashrc
wrangler r2 object put xai-testnet-artifacts/genesis.json --file genesis.json --remote
wrangler r2 object put xai-testnet-artifacts/config.json --file config.json --remote
wrangler r2 object put xai-testnet-artifacts/snapshot.tar.gz --file snapshot.tar.gz --remote
```

### Delete
```bash
wrangler r2 object delete xai-testnet-artifacts/<path> --remote
```

## Testnet Server

SSH key for testnet is stored at `.ssh_testnet_key` in repo root.

```bash
# Connect to XAI testnet
ssh -i /home/hudson/blockchain-projects/xai/.ssh_testnet_key ubuntu@54.39.129.11

# Or if ~/.ssh/config is set up:
ssh xai-testnet
```

## Chain Info
- Type: Python blockchain
- Home: `~/xai`
- API: http://localhost:8545
