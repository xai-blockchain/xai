# XAI CLI Reference

## Overview

Production-grade command-line interface for XAI blockchain with AI compute integration.

## Installation

```bash
# Install with dependencies
pip install -e ".[cli]"

# Or minimal install
pip install click rich requests
```

## Usage

```bash
# Enhanced CLI (default)
xai [command] [options]

# Legacy wallet CLI
xai --legacy [command]
```

---

## Command Structure

### Wallet Commands
- `wallet create` - Generate new wallet
- `wallet balance ADDRESS` - Check balance
- `wallet send` - Send XAI transaction
- `wallet history ADDRESS` - Transaction history
- `wallet portfolio ADDRESS` - Complete wallet overview

### Blockchain Commands
- `blockchain info` - Network statistics
- `blockchain block BLOCK_ID` - Block details
- `blockchain mempool` - Pending transactions

### Mining Commands
- `mining start --address ADDR` - Start mining
- `mining stop` - Stop mining
- `mining status` - Mining status
- `mining stats --address ADDR` - Mining earnings

### Network Commands
- `network info` - Network overview
- `network peers` - Connected peers

### AI Compute Commands (NEW)
- `ai submit` - Submit AI task
- `ai query TASK_ID` - Query task status
- `ai cancel TASK_ID` - Cancel task
- `ai list` - List your tasks
- `ai providers` - Browse AI providers
- `ai provider-details PROVIDER_ID` - Provider info
- `ai earnings --provider-id ID` - Provider earnings
- `ai register-provider` - Register as provider
- `ai marketplace` - Network statistics

---

## AI Compute Examples

### Submit AI Task

```bash
# Code generation task
xai ai submit \
  --task-type code \
  --description "Generate Python REST API with FastAPI" \
  --priority high \
  --max-cost 1.5 \
  --wallet YOUR_ADDRESS

# Security audit
xai ai submit \
  --task-type security \
  --description "Audit smart contract for vulnerabilities" \
  --input-file contract.sol \
  --model gpt-4 \
  --wallet YOUR_ADDRESS
```

### Query Task Status

```bash
# Single query
xai ai query AI-1733123456-abc123

# Watch in real-time
xai ai query AI-1733123456-abc123 --watch
```

### Browse Providers

```bash
# List by reputation
xai ai providers --sort-by reputation --min-reputation 90

# Filter by task type
xai ai providers --task-type security --sort-by cost
```

### Provider Earnings

```bash
# Monthly earnings
xai ai earnings --provider-id AI-NODE-001 --period 30d

# All-time earnings
xai ai earnings --provider-id AI-NODE-001 --period all
```

### Register as Provider

```bash
xai ai register-provider \
  --wallet YOUR_ADDRESS \
  --models "gpt-4,claude-3,gemini-pro" \
  --endpoint https://api.example.com \
  --min-cost 0.05 \
  --capacity 20
```

---

## Wallet Examples

### Create Wallet

```bash
# With encrypted keystore (RECOMMENDED)
xai wallet create --save-keystore

# Specify output path
xai wallet create --save-keystore --keystore-output /secure/path/wallet.keystore

# Use Argon2id KDF (more secure)
xai wallet create --save-keystore --kdf argon2id
```

### Check Balance

```bash
xai wallet balance TXAI1234567890abcdef
```

### Send Transaction

```bash
xai wallet send \
  --sender SENDER_ADDRESS \
  --recipient RECIPIENT_ADDRESS \
  --amount 100.5 \
  --fee 0.001 \
  --keystore /path/to/wallet.keystore
```

### Portfolio View

```bash
xai wallet portfolio TXAI1234567890abcdef
```

### Watch-Only Wallets

Monitor addresses without storing private keys:

```bash
# Add a single address
xai wallet watch add --address XAI_ADDRESS_TO_WATCH --label "treasury"

# Derive multiple addresses from an xpub (receiving chain)
xai wallet watch add --xpub XPUB... --derive-count 10 --label "hardware-wallet"

# List and filter watch entries
xai wallet watch list --tag treasury

# Remove an entry
xai wallet watch remove --address XAI_ADDRESS_TO_WATCH
```

---

## Mining Examples

### Start Mining

```bash
# Basic mining (1 thread)
xai mining start --address YOUR_ADDRESS

# High-performance mining
xai mining start \
  --address YOUR_ADDRESS \
  --threads 8 \
  --intensity 5
```

### Mining Statistics

```bash
# Current status
xai mining status

# Historical stats
xai mining stats --address YOUR_ADDRESS
```

---

## Global Options

```bash
--node-url URL        # Custom node URL (default: http://localhost:18545)
--timeout SECONDS     # Request timeout (default: 30)
--json-output         # Output raw JSON
--transport [http|local]  # Choose HTTP (default) or direct on-disk access
--local-data-dir PATH     # Data directory when using --transport local (default ~/.xai)
--local-mempool-limit N   # Max mempool entries returned in local mode (default 200)
--help                # Show help
```

### Local Transport Mode

