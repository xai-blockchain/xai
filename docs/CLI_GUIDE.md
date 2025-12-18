# XAI Blockchain CLI Guide

## Revolutionary AI-Enhanced Command Line Interface

The XAI CLI provides a production-grade, beautiful command-line interface for interacting with the XAI blockchain network. Built with modern Python tools (Click and Rich), it offers an intuitive, colorful terminal experience for blockchain operations, AI compute jobs, mining, and more.

## Installation

```bash
# Install XAI blockchain with CLI dependencies
pip install -e .

# Or install CLI dependencies separately
pip install click rich
```

## Quick Start

```bash
# Show help
xai --help

# Check blockchain info
xai blockchain info

# Create a new wallet
xai wallet create --save-keystore

# Check balance
xai wallet balance TXAI_YOUR_ADDRESS

# Start mining
xai mining start --address TXAI_YOUR_ADDRESS --threads 4
```

## Command Structure

The CLI is organized into logical command groups:

```
xai
├── wallet      # Wallet management
├── blockchain  # Blockchain information
├── mining      # Mining operations
├── network     # Network information
└── ai          # AI compute operations (REVOLUTIONARY)
```

## Global Options

All commands support these global options:

```bash
--node-url TEXT      XAI node URL (default: http://localhost:12001)
--timeout FLOAT      Request timeout in seconds (default: 30.0)
--json-output        Output raw JSON for scripting
--transport [http|local]  Select HTTP (default) or direct on-disk access
--local-data-dir PATH     Override blockchain data dir for local transport
--local-mempool-limit N   Cap mempool entries returned when offline (default 200)
```

### Offline / Local Transport

Use `--transport local` to query blockchain data directly from disk—ideal when the REST API is unreachable or during forensic reviews. Provide the node's data directory (defaults to `~/.xai`):

```bash
xai --transport local --local-data-dir ~/.xai --json-output blockchain block 1000
```

Local transport currently offers read-only capabilities (balances, blocks, mempool, state snapshots). Mutating operations such as mining control or transaction submission still require HTTP transport.

## Wallet Commands

### Create Wallet

Create a new XAI wallet with secure key management:

```bash
# Basic wallet creation (shows address and public key only)
xai wallet create

# Create with encrypted keystore (RECOMMENDED)
xai wallet create --save-keystore

# Specify keystore location
xai wallet create --save-keystore --keystore-output ~/.xai/my-wallet.keystore

# Use Argon2id for key derivation (more secure, slower)
xai wallet create --save-keystore --kdf argon2id
```

**Security Features:**
- Private key never displayed by default
- Encrypted keystores with AES-256-GCM
- Strong password requirements
- PBKDF2 or Argon2id key derivation
- Secure file permissions (0600)

### Check Balance

View wallet balance and pending transactions:

```bash
xai wallet balance TXAI_YOUR_ADDRESS
```

**Output includes:**
- Current balance
- Pending incoming transactions
- Pending outgoing transactions

### Transaction History

View wallet transaction history:

```bash
# Last 10 transactions (default)
xai wallet history TXAI_YOUR_ADDRESS

# Last 50 transactions
xai wallet history TXAI_YOUR_ADDRESS --limit 50

# Pagination
xai wallet history TXAI_YOUR_ADDRESS --limit 20 --offset 20
```

**Beautiful table output with:**
- Transaction timestamp
- Type (Sent/Received)
- Amount
- Counterparty address
- Transaction ID

### Watch-Only Wallets

Track balances without exposing private keys. Watch entries are stored securely under `~/.xai/watch_only.json`.

```bash
# Add a single address
xai wallet watch add --address XAI123... --label "treasury"

# Derive ten receiving addresses from an xpub
xai wallet watch add --xpub XPUB123... --derive-count 10 --label "ledger"

# List entries (JSON for scripting)
xai wallet watch list --json

# Remove an entry when no longer needed
xai wallet watch remove --address XAI123...
```

Use `--tags` to categorize entries and `--tag` filters when listing. The `watch-address` command remains as a backwards-compatible alias for `watch add`.

### Send Transaction

Send XAI to another address:

