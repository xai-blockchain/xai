---
sidebar_position: 2
---

# Quick Start

Get started with XAI in just 5 minutes. This guide will walk you through creating a wallet, getting testnet tokens, and sending your first transaction.

## Step 1: Create Your Wallet

Generate a new wallet address:

```bash
xai-wallet generate-address
```

**Output:**
```
Address: TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Private Key: 5KYZdUEo39z3FPrtuX2QbbwGnNP5zTd7yyr2SC1j299sBCnWjss
```

:::warning
**Never share your private key!** Store it securely in a password manager.
:::

## Step 2: Get Testnet Tokens

Request free testnet XAI from the faucet:

```bash
xai-wallet request-faucet --address TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

**Output:**
```
✅ Testnet faucet claim successful! 100 XAI will be added to your address after the next block.
Note: This is testnet XAI - it has no real value!
```

### Alternative: Web Faucet

You can also use the web interface:

1. Visit https://faucet.xai.network
2. Enter your TXAI address
3. Click "Request Tokens"
4. Wait for the next block (~2 minutes)

## Step 3: Check Your Balance

Wait for the next block (~2 minutes), then check your balance:

```bash
xai-wallet balance --address TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

**Output:**
```
Balance: 100.00000000 XAI
```

## Step 4: Send Your First Transaction

Send XAI to another address:

```bash
xai-wallet send \
  --from TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa \
  --to TXAI_RECIPIENT_ADDRESS \
  --amount 10.0
```

The CLI will:
1. Display the transaction hash
2. Prompt for your private key (never sent to network)
3. Sign and broadcast the transaction

**Output:**
```
Transaction Hash: abc123...
Enter private key: ********
✅ Transaction sent successfully!
TxID: def456...
```

## Step 5: View in Block Explorer

View your transaction in the block explorer:

1. Start the explorer (if not already running):
```bash
python src/xai/explorer.py
```

2. Open http://localhost:12080 in your browser

3. Search for your transaction or address

## Step 6: Start a Node (Optional)

Run your own XAI node:

```bash
# Set testnet environment
export XAI_NETWORK=testnet

# Start the node
xai-node
```

The node will start on:
- **RPC Port**: 12001
- **P2P Port**: 12002
- **WebSocket**: 12003

### Start Mining

To start mining with your wallet:

```bash
export MINER_ADDRESS=TXAI1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
xai-node --miner $MINER_ADDRESS
```

## Common Commands

### Wallet Operations

```bash
# Generate address
xai-wallet generate-address

# Check balance
xai-wallet balance --address TXAI_ADDRESS

# Send transaction
xai-wallet send --from TXAI_FROM --to TXAI_TO --amount 10.0

# Export private key
xai-wallet export-key --address TXAI_ADDRESS

# Request faucet
xai-wallet request-faucet --address TXAI_ADDRESS
```

### Node Operations

```bash
# Start node
xai-node

# Start mining
xai-node --miner TXAI_ADDRESS

# Check node status
curl http://localhost:12001/health

# View peers
curl http://localhost:12001/peers
```

## Troubleshooting

### Faucet Rate Limit

The faucet allows one claim per address per hour. If you see "rate limit exceeded", wait and try again.

### Insufficient Funds

Check your balance with `xai-wallet balance`. Ensure you have enough for both the amount and transaction fee.

### Cannot Connect to Node

Start the node first with `xai-node`, then run your command in a separate terminal.

### Transaction Not Confirming

Wait for the next block (~2 minutes). XAI has a 2-minute block time.

## Next Steps

Now that you're set up, explore advanced features:

- [Developer Guide](../developers/overview) - Build applications on XAI
- [AI Trading](../developers/ai-trading) - Use AI-powered trading strategies
- [Python SDK](../developers/python-sdk) - Integrate XAI into your applications
- [API Reference](../api/rest-api) - Explore the full API

## Getting Help

- **GitHub Issues**: Report bugs and request features
- **Discord**: Join our community for support
- **Documentation**: Browse this documentation site