Run CLI commands directly against the on-disk blockchain state (no HTTP dependency):

```bash
xai --transport local --local-data-dir ~/.xai blockchain info --json-output
```

Local mode is read-only and supports balance queries, chain info, block inspection, mempool snapshots, and state exports without requiring the REST API to be online.

---

## Task Types

| Type | Description | Avg Cost |
|------|-------------|----------|
| `code` | Code generation/refactoring | 0.05 XAI |
| `security` | Security audits | 0.15 XAI |
| `research` | Research/analysis | 0.10 XAI |
| `analysis` | Data analysis | 0.08 XAI |
| `optimization` | Code optimization | 0.12 XAI |
| `training` | Model training | 0.50 XAI |
| `inference` | Model inference | 0.03 XAI |

---

## Priority Levels

| Priority | Multiplier | When to Use |
|----------|-----------|-------------|
| `low` | 0.8x | Non-urgent tasks |
| `medium` | 1.0x | Standard tasks (default) |
| `high` | 1.5x | Time-sensitive tasks |
| `critical` | 2.5x | Emergency tasks |

---

## Provider Metrics

### Reputation Score
- 90-100: Excellent (green)
- 70-89: Good (yellow)
- <70: Poor (red)

### Sorting Options
- `reputation` - By reputation score
- `cost` - By average cost
- `speed` - By response time
- `availability` - By uptime
- `tasks` - By tasks completed

---

## Output Formats

### Human-Readable (default)
Pretty-formatted tables and panels with Rich styling.

### JSON Output
```bash
xai blockchain info --json-output
```

---

## Configuration

### Environment Variables

```bash
export XAI_NODE_URL=http://localhost:18545
export XAI_TIMEOUT=60
export XAI_LEGACY_CLI=1  # Use legacy CLI
```

### Node URL Priority
1. `--node-url` CLI flag
2. `XAI_NODE_URL` environment variable
3. Default: `http://localhost:18545`

---

## Advanced Usage

### Scripting with JSON Output

```bash
#!/bin/bash
# Check balance and submit task if sufficient

ADDR="TXAI1234567890abcdef"
BALANCE=$(xai wallet balance $ADDR --json-output | jq -r '.balance')

if (( $(echo "$BALANCE > 10" | bc -l) )); then
    xai ai submit \
        --task-type code \
        --description "Generate API" \
        --wallet $ADDR \
        --json-output
fi
```

### Watch Mining Progress

```bash
#!/bin/bash
# Continuously monitor mining

while true; do
    clear
    xai mining status
    sleep 10
done
```

### Provider Monitoring

```bash
#!/bin/bash
# Track daily earnings

xai ai earnings \
    --provider-id AI-NODE-001 \
    --period 24h \
    --json-output | jq '.earnings'
```

---

## Error Handling

### Common Errors

**Connection Error**
```
AI compute network error: Connection refused
```
Solution: Check node URL and ensure node is running.

**Authentication Error**
```
Error obtaining private key: Invalid keystore
```
Solution: Verify keystore path and password.

**Insufficient Balance**
```
Transaction failed: Insufficient funds
```
Solution: Check balance with `xai wallet balance`.

**Task Submission Failed**
```
Submission failed: Max cost too low
```
Solution: Increase `--max-cost` or reduce task complexity.

---

## Security Best Practices

### Private Keys
- ✅ **DO**: Use encrypted keystores (`--save-keystore`)
- ✅ **DO**: Use Argon2id KDF for new wallets
- ❌ **DON'T**: Pass private keys as CLI arguments
- ❌ **DON'T**: Store private keys in environment variables

### AI Tasks
- ✅ **DO**: Set reasonable `--max-cost` limits
- ✅ **DO**: Review provider reputation before use
- ❌ **DON'T**: Submit sensitive data without encryption
- ❌ **DON'T**: Trust low-reputation providers with critical tasks

### Provider Operation
- ✅ **DO**: Maintain 99%+ uptime for reputation
- ✅ **DO**: Set appropriate `--min-cost` to cover expenses
- ❌ **DON'T**: Overcommit capacity (`--capacity`)
- ❌ **DON'T**: Share API endpoints publicly

---

## Performance Tips

1. **Use JSON output for scripting** - Faster parsing
2. **Batch operations** - Submit multiple tasks at once
3. **Filter providers** - Use `--min-reputation` to speed up selection
4. **Local caching** - Store frequently-used addresses
5. **Timeout tuning** - Increase `--timeout` for complex queries

---

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- Community: Discord/Telegram (links in README)

---

## Quick Reference Card

```bash
# Essential Commands

# Wallet
xai wallet create --save-keystore
xai wallet balance ADDRESS
xai wallet send --sender A --recipient B --amount X

# AI Compute
xai ai submit --task-type TYPE --description DESC --wallet ADDR
xai ai query TASK_ID
xai ai providers --sort-by reputation

# Mining
xai mining start --address ADDR
xai mining status

# Blockchain
xai blockchain info
xai network peers
```
