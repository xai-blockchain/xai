# XAI Setup Wizard Guide

Interactive setup tool for configuring XAI blockchain nodes, wallets, and development environments.

## Overview

The XAI Setup Wizard is a beginner-friendly command-line tool that guides you through setting up your XAI node or wallet. It detects your operating system, checks prerequisites, and configures everything needed to get started with XAI.

## Features

- **OS Detection**: Automatically detects Linux, macOS, or Windows
- **Prerequisites Check**: Verifies Python 3.10+, pip, and git
- **Multiple Setup Modes**: Full Node, Light Client, Wallet Only, or Developer Mode
- **Interactive Configuration**: Step-by-step prompts with clear explanations
- **Progress Indicators**: Visual progress bars and step counters
- **Security**: Automatic generation of secure secrets and encryption keys
- **Safe Re-run**: Can be run multiple times, backs up existing configurations
- **Wallet Creation**: Optional secure wallet generation with mnemonic backup
- **Network Selection**: Choose between Testnet (recommended) and Mainnet
- **Port Configuration**: Automatic conflict detection and resolution

## Quick Start

### Run the Wizard

```bash
# From XAI project directory
cd /path/to/xai
./scripts/setup_wizard.sh

# Or run Python script directly
python3 scripts/setup_wizard.py
```

### First-Time User Recommendations

1. **Start with Testnet**: Choose testnet for your first setup
2. **Full Node**: Select Full Node mode for complete blockchain experience
3. **Create Wallet**: Let the wizard create a wallet for you
4. **Save Credentials**: Write down your mnemonic phrase immediately

## Setup Modes

### 1. Full Node

**Best for**: Users who want to validate transactions and support the network

**Features**:
- Complete blockchain synchronization
- Transaction validation
- Can serve as RPC endpoint for other applications
- Optional mining

**Requirements**:
- ~50GB disk space (Full) or ~10GB (Pruned)
- Stable internet connection
- Moderate CPU/RAM

**Setup Process**:
```
1. System check
2. Choose "Full Node" mode
3. Select network (testnet/mainnet)
4. Configure node type (full/pruned/archival)
5. Set data directory
6. Configure ports
7. Optional: Enable mining
8. Optional: Create wallet
```

### 2. Light Client

**Best for**: Users with limited resources or mobile devices

**Features**:
- Minimal storage (~1GB)
- Fast synchronization
- Depends on full nodes for data
- Can send/receive transactions

**Requirements**:
- ~1GB disk space
- Internet connection
- Minimal CPU/RAM

**Setup Process**:
```
1. System check
2. Choose "Light Client" mode
3. Select network
4. Set data directory
5. Configure connection settings
6. Optional: Create wallet
```

### 3. Wallet Only

**Best for**: Users who only need to manage XAI tokens

**Features**:
- No blockchain sync required
- Wallet management
- Transaction signing
- Connect to remote RPC nodes

**Requirements**:
- ~100MB disk space
- Internet connection for transactions
- Minimal resources

**Setup Process**:
```
1. System check
2. Choose "Wallet Only" mode
3. Set wallet directory
4. Create or import wallet
5. Configure RPC endpoint (optional)
```

### 4. Developer Mode

**Best for**: Developers building on XAI

**Features**:
- Full node capabilities
- Mining enabled by default
- Development tools
- Test environment setup
- API access configured

**Requirements**:
- ~50GB+ disk space
- Good internet connection
- Moderate to high CPU/RAM

**Setup Process**:
```
1. System check
2. Choose "Developer Mode"
3. Select network (testnet recommended)
4. Configure full node settings
5. Enable mining
6. Create development wallet
7. Set up test environment
```

## Step-by-Step Walkthrough

### Step 1: System Requirements Check

The wizard automatically detects and verifies:

- **Operating System**: Linux, macOS, or Windows
- **Python Version**: 3.10 or higher required
- **git**: Optional but recommended
- **pip**: Required for installing dependencies
- **Python Dependencies**: flask, requests, cryptography, eth_keys, ecdsa
- **Network Connectivity**: Internet connection test

**Example Output**:
```
Step 1/11: System Requirements Check
================================================================

✓ Operating System: Ubuntu 22.04.3 LTS 6.14.0-37-generic
ℹ Platform: linux
✓ Python version: 3.12.3
✓ git version: 2.43.0
✓ pip version: 24.0
ℹ Checking Python dependencies...
✓ flask: 3.0.0
✓ requests: 2.31.0
✓ cryptography: 41.0.7
✓ eth_keys: 0.4.0
✓ ecdsa: 0.18.0
✓ Internet connectivity OK
```

### Step 2: Setup Mode Selection

