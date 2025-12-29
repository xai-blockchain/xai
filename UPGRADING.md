# Upgrading XAI Blockchain

Guide for upgrading between XAI versions.

## Version Compatibility

| From Version | To Version | Migration Required | Downtime |
|--------------|------------|-------------------|----------|
| 0.1.x | 0.2.x | Yes | Rolling |
| 0.2.x | 0.3.x | No | Zero |

## Before Upgrading

1. **Backup your data**
   ```bash
   cp -r ~/.xai ~/.xai.backup.$(date +%Y%m%d)
   ```

2. **Check disk space** - Need 2x current data size for safe migration

3. **Review changelog** - See [CHANGELOG.md](CHANGELOG.md) for breaking changes

## Upgrade Steps

### Standard Upgrade (Zero Downtime)

```bash
# 1. Pull latest code
git fetch origin && git checkout v0.x.x

# 2. Install dependencies
pip install -c constraints.txt -e .

# 3. Restart node
systemctl restart xai-node  # or your process manager
```

### Database Migration (v0.1 → v0.2)

```bash
# 1. Stop node
systemctl stop xai-node

# 2. Run migration
python -m xai.tools.migrate --from 0.1 --to 0.2

# 3. Verify migration
python -m xai.core.node --verify-only

# 4. Start node
systemctl start xai-node
```

## Breaking Changes by Version

### v0.2.0
- **API**: `/tx` endpoint renamed to `/transactions`
- **Config**: `MINING_THREADS` moved to `mining.threads` in config.yaml
- **DB**: UTXO index format changed (auto-migrated on startup)

### v0.1.0
- Initial release

## Rollback Procedure

If upgrade fails:

```bash
# 1. Stop node
systemctl stop xai-node

# 2. Restore backup
rm -rf ~/.xai && cp -r ~/.xai.backup.YYYYMMDD ~/.xai

# 3. Checkout previous version
git checkout v0.1.x

# 4. Reinstall
pip install -c constraints.txt -e .

# 5. Start node
systemctl start xai-node
```

## Validator Upgrades

For validators, coordinate with network:

1. Announce upgrade window in Discord
2. Wait for 2/3 validators to be ready
3. Upgrade during low-activity period
4. Monitor consensus after upgrade

## Troubleshooting

### Node won't start after upgrade
```bash
# Check logs
journalctl -u xai-node -n 100

# Verify database
python -m xai.tools.verify_db
```

### Chain sync issues
```bash
# Force resync from checkpoint
python -m xai.core.node --resync --checkpoint latest
```

### API compatibility issues
- Use `/api/v1/` prefix for versioned endpoints
- Check deprecation warnings in logs

## Getting Help

- **Discord**: #node-operators channel
- **GitHub Issues**: [xai-blockchain/xai/issues](https://github.com/xai-blockchain/xai/issues)
- **Docs**: [docs/deployment/production.md](docs/deployment/production.md)
