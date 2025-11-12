# Configuration System Quick Start Guide

## Installation

```bash
pip install pyyaml==6.0.1
```

## Basic Usage (5 Minutes)

### 1. Import and Use

```python
from config_manager import get_config_manager

# Get config (automatically detects environment)
config = get_config_manager()

# Access configuration
port = config.network.port
difficulty = config.blockchain.difficulty
log_level = config.logging.level
```

### 2. Run Different Environments

```bash
# Development (easy mining, verbose logs)
export XAI_ENVIRONMENT=development
python -m core.node

# Testnet (faucet enabled, testnet prefix)
export XAI_ENVIRONMENT=testnet
python -m core.node

# Production (mainnet settings)
export XAI_ENVIRONMENT=production
python -m core.node
```

### 3. Override Settings with Environment Variables

```bash
# Change port
export XAI_NETWORK_PORT=9999

# Change difficulty
export XAI_BLOCKCHAIN_DIFFICULTY=6

# Change log level
export XAI_LOGGING_LEVEL=DEBUG

python -m core.node
```

### 4. Test It Works

```bash
# Run tests
python tests/test_config_manager.py

# Run examples
python examples/config_integration_example.py
```

## Common Use Cases

### Use Case 1: Running a Development Node

```bash
export XAI_ENVIRONMENT=development
python -m core.node
```

What you get:
- Easy mining (difficulty 2)
- Fast blocks (30 seconds)
- Debug logging
- Faucet enabled (1000 XAI per claim)
- Local only (127.0.0.1)

### Use Case 2: Running a Testnet Node

```bash
export XAI_ENVIRONMENT=testnet
python -m core.node
```

What you get:
- Testnet prefix (TXAI)
- Faucet enabled (100 XAI)
- Moderate difficulty (2)
- Different port (18545)
- Chain reset allowed

### Use Case 3: Running Production Node

```bash
export XAI_ENVIRONMENT=production
python -m core.node
```

What you get:
- Mainnet prefix (AIXN)
- Production difficulty (4)
- Standard port (8545)
- No faucet
- Chain reset forbidden
- Rate limiting enabled

### Use Case 4: Custom Settings

```bash
export XAI_ENVIRONMENT=production
export XAI_NETWORK_PORT=7777
export XAI_NETWORK_MAX_PEERS=100
export XAI_BLOCKCHAIN_DIFFICULTY=8
export XAI_LOGGING_LEVEL=WARNING
python -m core.node
```

### Use Case 5: Get Public Config via API

```python
from flask import Flask, jsonify
from config_manager import get_config_manager

app = Flask(__name__)

@app.route('/config')
def get_config():
    config = get_config_manager()
    return jsonify(config.get_public_config())
```

Then:
```bash
curl http://localhost:8545/config
```

## Configuration Files

Located in `config/` directory:

- **default.yaml** - Base settings
- **development.yaml** - Dev overrides
- **testnet.yaml** - Testnet overrides
- **staging.yaml** - Staging overrides
- **production.yaml** - Production overrides

## Environment Variable Format

All environment variables start with `XAI_` and use format:

```
XAI_SECTION_KEY=value
```

Examples:
```bash
XAI_NETWORK_PORT=8545
XAI_BLOCKCHAIN_DIFFICULTY=4
XAI_SECURITY_RATE_LIMIT_ENABLED=true
XAI_STORAGE_DATA_DIR=/var/lib/xai
XAI_LOGGING_LEVEL=INFO
```

## Available Configurations

### Network Settings
- `network.port` - Node port (default: 8545)
- `network.host` - Bind address (default: 0.0.0.0)
- `network.rpc_port` - RPC port (default: 8546)
- `network.max_peers` - Max peers (default: 50)

### Blockchain Settings
- `blockchain.difficulty` - Mining difficulty (default: 4)
- `blockchain.block_time_target` - Block time in seconds (default: 120)
- `blockchain.initial_block_reward` - Initial reward (default: 12.0)
- `blockchain.max_supply` - Max supply (default: 121,000,000)

### Security Settings
- `security.rate_limit_enabled` - Enable rate limiting (default: true)
- `security.rate_limit_requests` - Max requests per window (default: 100)
- `security.ban_threshold` - Violations before ban (default: 10)
- `security.max_mempool_size` - Max pending tx (default: 10,000)

### Storage Settings
- `storage.data_dir` - Data directory (default: "data")
- `storage.blockchain_file` - Blockchain file (default: "blockchain.json")
- `storage.backup_enabled` - Enable backups (default: true)

### Logging Settings
- `logging.level` - Log level (default: "INFO")
- `logging.log_file` - Log file path (default: "logs/node.log")
- `logging.enable_console_logging` - Console logs (default: true)

## Quick Reference

### Python API

```python
from config_manager import get_config_manager

# Initialize
config = get_config_manager()
config = get_config_manager(environment="production")
config = get_config_manager(environment="testnet", cli_overrides={"network.port": 9999})

# Access typed configs
config.network.port
config.blockchain.difficulty
config.security.rate_limit_enabled
config.storage.data_dir
config.logging.level

# Get with dot notation
config.get("network.port")
config.get("blockchain.difficulty")

# Get section
config.get_section("network")

# Public config (for API)
config.get_public_config()

# Reload
config.reload()
```

### Command Line

```bash
# Set environment
export XAI_ENVIRONMENT=production

# Override settings
export XAI_NETWORK_PORT=9999
export XAI_BLOCKCHAIN_DIFFICULTY=6

# Run node
python -m core.node
```

## Troubleshooting

**Config not loading?**
```bash
# Check files exist
ls -la config/

# Verify YAML syntax
python -c "import yaml; yaml.safe_load(open('config/default.yaml'))"
```

**Environment variables not working?**
```bash
# Must start with XAI_
export XAI_NETWORK_PORT=8545  # ✓ Correct
export NETWORK_PORT=8545       # ✗ Wrong
```

**Values not changing?**
```python
# Force reload
config = get_config_manager(force_reload=True)
```

## Next Steps

1. Review full documentation: `config/README.md`
2. See migration guide: `CONFIGURATION_MIGRATION_GUIDE.md`
3. Run examples: `python examples/config_integration_example.py`
4. Run tests: `python tests/test_config_manager.py`

## Support

- Configuration examples: `examples/config_integration_example.py`
- Test suite: `tests/test_config_manager.py`
- Full docs: `config/README.md`
- Migration: `CONFIGURATION_MIGRATION_GUIDE.md`