Choose what you want to set up:

1. **Full Node** - Complete node with blockchain sync
2. **Light Client** - Lightweight client
3. **Wallet Only** - Just wallet management
4. **Developer Mode** - Full node + dev tools

**Tip**: Select Full Node for first-time users on testnet.

### Step 3: Network Selection

Choose the network:

- **Testnet** (Recommended for beginners)
  - Safe environment for learning
  - Free tokens from faucet
  - No real economic value
  - Can experiment without risk

- **Mainnet** (Production)
  - Real economic value
  - Requires careful security
  - No free tokens
  - Irreversible transactions

**Mainnet Warning**: The wizard requires explicit confirmation for mainnet and displays security warnings.

### Step 4: Node Mode Selection

For Full Node setups, choose storage/sync mode:

- **Full Node** (~50GB): Complete blockchain, recommended
- **Pruned Node** (~10GB): Recent blocks only
- **Light Node** (~1GB): Minimal storage
- **Archival Node** (~500GB): All historical states

The wizard shows disk space requirements and checks available space.

### Step 5: Data Directory

Specify where blockchain data is stored:

**Default**: `~/.xai`

**Custom Example**: `/mnt/blockchain/xai`

The wizard:
- Creates the directory if it doesn't exist
- Checks disk space availability
- Warns if directory already exists
- Uses absolute paths for reliability

### Step 6: Port Configuration

Configure network ports (XAI uses range 12000-12999):

- **RPC Port** (default: 12001): JSON-RPC API endpoint
- **P2P Port** (default: 12002): Peer-to-peer networking
- **WebSocket Port** (default: 12003): Real-time updates

**Port Conflict Detection**: The wizard checks if ports are available and warns about conflicts.

**Example**:
```
? RPC/API port [12001]: 12001
✓ RPC port: 12001

? P2P port [12002]: 12002
✓ P2P port: 12002

? WebSocket port [12003]: 12003
✓ WebSocket port: 12003
```

### Step 7: Mining Configuration

Enable mining to help secure the network and earn rewards:

**Options**:
1. Enable mining with existing wallet address
2. Enable mining and create new wallet
3. Skip mining (can enable later)

**Mining Address Validation**: The wizard validates XAI addresses (XAI1... or 0x... format).

### Step 8: Monitoring Configuration

Optional Prometheus metrics for monitoring:

- Enable/disable metrics collection
- Configure metrics port (default: 12090)
- Metrics available at `http://localhost:12090/metrics`

### Step 9: Security Configuration

The wizard automatically generates cryptographically secure secrets:

- **JWT Secret** (64 hex chars): API authentication
- **Wallet Trade Secret**: Peer-to-peer trades
- **Time Capsule Key**: Time-locked transactions
- **Embedded Salt**: Wallet encryption
- **Lucky Block Seed**: Randomness generation

All secrets use Python's `secrets` module (CSPRNG) with 256-bit entropy.

**Mainnet Security Warnings**:
- Keep .env file secure
- Back up wallet private keys
- Use hardware wallet for large amounts
- Run behind firewall
- Enable firewall rules for P2P/RPC ports

### Step 10: Save Configuration

Creates `.env` file with all configuration:

**Location**: Project root (`/path/to/xai/.env`)

**Features**:
- Backs up existing .env (timestamped)
- Restrictive permissions (0600)
- Comments and documentation
- Never committed to git

**Optional**: On Linux, create systemd service file for auto-start.

### Step 11: Wallet Creation (Optional)

Create a new wallet with:

- **XAI Address**: Unique identifier
- **Private Key**: 256-bit secp256k1 key
- **Mnemonic Phrase**: 12-word BIP-39 backup

**Security Emphasis**:
- Mnemonic phrase displayed once
- User warned to write it down
- Optional secure file storage (0600 permissions)
- Private key never logged

**Example Output**:
```
✓ Wallet created successfully!

IMPORTANT: Save this information securely!

Address: XAI1a3f2c8d9e1b4f7a6c5d8e9f2a1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9

Private Key: 7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9f0a1b2c3d4e5f6g7h8

Mnemonic: abandon ability able about above absent absorb abstract absurd abuse access accident

⚠ Write down your mnemonic phrase and store it safely!
⚠ Anyone with your private key or mnemonic can access your funds!
```

### Step 12: Testnet Tokens (Optional)

For testnet setups with new wallets:

- Faucet URL provided
- Discord community link
- Address displayed for easy copying

**Example**:
```
Testnet Faucet Information:
  Address: XAI1a3f2c8d9e1b4f7...
  Faucet URL: https://faucet.xai.network
  Discord: https://discord.gg/xai-network

Visit the faucet URL or ask in Discord for testnet tokens.
```

