# Configuration Management Migration Guide

This guide helps you migrate from the old `config.py` to the new `config_manager.py` system.

## Overview

The new configuration management system provides:

- **Environment-based configs** (dev/staging/testnet/prod)
- **Multiple config sources** (files, environment variables, CLI)
- **Type checking and validation**
- **Better separation of concerns**
- **API-safe public config export**

## Quick Start

### 1. Install Dependencies

```bash
pip install pyyaml==6.0.1
```

### 2. Use the Config Manager

Old way (config.py):
```python
from config import Config

port = Config.DEFAULT_PORT
difficulty = Config.INITIAL_DIFFICULTY
```

New way (config_manager.py):
```python
from config_manager import get_config_manager

config = get_config_manager()
port = config.network.port
difficulty = config.blockchain.difficulty
```

## Migration Steps

### Step 1: Update imports

**blockchain.py:**

Old:
```python
from config import Config

class Blockchain:
    def __init__(self):
        self.difficulty = Config.INITIAL_DIFFICULTY
        self.initial_block_reward = Config.INITIAL_BLOCK_REWARD
        # ...
```

New:
```python
from config_manager import get_config_manager

class Blockchain:
    def __init__(self, config_manager=None):
        self.config = config_manager or get_config_manager()
        self.difficulty = self.config.blockchain.difficulty
        self.initial_block_reward = self.config.blockchain.initial_block_reward
        # ...
```

**node.py:**

Old:
```python
from config import Config

class BlockchainNode:
    def __init__(self, host=None, port=None):
        self.host = host or os.getenv('XAI_HOST', '0.0.0.0')
        self.port = port or int(os.getenv('XAI_PORT', str(Config.DEFAULT_PORT)))
        # ...
```

New:
```python
from config_manager import get_config_manager

class BlockchainNode:
    def __init__(self, host=None, port=None, config_manager=None):
        self.config = config_manager or get_config_manager()
        self.host = host or self.config.network.host
        self.port = port or self.config.network.port
        # ...
```

### Step 2: Configuration Mapping

| Old Config.py | New Config Manager |
|--------------|-------------------|
| `Config.DEFAULT_PORT` | `config.network.port` |
| `Config.DEFAULT_RPC_PORT` | `config.network.rpc_port` |
| `Config.INITIAL_DIFFICULTY` | `config.blockchain.difficulty` |
| `Config.INITIAL_BLOCK_REWARD` | `config.blockchain.initial_block_reward` |
| `Config.HALVING_INTERVAL` | `config.blockchain.halving_interval` |
| `Config.MAX_SUPPLY` | `config.blockchain.max_supply` |
| `Config.BLOCK_TIME_TARGET` | `config.blockchain.block_time_target` |
| `Config.BLOCKCHAIN_FILE` | `config.storage.blockchain_file` |
| `Config.WALLET_DIR` | `config.storage.wallet_dir` |
| `Config.DATA_DIR` | `config.storage.data_dir` |
| `Config.GENESIS_FILE` | `config.genesis.genesis_file` |
| `Config.GENESIS_TIMESTAMP` | `config.genesis.genesis_timestamp` |
| `Config.NETWORK_ID` | `config.genesis.network_id` |
| `Config.ADDRESS_PREFIX` | `config.genesis.address_prefix` |
| `Config.FAUCET_ENABLED` | `config.get('features.faucet_enabled')` |
| `Config.FAUCET_AMOUNT` | `config.get('features.faucet_amount')` |
| `Config.ALLOW_CHAIN_RESET` | `config.get('features.allow_chain_reset')` |

### Step 3: Update Main Entry Points

**Before:**
```python
if __name__ == "__main__":
    from config import Config

    node = BlockchainNode()
    node.run()
```

**After:**
```python
if __name__ == "__main__":
    import argparse
    from config_manager import get_config_manager

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='XAI Blockchain Node')
    parser.add_argument('--environment', default='production',
                       help='Environment: development, testnet, staging, production')
    parser.add_argument('--port', type=int, help='Override port')
    parser.add_argument('--difficulty', type=int, help='Override difficulty')
    args = parser.parse_args()

    # Build CLI overrides
    cli_overrides = {}
    if args.port:
        cli_overrides['network.port'] = args.port
    if args.difficulty:
        cli_overrides['blockchain.difficulty'] = args.difficulty

    # Initialize configuration
    config = get_config_manager(
        environment=args.environment,
        cli_overrides=cli_overrides
    )

    # Create and run node
    node = BlockchainNode(config_manager=config)
    node.run()
```

### Step 4: Add Config Endpoint to API

Add to your Flask/FastAPI app:

```python
@app.route('/config', methods=['GET'])
def get_config():
    """Get public node configuration"""
    config = get_config_manager()
    return jsonify(config.get_public_config())
```

### Step 5: Environment Variables

Update your environment variable usage:

