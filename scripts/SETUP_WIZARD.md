# XAI Node Setup Wizard

Interactive configuration tool for new XAI node operators.

## Features

- Beginner-friendly interface with colorful ASCII art
- **System requirements check**: Python version, dependencies, network connectivity
- **Disk space verification**: Ensures adequate storage for selected node mode
- Network selection (testnet/mainnet) with safety warnings
- Node mode selection (full/pruned/light/archival)
- Mining configuration with optional wallet creation
- **Monitoring setup**: Prometheus metrics configuration
- Port configuration with automatic conflict detection
- Secure secret generation for production use (JWT, encryption keys, etc.)
- .env file generation with automatic backup
- **Systemd service generation**: Auto-start configuration for Linux
- **Wallet integration**: Uses xai.core.wallet_factory when available
- Optional wallet creation with mnemonic backup
- Testnet token request guidance
- Comprehensive next steps and documentation

## Quick Start

### Option 1: Run from Project Directory

```bash
cd /home/hudson/blockchain-projects/xai
./scripts/setup_wizard.sh
```

### Option 2: Run Python Wizard Directly

```bash
cd /home/hudson/blockchain-projects/xai
python3 scripts/setup_wizard.py
```

### Option 3: Remote Installation (Future)

```bash
curl -sSL https://xai.example.com/install | bash
```

## Requirements

- Python 3.10 or higher (wizard checks and warns if below 3.10)
- Standard library only (no external dependencies for wizard itself)
- Terminal with ANSI color support (optional, auto-detects)
- Recommended: flask, requests, cryptography, eth_keys, ecdsa for full functionality

## What the Wizard Does

### 1. Network Selection

Choose between testnet (recommended for beginners) and mainnet (production).

- **Testnet**: Safe environment for testing and learning
- **Mainnet**: Production network with real economic value

The wizard includes safety warnings for mainnet and confirms your choice.

### 2. Node Mode Selection

Choose the storage and sync requirements that fit your needs:

- **Full Node**: Store complete blockchain (~50GB, recommended)
- **Pruned Node**: Store recent blocks only (~10GB)
- **Light Node**: Minimal storage, depends on full nodes (~1GB)
- **Archival Node**: Store all historical states (~500GB, for developers)

### 3. Data Directory

Specify where blockchain data should be stored. Default: `~/.xai`

The wizard will:
- Create the directory if it doesn't exist
- Warn if the directory already exists
- Use absolute paths for consistency

### 4. Port Configuration

Configure network ports with XAI's allocated range (12000-12999):

- **RPC Port**: JSON-RPC API endpoint (default: 12001)
- **P2P Port**: Peer-to-peer networking (default: 12002)
- **WebSocket Port**: Real-time updates (default: 12003)

The wizard checks for port conflicts and warns about ports outside the recommended range.

### 5. Mining Configuration

Enable mining to help secure the network and earn rewards:

- Option to enable/disable mining
- Mining address validation (XAI1... or 0x... format)
- Option to use existing wallet or create new one
- Can be enabled later if skipped

### 6. Monitoring Configuration (NEW)

Optional Prometheus metrics for monitoring:

- Enable/disable metrics collection
- Configure metrics port (default: 12090)
- Access metrics at http://localhost:12090/metrics

### 7. Security Secrets

Automatically generates cryptographically secure secrets:

- **JWT Secret**: For API authentication (64 hex characters)
- **Wallet Trade Secret**: For peer-to-peer trades (64 hex characters)
- **Time Capsule Master Key**: For time-locked transactions (64 hex characters)
- **Embedded Salt**: For wallet encryption (64 hex characters)
- **Lucky Block Seed**: For randomness generation (64 hex characters)

On mainnet, these secrets are required and the wizard emphasizes their importance.

### 7. Configuration File

Creates `.env` file with all configuration:

- Backs up existing `.env` if present (timestamped backup)
- Sets restrictive permissions (0600 - owner read/write only)
- Includes comments and examples
- Never commits to git (protected by .gitignore)

### 8. Wallet Creation (Optional)

Create a new wallet with:

- Unique XAI address
- Private key (secp256k1)
- 12-word mnemonic phrase
- Optional save to secure file (0600 permissions)

**Important**: The wizard emphasizes the importance of securing wallet credentials.

### 9. Testnet Tokens (Optional)

For testnet setups with new wallets:

- Provides faucet URL
- Shows Discord community link
- Displays wallet address for easy copying

### 10. Next Steps

Comprehensive guide including:

- How to start the node
- How to check node status
- How to start mining (if enabled)
- Links to block explorer and Grafana
- Documentation references

Option to start the node immediately after setup.

## Generated Files

### `.env` File

Located at project root: `/home/hudson/blockchain-projects/xai/.env`

Contains:
- Network configuration
- Port settings
- Data directory path
- Mining settings
- Security secrets
- Optional API keys
- Database URL

Permissions: `0600` (owner read/write only)

### Wallet File (Optional)

Located at: `<data_dir>/wallets/wallet_<address>.json`

Contains:
- Wallet address
- Private key
- Mnemonic phrase
- Creation timestamp
- Network

Permissions: `0600` (owner read/write only)

### Backup Files

If `.env` already exists, a timestamped backup is created:

`.env.backup.YYYYMMDD_HHMMSS`

## Security Considerations

### Mainnet Mode

The wizard enforces extra security for mainnet:

- Requires explicit confirmation
- Generates secure random secrets
- Displays security warnings
- Emphasizes backup importance

### Secret Management

All secrets are:
- Generated using Python's `secrets` module (cryptographically secure)
- 256-bit entropy (64 hex characters)
- Never logged or displayed after initial generation
- Stored in `.env` with 0600 permissions