### Step 13: Setup Complete

Comprehensive summary and next steps:

**Configuration Summary**:
- Network
- Node mode
- Data directory
- Ports
- Mining status
- Miner address (if applicable)

**Next Steps**:
1. Start your node
2. Check node status
3. View blockchain info
4. Start mining (if enabled)
5. Explore blockchain

**Optional**: Start node immediately after setup.

## Generated Files

### .env File

**Location**: `/path/to/xai/.env`

**Permissions**: `0600` (owner read/write only)

**Contents**:
```bash
# Network Configuration
XAI_NETWORK=testnet
XAI_NODE_MODE=full
XAI_NODE_NAME=xai-node

# Port Configuration
XAI_RPC_PORT=12001
XAI_P2P_PORT=12002
XAI_METRICS_PORT=12090
XAI_RPC_URL=http://localhost:12001

# Data Directory
XAI_DATA_DIR=/home/user/.xai
XAI_LOG_LEVEL=INFO

# Mining Configuration
XAI_MINING_ENABLED=true
MINER_ADDRESS=XAI1a3f2c8d9e1b4f7...
XAI_MINING_THREADS=2

# Security Secrets (auto-generated)
XAI_JWT_SECRET=7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c...
XAI_WALLET_TRADE_PEER_SECRET=3b4a5f6e7d8c9f0a1b2c3d4e5f6g7h8...
XAI_TIME_CAPSULE_MASTER_KEY=f6e7d8c9f0a1b2c3d4e5f6g7h8i9j0k...
XAI_EMBEDDED_SALT=9f0e1d2c3b4a5f6e7d8c9f0a1b2c3d4e...
XAI_LUCKY_BLOCK_SEED=2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r...

# Monitoring
XAI_PROMETHEUS_ENABLED=true

# Database
DATABASE_URL=sqlite:///home/user/.xai/blockchain.db
```

### Wallet File (Optional)

**Location**: `<data_dir>/wallets/wallet_<address>.json`

**Permissions**: `0600` (owner read/write only)

**Contents**:
```json
{
  "address": "XAI1a3f2c8d9e1b4f7...",
  "private_key": "7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c...",
  "mnemonic": "abandon ability able...",
  "created_at": "2025-12-18T17:30:00Z",
  "network": "testnet"
}
```

### Backup Files

If `.env` exists, timestamped backup created:

`.env.backup.20251218_173000`

### Systemd Service (Linux Only)

**Location**: `xai-node-testnet.service` (or mainnet)

**Usage**:
```bash
# Install service
sudo cp xai-node-testnet.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xai-node-testnet
sudo systemctl start xai-node-testnet

# Check status
sudo systemctl status xai-node-testnet

# View logs
sudo journalctl -u xai-node-testnet -f
```

## Using the Node After Setup

### Start the Node

```bash
cd /path/to/xai
python -m xai.core.node

# Or use testnet startup script
./src/xai/START_TESTNET.sh
```

### Check Node Status

```bash
# Health check
curl http://localhost:12001/health

# Blockchain info
curl http://localhost:12001/blocks

# Peer count
curl http://localhost:12001/peers
```

### Start Mining

```bash
curl -X POST http://localhost:12001/mining/start \
  -H 'Content-Type: application/json' \
  -d '{"miner_address":"XAI1...", "threads":2}'

# Stop mining
curl -X POST http://localhost:12001/mining/stop

# Check mining status
curl http://localhost:12001/mining/status
```

### Access Monitoring

- **Block Explorer**: http://localhost:12080
- **Grafana Dashboard**: http://localhost:12030
- **Prometheus Metrics**: http://localhost:12090/metrics

## Security Best Practices

### Mainnet Operations

1. **Secure .env File**:
   - Never commit to git
   - Restrictive permissions (0600)
   - Store backups securely
   - Rotate secrets periodically

2. **Wallet Security**:
   - Write down mnemonic phrase on paper
   - Store in secure location (safe, vault)
   - Never share private keys
   - Consider hardware wallet for large amounts

3. **Network Security**:
   - Run behind firewall
   - Use VPN for remote access
   - Disable unnecessary ports
   - Monitor for suspicious activity

4. **System Security**:
   - Keep OS and dependencies updated
   - Use strong passwords
   - Enable 2FA where possible
   - Regular backups

### Testnet Operations

1. **Testing Environment**:
   - Use testnet for learning
   - Experiment freely
   - No real economic value
   - Request tokens from faucet

2. **Best Practices**:
   - Still secure credentials
   - Practice good habits
   - Test backup/restore
   - Simulate mainnet scenarios

