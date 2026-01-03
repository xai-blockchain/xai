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

Use the pre-configured SSH alias:

```bash
ssh xai-testnet  # 54.39.129.11
```

The SSH config is in `~/.ssh/config`. Never store SSH keys in repositories.

## Chain Info
- Type: Python blockchain
- Home: `~/xai`
- API: http://localhost:8545