```bash
# With encrypted keystore (RECOMMENDED)
xai wallet send \
  --sender TXAI_YOUR_ADDRESS \
  --recipient TXAI_RECIPIENT_ADDRESS \
  --amount 10.5 \
  --fee 0.001 \
  --keystore ~/.xai/keystores/wallet.keystore

# With interactive private key input (secure)
xai wallet send \
  --sender TXAI_YOUR_ADDRESS \
  --recipient TXAI_RECIPIENT_ADDRESS \
  --amount 10.5
```

**Security Features:**
- Private key obtained securely (never via CLI argument)
- Transaction confirmation prompt with summary
- Real-time transaction status
- Secure memory cleanup

### Portfolio View

Comprehensive wallet portfolio overview:

```bash
xai wallet portfolio TXAI_YOUR_ADDRESS
```

**Displays:**
- Current balance
- Total received
- Total sent
- Transaction count
- Average transaction size

## Blockchain Commands

### Blockchain Info

Get current blockchain state:

```bash
xai blockchain info
```

**Information includes:**
- Chain height (current block number)
- Latest block hash
- Current difficulty
- Pending transactions count
- Network hashrate
- Total supply

### Get Block

Retrieve block details by index or hash:

```bash
# By block index
xai blockchain block 12345

# By block hash
xai blockchain block 0x1234567890abcdef...
```

**Block details include:**
- Block index
- Block hash
- Previous block hash
- Timestamp
- Difficulty
- Nonce
- Miner address
- List of transactions

### View Mempool

See pending transactions waiting to be mined:

```bash
xai blockchain mempool
```

**Displays:**
- Transaction ID
- Sender address
- Recipient address
- Amount
- Fee
- Total transactions pending

## Mining Commands

### Start Mining

Begin mining blocks to earn rewards:

```bash
# Basic mining (1 thread, low intensity)
xai mining start --address TXAI_YOUR_ADDRESS

# High-performance mining
xai mining start \
  --address TXAI_YOUR_ADDRESS \
  --threads 8 \
  --intensity 5

# Maximum intensity
xai mining start \
  --address TXAI_YOUR_ADDRESS \
  --threads 16 \
  --intensity 10
```

**Parameters:**
- `--address`: Your wallet address (receives mining rewards)
- `--threads`: Number of mining threads (default: 1)
- `--intensity`: Mining intensity 1-10 (default: 1)

### Stop Mining

Stop mining operations:

```bash
xai mining stop
```

### Mining Status

Check current mining status:

```bash
xai mining status
```

**Status includes:**
- Mining active/inactive
- Miner address
- Thread count
- Current hashrate
- Blocks mined
- Total rewards earned

### Detailed Mining Stats

View comprehensive mining statistics:

```bash
xai mining stats --address TXAI_YOUR_ADDRESS
```

**Statistics include:**
- Total blocks mined
- Total rewards earned
- Current balance
- Average reward per block
- Mining efficiency

## Network Commands

### Network Information

View network status and configuration:

```bash
xai network info
```

**Information includes:**
- Network name (mainnet/testnet)
- Node version
- Node ID
- Connected peers count
- Network hashrate
- Sync status

### Connected Peers

List all connected peer nodes:

```bash
xai network peers
```

**Peer information:**
- Node ID
- IP address and port
- Software version
- Connection duration

## AI Commands (REVOLUTIONARY)

The AI command group provides revolutionary AI-blockchain integration features.

### Submit AI Task

Submit an AI compute job to the network:

```bash
xai ai submit \
  --task-type code \
  --description "Optimize blockchain consensus algorithm" \
  --priority high \
  --max-cost 5.0
```

**Task types:**
- `code` - Code generation and refactoring
- `security` - Security audits and analysis
- `research` - Research and data analysis
- `analysis` - Code and system analysis
- `optimization` - Performance optimization

**Priority levels:**
- `low` - Best effort, lowest cost
- `medium` - Standard priority (default)
- `high` - High priority, faster completion
- `critical` - Urgent, premium providers

**Features:**
- Automatic AI provider matching
- Cost optimization
- Task confirmation prompt
- Unique task ID for tracking

### Query Task Status