### Wallet Security

If wallet creation is used:

- Private keys are generated with `secrets.token_hex(32)`
- Mnemonic phrases use standard BIP-39 wordlist
- Files are saved with 0600 permissions
- User is warned about backup importance
- Option to decline file storage (manual backup only)

## Port Conflict Detection

The wizard uses `socket.socket()` to check if ports are available:

```python
def is_port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False
```

If a port is unavailable:
- User is warned
- Option to choose different port
- Can proceed with warning if needed

## Address Validation

XAI addresses are validated using basic format checks:

- Must start with "XAI1" (40+ characters) or "0x" (42 characters)
- Hex character validation
- Checksum validation (in full implementation)

```python
def validate_xai_address(address: str) -> bool:
    if address.startswith("XAI1"):
        return len(address) >= 40
    elif address.startswith("0x"):
        return len(address) == 42
    return False
```

## Color Support

ANSI colors are used for better UX:

- **Cyan**: Informational messages and prompts
- **Green**: Success messages
- **Yellow**: Warnings
- **Red**: Errors
- **Blue**: Headers and sections

Colors are automatically disabled if:
- Output is not a TTY (piped/redirected)
- User requests with environment variable

## Error Handling

The wizard handles:

- **KeyboardInterrupt** (Ctrl+C): Graceful cancellation
- **EOFError**: Input stream closed
- **ValueError**: Invalid numeric input
- **OSError**: File/socket operations
- **Permission errors**: File creation/chmod

All errors display helpful messages and guide the user to resolution.

## Customization

### Environment Variables

Pre-set values via environment variables:

```bash
export XAI_NETWORK=testnet
export XAI_DATA_DIR=~/.xai
export XAI_NODE_PORT=12001
./scripts/setup_wizard.sh
```

The wizard will use these as defaults.

### Non-Interactive Mode

For automation, create `.env` manually or use templates:

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Integration with Existing Tools

### node_wizard.py

The existing `node_wizard.py` is simpler and focuses on:
- Single-node testnet setup
- Quick start for developers
- No wallet creation
- No security emphasis

`setup_wizard.py` is more comprehensive:
- Production-ready configuration
- Mainnet support with security warnings
- Wallet creation and management
- Full validation and error handling

Both can coexist. Use `setup_wizard.py` for production deployments.

## Testing the Wizard

### Dry Run

The wizard doesn't make changes until the final confirmation step.

You can:
1. Run through all prompts
2. Review the summary
3. Cancel before writing configuration

### Test Cases

Test different scenarios:

```bash
# Testnet with mining
./scripts/setup_wizard.sh

# Mainnet without mining
XAI_NETWORK=mainnet ./scripts/setup_wizard.sh

# Custom data directory
XAI_DATA_DIR=/mnt/blockchain ./scripts/setup_wizard.sh

# Non-default ports
XAI_NODE_PORT=15000 ./scripts/setup_wizard.sh
```

## Troubleshooting

### Python Not Found

```
Error: Python is not installed!
```

Install Python 3.8+:

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# Fedora/RHEL
sudo dnf install python3 python3-pip

# macOS
brew install python3
```

### Port Already in Use

```
Error: Port 12001 is already in use!
```

Options:
1. Stop the service using that port
2. Choose a different port
3. Use the wizard's port detection to find available ports

### Permission Denied

```
Error: Permission denied: .env
```

Ensure you have write permissions in the project directory:

```bash
chmod u+w /home/hudson/blockchain-projects/xai/.env
```

### Wallet Creation Failed

If wallet creation encounters errors, you can:
1. Create wallet manually later using `xai-cli wallet create`
2. Import existing wallet
3. Re-run wizard after fixing issues

## Command Reference

### Start Setup Wizard

```bash
# Via bash wrapper (recommended)
./scripts/setup_wizard.sh

# Direct Python execution
python3 scripts/setup_wizard.py

# From any directory
/home/hudson/blockchain-projects/xai/scripts/setup_wizard.sh
```

### After Setup

```bash
# Start node
python -m xai.core.node

# Or use the testnet startup script
./src/xai/START_TESTNET.sh

# Check status
curl http://localhost:12001/health

# View blocks
curl http://localhost:12001/blocks
```

### Mining Commands

```bash
# Start mining (if configured)
curl -X POST http://localhost:12001/mining/start \
  -H 'Content-Type: application/json' \
  -d '{"miner_address":"XAI1...", "threads":2}'

# Stop mining
curl -X POST http://localhost:12001/mining/stop

# Check mining status
curl http://localhost:12001/mining/status
```

## Future Enhancements

Potential improvements:

1. **Hardware Wallet Support**: Ledger/Trezor integration
2. **Multi-Node Setup**: Configure multiple validators
3. **Docker Support**: Generate docker-compose.yml
4. **Backup/Restore**: Built-in configuration backup
5. **Update Check**: Notify of new versions
6. **Network Test**: Verify internet connectivity and port forwarding
7. **Resource Check**: Validate disk space and RAM
8. **Config Migration**: Upgrade old configurations
9. **Plugin System**: Extend with custom modules
10. **Web Interface**: Browser-based wizard

## Contributing

To improve the wizard:

1. Test on different systems (Linux, macOS, Windows/WSL)
2. Add validation for edge cases
3. Improve error messages
4. Enhance security features
5. Add more comprehensive address validation
6. Integrate with actual wallet generation code

## License

Same as the XAI project.

## Support

- Documentation: https://docs.xai.network
- Discord: https://discord.gg/xai-network
- GitHub: https://github.com/xai-network/xai
- Issues: https://github.com/xai-network/xai/issues