**Old:**
```bash
export XAI_NETWORK=testnet
export XAI_HOST=0.0.0.0
export XAI_PORT=8545
```

**New:**
```bash
export XAI_ENVIRONMENT=testnet
export XAI_NETWORK_HOST=0.0.0.0
export XAI_NETWORK_PORT=8545
export XAI_BLOCKCHAIN_DIFFICULTY=4
export XAI_LOGGING_LEVEL=INFO
```

## Complete Example

Here's a complete example of migrating the Blockchain class:

**Before (config.py):**
```python
from config import Config

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.difficulty = Config.INITIAL_DIFFICULTY
        self.initial_block_reward = Config.INITIAL_BLOCK_REWARD
        self.halving_interval = Config.HALVING_INTERVAL
        self.max_supply = Config.MAX_SUPPLY
        self.transaction_fee_percent = 0.24

        self.create_genesis_block()
```

**After (config_manager.py):**
```python
from config_manager import get_config_manager

class Blockchain:
    def __init__(self, config_manager=None):
        # Get configuration
        self.config = config_manager or get_config_manager()

        # Initialize blockchain
        self.chain = []
        self.pending_transactions = []

        # Use configuration values
        self.difficulty = self.config.blockchain.difficulty
        self.initial_block_reward = self.config.blockchain.initial_block_reward
        self.halving_interval = self.config.blockchain.halving_interval
        self.max_supply = self.config.blockchain.max_supply
        self.transaction_fee_percent = self.config.blockchain.transaction_fee_percent

        self.create_genesis_block()
```

## Testing the Migration

1. **Run the test suite:**
   ```bash
   python tests/test_config_manager.py
   ```

2. **Run the example script:**
   ```bash
   python examples/config_integration_example.py
   ```

3. **Test different environments:**
   ```bash
   # Development
   XAI_ENVIRONMENT=development python -m core.node

   # Testnet
   XAI_ENVIRONMENT=testnet python -m core.node

   # Production
   XAI_ENVIRONMENT=production python -m core.node
   ```

4. **Test environment variable overrides:**
   ```bash
   XAI_NETWORK_PORT=9999 \
   XAI_BLOCKCHAIN_DIFFICULTY=8 \
   XAI_LOGGING_LEVEL=DEBUG \
   python -m core.node
   ```

5. **Test CLI overrides:**
   ```bash
   python -m core.node --environment production --port 9999 --difficulty 8
   ```

## Backwards Compatibility

To maintain backwards compatibility temporarily, you can create a compatibility layer:

**config_compat.py:**
```python
"""
Backwards compatibility layer for old config.py usage
Allows gradual migration
"""

from config_manager import get_config_manager
from enum import Enum

class NetworkType(Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"

class Config:
    """Compatibility wrapper for old Config class"""

    _config = None

    @classmethod
    def _get_config(cls):
        if cls._config is None:
            cls._config = get_config_manager()
        return cls._config

    @classmethod
    @property
    def DEFAULT_PORT(cls):
        return cls._get_config().network.port

    @classmethod
    @property
    def INITIAL_DIFFICULTY(cls):
        return cls._get_config().blockchain.difficulty

    # Add more properties as needed...
```

Then in your code:
```python
# Old code still works
from config_compat import Config
port = Config.DEFAULT_PORT

# New code recommended
from config_manager import get_config_manager
config = get_config_manager()
port = config.network.port
```

## Common Issues

### Issue 1: Config files not found

**Solution:** Ensure config files exist in the `config/` directory:
```bash
ls -la config/
# Should show: default.yaml, development.yaml, production.yaml, etc.
```

### Issue 2: YAML parsing errors

**Solution:** Validate YAML syntax online or use:
```bash
python -c "import yaml; yaml.safe_load(open('config/default.yaml'))"
```

### Issue 3: Environment variables not working

**Solution:** Ensure variables start with `XAI_` and use correct format:
```bash
# Correct
export XAI_NETWORK_PORT=8545

# Wrong
export NETWORK_PORT=8545
```

### Issue 4: Configuration values not changing

**Solution:** Force reload the configuration:
```python
config = get_config_manager(force_reload=True)
```

## Rollback Plan

If you need to rollback:

1. Keep the old `config.py` file
2. Revert import changes in your code
3. Remove config_manager.py import
4. Use the old Config class

The new system is designed to coexist with the old one temporarily.

## Next Steps

1. ✅ Install PyYAML
2. ✅ Review config files in `config/` directory
3. ✅ Update blockchain.py and node.py imports
4. ✅ Test with different environments
5. ✅ Update deployment scripts
6. ✅ Update documentation
7. ✅ Remove old config.py (optional, after full migration)

## Support

For questions or issues:
- Check the examples in `examples/config_integration_example.py`
- Read the config README in `config/README.md`
- Review tests in `tests/test_config_manager.py`
- Check configuration validation error messages