Check the status of submitted AI tasks:

```bash
xai ai query AI-1733123456-1234
```

**Status information:**
- Task ID
- Current status (pending/running/completed/failed)
- Result or error message
- Cost incurred
- Provider used

### List AI Providers

View available AI compute providers:

```bash
# Default sorting (by reputation)
xai ai providers

# Sort by cost (cheapest first)
xai ai providers --sort-by cost

# Sort by speed
xai ai providers --sort-by speed

# Sort by availability
xai ai providers --sort-by availability
```

**Provider information:**
- Provider ID
- Reputation score (0-100%)
- Tasks completed
- Average cost
- Average response time
- Availability percentage
- Supported AI models

### Provider Earnings

Calculate earnings for AI compute providers:

```bash
# Last 24 hours
xai ai earnings --provider-id AI-NODE-001 --period 24h

# Last 7 days
xai ai earnings --provider-id AI-NODE-001 --period 7d

# Last 30 days
xai ai earnings --provider-id AI-NODE-001 --period 30d

# All time
xai ai earnings --provider-id AI-NODE-001 --period all
```

**Earnings report:**
- Total earnings in XAI
- Tasks completed
- Average earnings per task
- Model usage distribution
- Efficiency metrics

### AI Task History

View completed AI task history:

```bash
# Last 10 tasks (default)
xai ai history

# Last 50 tasks
xai ai history --limit 50
```

**History includes:**
- Task ID
- Task type
- Status
- Cost
- Completion timestamp
- Provider used

## JSON Output Mode

All commands support `--json-output` for scripting:

```bash
# Get balance as JSON
xai --json-output wallet balance TXAI_YOUR_ADDRESS

# Get blockchain info as JSON
xai --json-output blockchain info

# Query AI task as JSON
xai --json-output ai query AI-1733123456-1234
```

**Use cases:**
- Shell scripts
- CI/CD pipelines
- Automated monitoring
- Data extraction
- Integration with other tools

## Configuration

### Environment Variables

```bash
# Set default node URL
export XAI_NODE_URL="http://mainnet.xai.network:18545"

# Set request timeout
export XAI_TIMEOUT=60

# Use legacy CLI interface
export XAI_LEGACY_CLI=1
```

### Configuration File

Create `~/.xai/config.yaml`:

```yaml
node:
  url: "http://localhost:12001"
  timeout: 30

wallet:
  keystore_dir: "~/.xai/keystores"
  default_kdf: "argon2id"

mining:
  default_threads: 4
  default_intensity: 3
```

## Advanced Usage Examples

### Automated Mining Script

```bash
#!/bin/bash
# Start mining with monitoring

WALLET="TXAI_YOUR_ADDRESS"

# Start mining
xai mining start --address $WALLET --threads 8 --intensity 5

# Monitor earnings every hour
while true; do
    echo "=== Mining Status ==="
    xai mining status
    echo ""
    echo "=== Current Balance ==="
    xai wallet balance $WALLET
    echo ""
    sleep 3600
done
```

### AI Task Automation

```bash
#!/bin/bash
# Submit AI task and wait for completion

TASK_ID=$(xai --json-output ai submit \
    --task-type security \
    --description "Audit smart contract" \
    --priority high | jq -r '.task_id')

echo "Task submitted: $TASK_ID"

# Poll for completion
while true; do
    STATUS=$(xai --json-output ai query $TASK_ID | jq -r '.status')
    if [ "$STATUS" = "completed" ]; then
        echo "Task completed!"
        xai ai query $TASK_ID
        break
    fi
    echo "Status: $STATUS - waiting..."
    sleep 30
done
```

### Portfolio Monitoring

```bash
#!/bin/bash
# Monitor multiple wallets

WALLETS=(
    "TXAI_WALLET_1"
    "TXAI_WALLET_2"
    "TXAI_WALLET_3"
)

for wallet in "${WALLETS[@]}"; do
    echo "=== Portfolio: $wallet ==="
    xai wallet portfolio $wallet
    echo ""
done
```

## Troubleshooting

### Connection Issues