## Troubleshooting

### Python Version Error

```
Error: Python 3.10 or higher required
```

**Solution**:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.10

# macOS
brew install python@3.10

# Windows
Download from https://python.org
```

### Port Already in Use

```
Error: Port 12001 is already in use!
```

**Solutions**:
1. Stop the service using that port
2. Choose a different port in the wizard
3. Check what's using the port: `lsof -i :12001`

### Missing Dependencies

```
Warning: Missing dependencies: flask, requests
```

**Solution**:
```bash
pip install flask requests cryptography eth_keys ecdsa
```

### Permission Denied

```
Error: Permission denied: .env
```

**Solution**:
```bash
# Ensure write permissions
chmod u+w /path/to/xai/.env

# Or run with appropriate user
sudo chown $USER:$USER /path/to/xai
```

### Disk Space Error

```
Error: Only 5 GB available, but 50 GB recommended
```

**Solutions**:
1. Free up disk space
2. Choose different data directory
3. Select Pruned or Light mode (less storage)
4. Continue anyway (not recommended)

### Wallet Creation Failed

**Solutions**:
1. Check file permissions in data directory
2. Ensure sufficient disk space
3. Create wallet manually later
4. Re-run wizard after fixing issues

### Network Connectivity Error

```
Warning: No internet connection detected
```

**Solutions**:
1. Check internet connection
2. Verify firewall settings
3. Continue without network (local only)
4. Configure proxy settings

## Advanced Usage

### Non-Interactive Setup

Use environment variables for automation:

```bash
export XAI_NETWORK=testnet
export XAI_NODE_MODE=full
export XAI_DATA_DIR=/mnt/blockchain/xai
export XAI_RPC_PORT=12001
./scripts/setup_wizard.sh
```

### Multiple Nodes

Set up multiple nodes on same machine:

```bash
# Node 1
XAI_NODE_PORT=12001 XAI_DATA_DIR=~/.xai/node1 ./scripts/setup_wizard.sh

# Node 2
XAI_NODE_PORT=12011 XAI_DATA_DIR=~/.xai/node2 ./scripts/setup_wizard.sh

# Node 3
XAI_NODE_PORT=12021 XAI_DATA_DIR=~/.xai/node3 ./scripts/setup_wizard.sh
```

### Re-running the Wizard

The wizard can be safely re-run:

1. Backs up existing .env file
2. Preserves existing wallets
3. Can update configuration
4. Won't overwrite without confirmation

### Manual Configuration

Instead of wizard, manually create .env:

```bash
# Copy example
cp .env.example .env

# Edit configuration
nano .env

# Set permissions
chmod 600 .env
```

## FAQs

### Q: Can I run the wizard multiple times?

**A**: Yes, it's safe to re-run. Existing configurations are backed up before overwriting.

### Q: Which setup mode should I choose?

**A**: For beginners: Full Node on Testnet. For developers: Developer Mode. For resource-constrained devices: Light Client.

### Q: Do I need to create a wallet during setup?

**A**: No, it's optional. You can create or import wallets later using the CLI.

### Q: Can I change settings after setup?

**A**: Yes, edit the `.env` file directly or re-run the wizard.

### Q: Is it safe to use generated wallets in production?

**A**: The wizard generates secure wallets, but for large amounts on mainnet, consider a hardware wallet.

### Q: What if I lose my mnemonic phrase?

**A**: Your funds are permanently lost. Always back up your mnemonic phrase securely.

### Q: Can I use the same wallet on testnet and mainnet?

**A**: Technically yes, but not recommended. Use separate wallets for testnet and mainnet.

### Q: How do I upgrade my node?

**A**: Pull latest code, re-run wizard to update config, restart node.

### Q: Where are logs stored?

**A**: Check `<data_dir>/logs/` or system journal for systemd services.

### Q: Can I run XAI on Windows?

**A**: Yes, via WSL (Windows Subsystem for Linux) or native Windows with Python 3.10+.

## Additional Resources

- **Main Documentation**: https://docs.xai.network
- **GitHub Repository**: https://github.com/xai-network/xai
- **Discord Community**: https://discord.gg/xai-network
- **Block Explorer**: https://explorer.xai.network
- **Testnet Faucet**: https://faucet.xai.network

## Support

For help with the setup wizard:

1. Check this documentation
2. Review troubleshooting section
3. Search GitHub issues
4. Ask in Discord community
5. Create GitHub issue with detailed description

## Contributing

To improve the wizard:

1. Test on different operating systems
2. Report bugs with detailed logs
3. Suggest features or improvements
4. Submit pull requests
5. Help others in the community

## License

Same as the XAI project.
