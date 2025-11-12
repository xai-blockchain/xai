# XAI Blockchain Configuration System

## Overview

The XAI blockchain uses a sophisticated configuration management system that supports multiple environments, file-based configuration, environment variables, and command-line overrides.

## Configuration Files

- **default.yaml** - Base configuration that applies to all environments
- **development.yaml** - Development environment overrides
- **testnet.yaml** - Testnet environment overrides
- **staging.yaml** - Staging/pre-production environment overrides
- **production.yaml** - Production/mainnet environment overrides

## Configuration Precedence

Configuration values are loaded with the following precedence (highest to lowest):

1. **Command-line arguments** (highest priority)
2. **Environment variables** (XAI_*)
3. **Environment-specific config file** (e.g., production.yaml)
4. **Default config file** (default.yaml)
5. **Built-in defaults** (lowest priority)

## Environment Variables

All configuration values can be overridden using environment variables with the format:

```bash
XAI_SECTION_KEY=value
```

### Examples:

```bash
# Set environment
export XAI_ENVIRONMENT=production

# Network settings
export XAI_NETWORK_PORT=8545
export XAI_NETWORK_HOST=0.0.0.0
export XAI_NETWORK_MAX_PEERS=100

# Blockchain settings
export XAI_BLOCKCHAIN_DIFFICULTY=6
export XAI_BLOCKCHAIN_BLOCK_TIME_TARGET=60

# Security settings
export XAI_SECURITY_RATE_LIMIT_ENABLED=true
export XAI_SECURITY_RATE_LIMIT_REQUESTS=50

# Storage settings
export XAI_STORAGE_DATA_DIR=/var/lib/xai
export XAI_STORAGE_BACKUP_ENABLED=true

# Logging settings
export XAI_LOGGING_LEVEL=DEBUG
export XAI_LOGGING_LOG_FILE=/var/log/xai/node.log
```

## Configuration Sections

### Network Configuration

Controls network and P2P settings:

- `port` - Node listening port (default: 8545)
- `host` - Bind address (default: 0.0.0.0)
- `rpc_port` - RPC port (default: 8546)
- `max_peers` - Maximum peer connections (default: 50)
- `peer_timeout` - Peer connection timeout in seconds (default: 30)
- `sync_interval` - Blockchain sync interval in seconds (default: 60)
- `p2p_enabled` - Enable P2P networking (default: true)

### Blockchain Configuration

Core blockchain parameters:

- `difficulty` - Mining difficulty (default: 4)
- `block_time_target` - Target block time in seconds (default: 120)
- `initial_block_reward` - Initial mining reward (default: 12.0)
- `halving_interval` - Blocks between halvings (default: 262800)
- `max_supply` - Maximum token supply (default: 121000000.0)
- `max_block_size` - Maximum block size in bytes (default: 1048576)
- `min_transaction_fee` - Minimum transaction fee (default: 0.0001)
- `transaction_fee_percent` - Transaction fee percentage (default: 0.24)

### Security Configuration

Security and rate limiting settings:

- `rate_limit_enabled` - Enable rate limiting (default: true)
- `rate_limit_requests` - Requests per window (default: 100)
- `rate_limit_window` - Rate limit window in seconds (default: 60)
- `ban_threshold` - Violations before ban (default: 10)
- `ban_duration` - Ban duration in seconds (default: 3600)
- `enable_ip_whitelist` - Enable IP whitelist (default: false)
- `ip_whitelist` - List of whitelisted IPs
- `enable_ip_blacklist` - Enable IP blacklist (default: true)
- `ip_blacklist` - List of blacklisted IPs
- `max_transaction_size` - Max transaction size in bytes (default: 102400)
- `max_mempool_size` - Max pending transactions (default: 10000)

### Storage Configuration

Data storage and backup settings:

- `data_dir` - Data directory path (default: "data")
- `blockchain_file` - Blockchain file name (default: "blockchain.json")
- `wallet_dir` - Wallet directory path (default: "wallets")
- `backup_enabled` - Enable automatic backups (default: true)
- `backup_frequency` - Backup interval in seconds (default: 3600)
- `backup_retention` - Backup retention in days (default: 7)
- `max_backup_count` - Maximum backup files (default: 10)
- `enable_compression` - Compress backups (default: true)

