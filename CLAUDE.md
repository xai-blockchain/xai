# XAI Project Guidelines

**Read `../CLAUDE.md` first** - contains all general instructions.

## Project-Specific
- **Framework**: Python (NOT Cosmos SDK)
- **Virtual Env**: `source venv/bin/activate`
- **Install**: `pip install -e .`
- **Tests**: `pytest tests/ -v`

## Testnet Access
- **Server**: `ssh xai-testnet` (54.39.129.11)
- **Node Port**: 8545
- **CLI Wrapper**: `~/xai-cli.sh`
- **Home**: `~/xai`
- **VPN**: 10.10.0.3

### Quick Commands
```bash
# Bash wrapper
~/xai-cli.sh stats
~/xai-cli.sh blocks

# Direct curl
curl -s http://localhost:8545/stats | jq
```

**Full docs**: See `TESTNET_INFRASTRUCTURE.md`
