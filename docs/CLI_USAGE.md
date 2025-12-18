# XAI CLI Usage Guide

## Installation

After installing the XAI blockchain package, three command-line tools are available:

```bash
pip install -e .
```

## Available Commands

### 1. `xai` - Main CLI (Recommended)

The primary command-line interface with comprehensive blockchain operations.

**Features:**
- AI compute job management
- Blockchain information and operations
- Wallet management
- Mining operations
- Network information
- Beautiful terminal output with Rich library
- Click-based command interface

**Usage:**
```bash
# Get help
xai --help

# Blockchain operations
xai blockchain info
xai blockchain get-block --height 100

# Wallet operations
xai wallet balance --address YOUR_ADDRESS
xai wallet send --from YOUR_ADDRESS --to RECIPIENT --amount 100

# AI operations
xai ai submit-job --model gpt-4 --data "task description"
xai ai list-jobs

# Mining
xai mining status
xai mining start --address MINER_ADDRESS

# Network
xai network peers
xai network status
```

**Global Options:**
```bash
--node-url TEXT          XAI node URL (default: http://localhost:12001)
--timeout FLOAT          Request timeout in seconds (default: 30.0)
--json-output            Output raw JSON
--api-key TEXT           API key for authenticated endpoints
--transport [http|local] Communication transport (default: http)
```

### 2. `xai-wallet` - Legacy Wallet CLI

Wallet-specific command-line interface with argparse-based commands.

**Features:**
- Wallet creation and management
- Transaction operations
- Hardware wallet support
- Multi-signature wallets
- 2FA management
- Watch-only wallets
- QR code backups

**Usage:**
```bash
# Get help
xai-wallet --help

# Generate address
xai-wallet generate-address

# Request faucet funds
xai-wallet request-faucet --address YOUR_ADDRESS

# Check balance
xai-wallet balance --address YOUR_ADDRESS

# Send transaction
xai-wallet send --from YOUR_ADDRESS --to RECIPIENT --amount 100

# Transaction history
xai-wallet history --address YOUR_ADDRESS

# Export/Import
xai-wallet export --address YOUR_ADDRESS --output wallet.json
xai-wallet import --input wallet.json

# Hardware wallet
xai-wallet hw-address --ledger
xai-wallet hw-sign --ledger --message "Hello"
xai-wallet hw-send --ledger --to RECIPIENT --amount 100

# Multi-signature
xai-wallet multisig-create --required 2 --total 3 --pubkeys KEY1,KEY2,KEY3
xai-wallet multisig-sign --wallet WALLET_ID --tx TX_DATA
xai-wallet multisig-submit --wallet WALLET_ID

# Two-Factor Authentication
xai-wallet 2fa-setup --address YOUR_ADDRESS
xai-wallet 2fa-status --address YOUR_ADDRESS
xai-wallet 2fa-disable --address YOUR_ADDRESS

# Watch-only wallets
xai-wallet watch add --address WATCH_ADDRESS --label "Cold Storage"
xai-wallet watch list

# QR backup
xai-wallet mnemonic-qr --mnemonic "word1 word2 ..." --output backup.png
```

### 3. `xai-node` - Node Management

Start and manage XAI blockchain nodes.

**Features:**
- Full node operation
- P2P networking
- Mining support
- Blockchain persistence

**Usage:**
```bash
# Get help
xai-node --help

# Start node with defaults
xai-node

# Start with custom configuration
xai-node --port 12001 --host 0.0.0.0 --p2p-port 12002

# Start mining node
xai-node --miner YOUR_MINER_ADDRESS

# Use custom data directory
xai-node --data-dir ~/.xai/custom

# Connect to peers
xai-node --peers http://peer1:12001 http://peer2:12001
```

**Options:**
```bash
--port PORT              HTTP API port (default: 12001)
--host HOST              Host to bind to (default: localhost)
--p2p-port P2P_PORT      P2P networking port (default: 12002)
--miner MINER            Miner wallet address for block rewards
--data-dir DATA_DIR      Blockchain data directory (default: ~/.xai)
--peers PEERS [PEERS...] Bootstrap peer URLs
```

## Development Mode

For development without installing the package, use Python module syntax:

```bash
# Main CLI
python -m xai.cli.main --help

# Wallet CLI
python -m xai.wallet.cli --help

# Node
python -m xai.core.node --help
```

## Environment Variables

Configure CLI behavior with environment variables:

```bash
# API endpoint
export XAI_API_URL=http://localhost:12001

# Network selection
export XAI_NETWORK=development  # or testnet, mainnet

# Enable legacy CLI mode
export XAI_LEGACY_CLI=1

# Force legacy CLI in xai command
xai --legacy wallet balance --address YOUR_ADDRESS
```

## Shell Completion

Generate shell completion scripts:

```bash
# Bash
xai completion bash > ~/.xai-completion.bash
echo 'source ~/.xai-completion.bash' >> ~/.bashrc

# Zsh
xai completion zsh > ~/.xai-completion.zsh
echo 'source ~/.xai-completion.zsh' >> ~/.zshrc

# Fish
xai completion fish > ~/.config/fish/completions/xai.fish
```

## Common Workflows

### Quick Start

```bash
# 1. Generate wallet
xai-wallet generate-address

# 2. Get test funds
xai-wallet request-faucet --address YOUR_ADDRESS

# 3. Check balance
xai wallet balance --address YOUR_ADDRESS

# 4. Start mining
xai-node --miner YOUR_ADDRESS
```

### Transaction Workflow

```bash
# Check balance
xai wallet balance --address YOUR_ADDRESS

# Send transaction
xai wallet send --from YOUR_ADDRESS --to RECIPIENT --amount 100

# Check transaction status
xai blockchain get-transaction --hash TX_HASH
```

### AI Compute Jobs

```bash
# Submit job
xai ai submit-job --model gpt-4 --data "Analyze blockchain state"

# List jobs
xai ai list-jobs

# Get job status
xai ai get-job --id JOB_ID

# Get job result
xai ai get-result --id JOB_ID
```

## Troubleshooting

### Entry Points Not Found

If commands aren't available after installation:

```bash
# Reinstall in editable mode
pip install -e .

# Verify entry points
pip show xai-blockchain | grep Location
ls -l $(pip show xai-blockchain | grep Location | cut -d' ' -f2)/../../../bin/xai*
```

### Missing Dependencies

Enhanced CLI requires `click` and `rich`:

```bash
pip install click rich
```

Legacy wallet CLI requires core dependencies:

```bash
pip install flask flask-cors cryptography pyyaml secp256k1
```

### Import Errors

Ensure package is installed:

```bash
pip install -e .
```

Or use development mode:

```bash
export PYTHONPATH=/path/to/xai/src:$PYTHONPATH
python -m xai.cli.main --help
```

## Entry Point Configuration

Entry points are defined in `pyproject.toml`:

```toml
[project.scripts]
xai = "xai.cli.main:main"
xai-wallet = "xai.wallet.cli:main"
xai-node = "xai.core.node:main"
```

These create executable scripts in your Python environment's `bin/` directory
after `pip install`.