### Logging Configuration

Logging behavior settings:

- `level` - Log level: DEBUG/INFO/WARNING/ERROR/CRITICAL (default: INFO)
- `format` - Log message format
- `enable_file_logging` - Write logs to file (default: true)
- `log_file` - Log file path (default: "logs/node.log")
- `max_log_size` - Max log file size in bytes (default: 10485760)
- `log_retention` - Log retention in days (default: 7)
- `enable_console_logging` - Print logs to console (default: true)
- `enable_anonymous_logging` - Anonymize logs (default: true)

### Genesis Configuration

Genesis block parameters:

- `genesis_file` - Genesis block file name
- `genesis_timestamp` - Genesis timestamp
- `network_id` - Network identifier
- `address_prefix` - Address prefix (AIXN for mainnet, TXAI for testnet)

## Usage Examples

### Python Code

```python
from config_manager import get_config_manager

# Initialize config manager
config = get_config_manager(environment="production")

# Access configuration
port = config.network.port
difficulty = config.blockchain.difficulty
log_level = config.logging.level

# Get value with dot notation
max_supply = config.get("blockchain.max_supply")

# Get entire section
network_config = config.get_section("network")

# Get public config (for API exposure)
public_config = config.get_public_config()

# Reload configuration
config.reload()
```

### Command-Line Arguments

```python
from config_manager import get_config_manager

# CLI overrides
cli_overrides = {
    "network.port": 9545,
    "blockchain.difficulty": 6,
    "logging.level": "DEBUG"
}

config = get_config_manager(
    environment="production",
    cli_overrides=cli_overrides
)
```

### Running the Node

```bash
# Using environment variables
export XAI_ENVIRONMENT=production
export XAI_NETWORK_PORT=8545
python -m core.node

# Using config directory
python -m core.node --config-dir /etc/xai/config

# Testnet
export XAI_ENVIRONMENT=testnet
python -m core.node

# Development
export XAI_ENVIRONMENT=development
python -m core.node
```

## Environment Comparison

| Setting | Development | Testnet | Staging | Production |
|---------|------------|---------|---------|------------|
| Port | 8545 | 18545 | 9545 | 8545 |
| Difficulty | 2 | 2 | 3 | 4 |
| Block Time | 30s | 120s | 120s | 120s |
| P2P | Disabled | Enabled | Enabled | Enabled |
| Rate Limiting | Disabled | Enabled | Enabled | Enabled |
| Faucet | Enabled (1000) | Enabled (100) | Enabled (50) | Disabled |
| Chain Reset | Allowed | Allowed | Allowed | NOT Allowed |
| Log Level | DEBUG | INFO | DEBUG | INFO |
| Backups | Disabled | Enabled | Enabled | Enabled |

## Configuration Validation

The configuration manager automatically validates all settings on load:

- Port numbers must be valid (1024-65535)
- Difficulty must be reasonable (1-32)
- Timing values must be positive
- File paths are validated
- Log levels are checked against valid values

Invalid configurations will raise detailed error messages.

## Security Considerations

- Never commit sensitive values to config files
- Use environment variables for secrets
- The `get_public_config()` method filters sensitive values for API exposure
- In production, ensure proper file permissions on config files
- Anonymous logging is enabled by default to protect user privacy

## Extending Configuration

To add new configuration sections:

1. Add a new `@dataclass` in `config_manager.py`
2. Add a `validate()` method to the dataclass
3. Update the `_parse_configuration()` method
4. Add the section to config YAML files
5. Update this README

## Troubleshooting

### Configuration not loading

- Check file paths and permissions
- Verify YAML syntax (use online validator)
- Check environment variable names (must start with XAI_)

### Values not overriding

Remember the precedence order:
1. CLI args (highest)
2. Environment variables
3. Environment-specific file
4. Default file
5. Built-in defaults (lowest)

### Validation errors

Read the error message - it will indicate which setting is invalid and why.

## Support

For configuration issues, check:
- This README
- Example config files in this directory
- Environment variable examples above
- Code documentation in `config_manager.py`
