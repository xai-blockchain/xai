# Transaction Guide

A comprehensive guide to sending, receiving, and managing transactions on the XAI blockchain.

## Table of Contents

- [Introduction](#introduction)
- [Transaction Basics](#transaction-basics)
- [Sending Transactions](#sending-transactions)
- [Receiving Transactions](#receiving-transactions)
- [Transaction Fees](#transaction-fees)
- [Advanced Transaction Types](#advanced-transaction-types)
- [Transaction Status and Confirmations](#transaction-status-and-confirmations)
- [Troubleshooting](#troubleshooting)

## Introduction

Transactions are the fundamental way to transfer XAI tokens between addresses. This guide covers everything from basic sends to advanced features like time-locked transactions and atomic swaps.

### What You'll Learn

- How to send and receive XAI
- Understanding transaction fees
- Using advanced transaction features
- Monitoring transaction status
- Resolving transaction issues

### Prerequisites

- Wallet set up and funded (see [Wallet Setup Guide](wallet-setup.md))
- Basic understanding of blockchain concepts
- XAI node running and synchronized

## Transaction Basics

### What is a Transaction?

A transaction transfers XAI tokens from one or more addresses (inputs) to one or more addresses (outputs). Each transaction includes:

- **Inputs**: Source addresses and amounts (must be unspent outputs)
- **Outputs**: Destination addresses and amounts
- **Fee**: Payment to miners for including transaction in a block
- **Signature**: Cryptographic proof of ownership
- **Timestamp**: When transaction was created

### UTXO Model

XAI uses the UTXO (Unspent Transaction Output) model:

- Your balance is the sum of all unspent outputs to your addresses
- Transactions consume entire UTXOs (with change returned)
- UTXOs can only be spent once (prevents double-spending)

**Example:**
```
You have:  UTXO of 100 XAI

You send:  50 XAI to recipient
Result:    - Output 1: 50 XAI to recipient
           - Output 2: 49 XAI back to you (change)
           - Fee: 1 XAI to miner
```

### Transaction Lifecycle

```
1. Create Transaction → Specify recipient(s) and amount(s)
2. Sign Transaction   → Prove ownership with private key
3. Broadcast          → Send to network
4. Mempool           → Waiting in memory pool
5. Mining            → Included in candidate block
6. Confirmation      → Block added to blockchain
7. Finality          → Multiple confirmations received
```

## Sending Transactions

### Basic Transaction (CLI)

```bash
# Send XAI to an address
python src/xai/wallet/cli.py send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10.5 \
  --private-key YOUR_PRIVATE_KEY

# Output:
# Transaction Hash: 0xabc123...
# Status: Broadcast to network
# Track: http://localhost:12001/explorer/transaction/0xabc123...
```

### Send with Custom Fee

```bash
# Specify transaction fee
python src/xai/wallet/cli.py send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10.5 \
  --fee 0.001 \
  --private-key YOUR_PRIVATE_KEY
```

### Send to Multiple Recipients

```bash
# Send to multiple addresses in one transaction
python src/xai/wallet/cli.py send-many \
  --from YOUR_ADDRESS \
  --to RECIPIENT_1:10.5 \
  --to RECIPIENT_2:5.25 \
  --to RECIPIENT_3:3.75 \
  --private-key YOUR_PRIVATE_KEY
```

### Using Desktop Wallet

1. **Open Desktop Wallet**
   ```bash
   cd src/xai/electron
   npm start
   ```

2. **Navigate to Send Tab**
   - Click "Send" in left sidebar
   - Enter recipient address
   - Enter amount to send
   - Review fee (adjust if needed)

3. **Verify Transaction Details**
   - Double-check recipient address
   - Confirm amount is correct
   - Review total (amount + fee)

4. **Send Transaction**
   - Click "Send"
   - Enter wallet password
   - Click "Confirm"
   - Transaction hash displayed

5. **Track Transaction**
   - View in "Transactions" tab
   - Click transaction for details
   - Monitor confirmations

### Transaction Best Practices

1. **Always Verify Addresses**
   ```bash
   # Verify address format before sending
   python src/xai/wallet/cli.py validate-address RECIPIENT_ADDRESS
   ```

2. **Start with Small Test Amount**
   - Send small amount first to new addresses
   - Verify receipt before sending larger amounts
   - Especially important for large transfers

3. **Check Balance Before Sending**
   ```bash
   # Ensure sufficient balance
   python src/xai/wallet/cli.py balance --address YOUR_ADDRESS
   ```

4. **Set Appropriate Fees**
   - Higher fees = faster confirmation
   - Check mempool status for fee estimation
   - Standard fee usually sufficient

5. **Save Transaction Hash**
   - Record transaction hash for tracking
   - Use for customer support if issues arise
   - Proves transaction was sent

## Receiving Transactions

### Generate Receiving Address

```bash
# Get your current address
python src/xai/wallet/cli.py get-address

# Generate new address (HD wallet - recommended for privacy)
python src/xai/wallet/cli.py generate-address --index next

# Display as QR code (desktop wallet)
# Available in GUI wallet interface
```

### Share Your Address

**Safe to share publicly:**
- Your XAI address (starts with XAI or TXAI)
- QR code representing your address

**NEVER share:**
- Private key
- Mnemonic phrase
- Wallet password

### Monitor Incoming Transactions

```bash
# Check balance
python src/xai/wallet/cli.py balance --address YOUR_ADDRESS

# List recent transactions
python src/xai/wallet/cli.py transactions --address YOUR_ADDRESS

# Watch for specific transaction
python src/xai/wallet/cli.py watch-transaction --tx-hash TX_HASH

# Real-time monitoring (optional)
xai wallet watch add --address YOUR_ADDRESS --label "incoming-monitor"
xai wallet watch list --tag incoming-monitor
```

### Verify Receipt

Once notified of incoming transaction:

```bash
# Check transaction status
python src/xai/wallet/cli.py transaction-status --tx-hash TX_HASH

# Verify sender address (optional)
python src/xai/wallet/cli.py transaction-details --tx-hash TX_HASH

# Check confirmations
python src/xai/wallet/cli.py confirmations --tx-hash TX_HASH
```

### Address Reuse Considerations

**Privacy Recommendation:** Use new address for each transaction

**Benefits:**
- Enhanced privacy (harder to track balance)
- Better transaction organization
- Reduced address clustering

**When to reuse:**
- Public donation addresses
- Business/merchant addresses
- Long-term savings address

## Transaction Fees

### How Fees Work

Transaction fees incentivize miners to include your transaction in a block:

- **Paid to:** Miners who mine the block containing your transaction
- **Calculated:** Typically as XAI per byte or fixed amount
- **Priority:** Higher fees = faster confirmation

### Fee Estimation

```bash
# Get recommended fee
python src/xai/wallet/cli.py estimate-fee

# Output:
# Low Priority:    0.0001 XAI (30+ min)
# Medium Priority: 0.0005 XAI (10-20 min)
# High Priority:   0.001 XAI  (2-10 min)

# Check current mempool
python src/xai/wallet/cli.py mempool-status
```

### Setting Custom Fees

```bash
# Low fee (slower confirmation)
python src/xai/wallet/cli.py send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10 \
  --fee 0.0001

# High fee (faster confirmation)
python src/xai/wallet/cli.py send \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 10 \
  --fee 0.01
```

### Fee Considerations

**When to use higher fees:**
- Time-sensitive transactions
- During network congestion
- Large-value transactions requiring fast confirmation

**When lower fees acceptable:**
- Non-urgent transactions
- Low network activity
- Willing to wait for confirmation

**Fee too low?**
- Transaction may take longer to confirm
- Could be stuck in mempool
- See [Stuck Transactions](#stuck-transactions) for solutions

## Advanced Transaction Types

### Time-Locked Transactions

Send XAI that can only be spent after a specific time:

```bash
# Lock until specific timestamp
python src/xai/wallet/cli.py send-timelocked \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 100 \
  --unlock-time 1735689600 \
  --private-key YOUR_PRIVATE_KEY

# Lock for specific duration (time capsule)
python src/xai/wallet/cli.py send-timelocked \
  --from YOUR_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 100 \
  --duration 365d \
  --private-key YOUR_PRIVATE_KEY
```

**Use Cases:**
- Scheduled payments
- Inheritance planning
- Savings lockup
- Vesting schedules
- Time capsules

**Important:** Funds cannot be accessed before unlock time, even by sender!

### Multi-Signature Transactions

Require multiple signatures for transaction authorization:

```bash
# Create multisig transaction (requires setup - see Wallet Setup Guide)
python src/xai/wallet/cli.py send-multisig \
  --multisig-address MULTISIG_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 50.0

# Output: Unsigned transaction hex

# First signer
python src/xai/wallet/cli.py sign-multisig-tx \
  --tx-hex UNSIGNED_TX \
  --private-key SIGNER_1_KEY

# Second signer (if 2-of-3 multisig)
python src/xai/wallet/cli.py sign-multisig-tx \
  --tx-hex PARTIALLY_SIGNED_TX \
  --private-key SIGNER_2_KEY

# Broadcast when enough signatures
python src/xai/wallet/cli.py broadcast-tx --tx-hex FULLY_SIGNED_TX
```

**Use Cases:**
- Shared accounts
- Corporate funds
- Enhanced security
- Escrow services

### Atomic Swaps

Exchange XAI for other cryptocurrencies without intermediaries:

```bash
# Initiate atomic swap with Bitcoin
python src/xai/core/atomic_swap.py initiate \
  --asset BTC \
  --amount 0.5 \
  --recipient BTC_ADDRESS \
  --xai-amount 1000

# Wait for counterparty to lock their funds
# Complete swap with secret
python src/xai/core/atomic_swap.py complete \
  --swap-id SWAP_ID \
  --secret SECRET_HASH
```

**Supported Cryptocurrencies:**
- Bitcoin (BTC)
- Ethereum (ETH)
- Litecoin (LTC)
- And 8+ more

**Benefits:**
- No trusted intermediary
- Cryptographically secure
- Atomic (both happen or neither)
- No exchange fees

For detailed atomic swap guide, see [Atomic Swaps Documentation](../advanced/atomic-swaps.md)

### Smart Contract Transactions

Execute smart contract functions:

```bash
# Call smart contract
python src/xai/wallet/cli.py contract-call \
  --contract-address CONTRACT_ADDRESS \
  --function "transfer" \
  --params "recipient_address,100" \
  --from YOUR_ADDRESS \
  --private-key YOUR_PRIVATE_KEY
```

## Transaction Status and Confirmations

### Check Transaction Status

```bash
# Get transaction details
python src/xai/wallet/cli.py transaction-status --tx-hash TX_HASH

# Output:
# Status: Confirmed
# Confirmations: 6
# Block: 12345
# Block Time: 2025-01-24 10:30:00 UTC
```

### Understanding Confirmations

A confirmation means a block containing your transaction has been added to the blockchain.

| Confirmations | Status | Recommended For |
|---------------|--------|-----------------|
| 0 (Unconfirmed) | In mempool | Not recommended |
| 1 | In blockchain | Small amounts only |
| 3 | Moderate security | Standard transactions |
| 6 | High security | Large amounts |
| 12+ | Very high security | Critical/high-value |

**Why wait for confirmations?**
- Protection against blockchain reorganizations
- Increased security against double-spending
- More confirmations = more confidence

### Transaction States

```
Pending    → Transaction created, not yet broadcast
Broadcast  → Sent to network, waiting for mining
Mempool    → In memory pool, waiting for inclusion in block
Mining     → Being included in candidate block
Confirmed  → Included in blockchain (1+ confirmations)
Finalized  → Sufficient confirmations (6+)
Failed     → Transaction rejected or invalid
```

### Monitor Transaction Progress

```bash
# Watch transaction until confirmed
python src/xai/wallet/cli.py watch-transaction \
  --tx-hash TX_HASH \
  --wait-confirmations 6

# Check in block explorer
# http://localhost:12001/explorer/transaction/TX_HASH

# Real-time updates (desktop wallet)
# Automatically updates in GUI transaction list
```

## Troubleshooting

### Stuck Transactions

**Symptoms:** Transaction remains unconfirmed for extended period

**Causes:**
- Fee too low
- Network congestion
- Node not connected to network

**Solutions:**

1. **Wait it out** (may confirm eventually)
2. **Replace-by-Fee (RBF)** if enabled:
   ```bash
   python src/xai/wallet/cli.py replace-transaction \
     --tx-hash STUCK_TX_HASH \
     --new-fee 0.01
   ```
3. **Create new transaction** with higher fee
4. **Wait for transaction to drop from mempool** (typically 72 hours)

### Insufficient Balance Error

**Symptoms:** "Insufficient balance" when sending

**Solutions:**
```bash
# Check actual balance
python src/xai/wallet/cli.py balance --address YOUR_ADDRESS

# Check for unconfirmed transactions
python src/xai/wallet/cli.py pending-transactions --address YOUR_ADDRESS

# Remember to account for fees
# Required: amount + fee <= balance
```

### Invalid Address Error

**Symptoms:** "Invalid address" when sending

**Solutions:**
```bash
# Validate address format
python src/xai/wallet/cli.py validate-address RECIPIENT_ADDRESS

# Check network matches (mainnet vs testnet)
# Mainnet: XAI prefix
# Testnet: TXAI prefix

# Ensure no extra spaces or characters
```

### Transaction Rejected

**Symptoms:** Transaction rejected by network

**Causes & Solutions:**
- **Invalid signature:** Verify private key is correct
- **Double spend:** Wait for previous transaction to confirm
- **Invalid format:** Check transaction structure
- **Blacklisted address:** Contact support if legitimate

### Transaction Not Showing

**Symptoms:** Sent transaction doesn't appear in wallet

**Solutions:**
```bash
# Force wallet refresh
python src/xai/wallet/cli.py refresh-wallet

# Resync blockchain
python src/xai/wallet/cli.py resync

# Check on block explorer
# http://localhost:12001/explorer/transaction/TX_HASH

# Verify transaction was broadcast
python src/xai/wallet/cli.py transaction-status --tx-hash TX_HASH
```

### Wrong Amount Sent

**Prevention is key - always:**
- Double-check amount before sending
- Verify recipient address
- Review total including fees
- Use test transaction first for new recipients

**If already sent:**
- **Cannot be reversed** - blockchain transactions are permanent
- Contact recipient and request return (if known)
- Learn from mistake and implement prevention measures

## Best Practices Summary

### Before Sending
- [ ] Verify recipient address (double-check!)
- [ ] Confirm amount is correct
- [ ] Check balance covers amount + fee
- [ ] Test with small amount for new recipients
- [ ] Save transaction details

### While Sending
- [ ] Use appropriate fee for urgency
- [ ] Review all transaction details
- [ ] Save transaction hash immediately
- [ ] Screenshot confirmation if important

### After Sending
- [ ] Monitor transaction status
- [ ] Wait for confirmations based on value
- [ ] Verify recipient confirms receipt
- [ ] Keep records for accounting/taxes

### Security
- [ ] Never share private keys
- [ ] Verify addresses on multiple channels if possible
- [ ] Be cautious of phishing attempts
- [ ] Use secure connections only
- [ ] Keep wallet software updated

## Additional Resources

- [Wallet Setup Guide](wallet-setup.md) - Setting up and securing wallets
- [Mining Guide](mining.md) - Understanding transaction mining
- [FAQ](faq.md) - Common questions and answers
- [Block Explorer](http://localhost:12001/explorer) - View transactions

## Getting Help

**Transaction Issues:**
- Check [FAQ](faq.md) for common problems

**Support:**
- Email: info@xai.io
- Include transaction hash in support requests
- Provide detailed description of issue

---

**Last Updated**: January 2025

**Note:** Always test on testnet before executing important mainnet transactions. Blockchain transactions are irreversible!