```bash
# Test node connectivity
curl http://localhost:12001/info

# Specify different node
xai --node-url http://mainnet.xai.network:18545 blockchain info

# Increase timeout for slow connections
xai --timeout 60 blockchain info
```

### Keystore Issues

```bash
# Check keystore permissions
ls -la ~/.xai/keystores/

# Fix permissions if needed
chmod 600 ~/.xai/keystores/*.keystore
chmod 700 ~/.xai/keystores
```

### Missing Dependencies

```bash
# Install all dependencies
pip install -e ".[dev]"

# Or just CLI dependencies
pip install click rich
```

## Security Best Practices

1. **Always use encrypted keystores**
   - Never store private keys in plaintext
   - Use strong, unique passwords
   - Enable 2FA where available

2. **Verify transaction details**
   - Always check the confirmation prompt
   - Verify recipient address carefully
   - Start with small test transactions

3. **Secure your environment**
   - Don't run commands over untrusted networks
   - Clear terminal history after using private keys
   - Use secure channels for remote node connections

4. **Keep software updated**
   ```bash
   pip install --upgrade xai-blockchain
   ```

5. **Backup keystores securely**
   - Store encrypted backups offline
   - Use hardware wallets for large amounts
   - Test backup restoration procedure

## Legacy CLI

To use the original wallet CLI:

```bash
# Use legacy flag
xai --legacy wallet generate-address

# Or set environment variable
export XAI_LEGACY_CLI=1
xai wallet generate-address

# Direct legacy command
xai-wallet generate-address
```

## API Integration

The CLI can be used programmatically:

```python
from xai.cli.enhanced_cli import XAIClient

# Create client
client = XAIClient(node_url="http://localhost:12001")

# Get balance
balance = client.get_balance("TXAI_YOUR_ADDRESS")
print(f"Balance: {balance['balance']} XAI")

# Get blockchain info
info = client.get_blockchain_info()
print(f"Height: {info['height']}")

# Submit transaction
result = client.submit_transaction(
    sender="TXAI_SENDER",
    recipient="TXAI_RECIPIENT",
    amount=10.0,
    private_key="your_private_key",
    fee=0.001
)
```

## Contributing

To contribute to CLI development:

1. **Add new commands**: Edit `src/xai/cli/enhanced_cli.py`
2. **Follow conventions**: Use Click decorators and Rich output
3. **Add tests**: Include unit and integration tests
4. **Update docs**: Keep this guide current
5. **Submit PR**: Follow project contribution guidelines

## Support

- **Documentation**: https://xai-blockchain.readthedocs.io
- **Issues**: Report bugs via GitHub Issues
- **Community**: Join Discord/Telegram channels
- **Email**: support@xai-blockchain.org

## What Makes This CLI Revolutionary

### 1. Beautiful Terminal UX
- Rich colored output with tables and panels
- Progress indicators and spinners
- Syntax highlighting for code
- Tree views for hierarchical data
- Live updating displays

### 2. AI-Blockchain Integration
- Submit AI compute jobs directly
- Query task status in real-time
- Browse and rank AI providers
- Track provider earnings
- View AI task history

### 3. Production-Grade Features
- Secure private key handling
- Encrypted keystore management
- Transaction confirmations
- Comprehensive error handling
- JSON output for automation
- Configuration file support

### 4. Developer-Friendly
- Intuitive command structure
- Extensive help text
- Examples for all commands
- Scriptable with JSON output
- Python API integration

### 5. Complete Blockchain Operations
- Wallet management
- Transaction sending
- Mining control
- Network monitoring
- Block exploration
- Mempool inspection

## See Also

- [Wallet Setup Guide](user-guides/wallet-setup.md) - Getting started with XAI wallets
- [Wallet Advanced Features](user-guides/wallet_advanced_features.md) - Multisig, hardware wallets, typed signing
- [Transaction Guide](user-guides/transactions.md) - Creating and submitting transactions
- [Hardware Wallet Usage](user-guides/hardware_wallet_usage.md) - Ledger and Trezor integration

This CLI sets a new standard for blockchain command-line interfaces, combining professional-grade security with beautiful, intuitive user experience and revolutionary AI-blockchain features.
