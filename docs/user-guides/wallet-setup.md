# Wallet Setup Guide

This comprehensive guide covers everything you need to know about setting up and managing XAI wallets.

## Table of Contents

- [Introduction](#introduction)
- [Wallet Types](#wallet-types)
- [Creating Your First Wallet](#creating-your-first-wallet)
- [Backing Up Your Wallet](#backing-up-your-wallet)
- [Restoring a Wallet](#restoring-a-wallet)
- [Multi-Signature Wallets](#multi-signature-wallets)
- [HD Wallet Features](#hd-wallet-features)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

A wallet is essential for interacting with the XAI blockchain. It securely stores your private keys, generates addresses, and signs transactions. XAI supports multiple wallet types to meet different security and usability needs.

### What You'll Learn

- How to create and manage wallets
- Wallet backup and recovery procedures
- Advanced features like multi-signature and HD wallets
- Security best practices for protecting your funds

### Prerequisites

- XAI blockchain client installed
- Basic understanding of cryptocurrency concepts
- Secure device for storing backup information

## Wallet Types

XAI supports multiple wallet implementations:

### 1. CLI Wallet (Command Line)

**Best for:** Advanced users, automation, server environments

**Features:**
- Full control over wallet operations
- Scriptable for automation
- Minimal resource usage
- Direct access to all features

**Installation:**
```bash
# Already included with XAI installation
python src/xai/wallet/cli.py --help
```

### 2. Desktop Wallet (Electron)

**Best for:** General users, daily transactions, visual interface

**Features:**
- User-friendly graphical interface
- Transaction history visualization
- Address book for contacts
- QR code generation

**Installation:**
```bash
# Navigate to electron wallet directory
cd src/xai/electron

# Install dependencies
npm install

# Start wallet
npm start
```

### 3. Web Wallet (Block Explorer)

**Best for:** Quick access, read-only operations, checking balances

**Features:**
- No installation required
- Check balances and transactions
- Request testnet faucet funds
- View blockchain data

**Access:** Visit the block explorer at `http://localhost:18546/explorer`

### 4. Multi-Signature Wallet

**Best for:** Shared funds, enhanced security, organizations

**Features:**
- Requires multiple signatures for transactions
- Customizable signature thresholds (e.g., 2-of-3, 3-of-5)
- Enhanced security for large holdings
- Organizational fund management

### 5. Hardware Wallet

**Best for:** Maximum security, large holdings, cold storage

**Features:**
- Private keys never leave the device
- Secure element chip protection
- Physical confirmation required for transactions
- Support for Ledger and Trezor devices

**Setup:** See [Wallet Advanced Features - Hardware Wallets](wallet_advanced_features.md#hardware-wallets)

## Creating Your First Wallet

### Using CLI Wallet

#### Generate a New Wallet

```bash
# Generate new wallet with random mnemonic
python src/xai/wallet/cli.py generate-address

# Output:
# Address: XAI1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0
# Mnemonic: abandon ability able about above absent absorb abstract absurd abuse access accident
# Private Key: [ENCRYPTED]
```

**Important:** The mnemonic phrase is displayed only once. Write it down and store it securely!

#### Create Wallet with Custom Parameters

```bash
# Specify wallet name
python src/xai/wallet/cli.py generate-address --name "my-savings-wallet"

# Generate testnet address
export XAI_NETWORK=testnet
python src/xai/wallet/cli.py generate-address
```

### Using Desktop Wallet

1. **Launch Desktop Wallet**
   ```bash
   cd src/xai/electron
   npm start
   ```

2. **Welcome Screen**
   - Click "Create New Wallet"
   - Choose a strong password (minimum 12 characters)
   - Confirm password

3. **Backup Mnemonic**
   - Write down your 12-word mnemonic phrase
   - Verify the mnemonic by entering words in correct order
   - Confirm you've backed up the mnemonic

4. **Wallet Created**
   - Your wallet address is displayed
   - You can now receive and send XAI

### Wallet Address Format

XAI addresses follow specific formats depending on network:

- **Mainnet**: Starts with `XAI` (e.g., `XAI1a2b3c4d5e6f7...`)
- **Testnet**: Starts with `TXAI` (e.g., `TXAI1a2b3c4d5e6f7...`)

## Backing Up Your Wallet

**Critical:** Always back up your wallet before sending funds to it!

### Backup Methods

#### 1. Mnemonic Phrase (Recommended)

The mnemonic phrase is the master key to your wallet. With it, you can recover all addresses and funds.

**Best Practices:**
- Write on paper (never store digitally)
- Use multiple copies in separate secure locations
- Consider using a fireproof/waterproof safe
- Never share with anyone
- Never take photos or screenshots

**To Display Mnemonic:**
```bash
# CLI Wallet
python src/xai/wallet/cli.py show-mnemonic --address YOUR_ADDRESS

# You'll be prompted for password
```

#### 2. Private Key Export

Export private keys for individual addresses:

```bash
# Export private key
python src/xai/wallet/cli.py export-key --address YOUR_ADDRESS

# Export to encrypted file
python src/xai/wallet/cli.py export-key --address YOUR_ADDRESS --output key.enc
```

**Security Warning:** Private keys grant full access to funds. Protect them like cash!

#### 3. Wallet File Backup

Back up the entire wallet file:

```bash
# Locate wallet file
# Default location: ~/.xai/wallets/

# Create backup
cp ~/.xai/wallets/default.wallet ~/backups/xai-wallet-backup-$(date +%Y%m%d).wallet

# Encrypt backup (recommended)
gpg -c ~/backups/xai-wallet-backup-$(date +%Y%m%d).wallet
```

#### 4. Hardware Backup

For additional security:
- Store encrypted USB drives in multiple locations
- Use hardware security modules (HSM) for large holdings
- Consider multisig with geographically distributed keys

### Backup Verification

Always verify your backup works:

```bash
# Test restore on testnet first
export XAI_NETWORK=testnet

# Restore from mnemonic
python src/xai/wallet/cli.py restore --mnemonic "your twelve word phrase here..."

# Check balance matches original
python src/xai/wallet/cli.py balance --address RESTORED_ADDRESS
```

## Restoring a Wallet

### From Mnemonic Phrase

```bash
# Interactive restore
python src/xai/wallet/cli.py restore

# You'll be prompted to enter:
# 1. Mnemonic phrase (12 or 24 words)
# 2. Optional passphrase
# 3. New wallet password

# Direct restore with parameters
python src/xai/wallet/cli.py restore \
  --mnemonic "word1 word2 word3 ... word12" \
  --name "restored-wallet"
```

### From Private Key

```bash
# Import single private key
python src/xai/wallet/cli.py import-key \
  --private-key YOUR_PRIVATE_KEY \
  --name "imported-wallet"

# Import from encrypted file
python src/xai/wallet/cli.py import-key \
  --file key.enc \
  --name "imported-wallet"
```

### From Wallet File

```bash
# Copy wallet file to wallets directory
cp ~/backups/xai-wallet-backup.wallet ~/.xai/wallets/restored.wallet

# Verify wallet loaded
python src/xai/wallet/cli.py list-wallets

# Check balance
python src/xai/wallet/cli.py balance
```

### Recovery Troubleshooting

**Issue: "Invalid mnemonic phrase"**
- Verify word order is correct
- Check for typos (use BIP-39 word list)
- Ensure using correct language (English)

**Issue: "Restored wallet shows zero balance"**
- Confirm you're on correct network (mainnet vs testnet)
- Wait for blockchain synchronization to complete
- Verify derivation path is correct

**Issue: "Cannot decrypt wallet file"**
- Ensure using correct password
- Check file isn't corrupted
- Try alternative backup if available

## Multi-Signature Wallets

Multi-signature (multisig) wallets require multiple signatures to authorize transactions, providing enhanced security.

### Creating a Multisig Wallet

```bash
# Create 2-of-3 multisig wallet
python src/xai/wallet/cli.py create-multisig \
  --required 2 \
  --total 3 \
  --pubkey1 PUBLIC_KEY_1 \
  --pubkey2 PUBLIC_KEY_2 \
  --pubkey3 PUBLIC_KEY_3

# Output:
# Multisig Address: XAI_multisig_address_here
# Configuration: 2-of-3 signatures required
```

### Common Multisig Configurations

| Configuration | Description | Use Case |
|---------------|-------------|----------|
| 1-of-2 | Any one of two can sign | Backup key scenario |
| 2-of-2 | Both must sign | Two-party agreement |
| 2-of-3 | Two of three must sign | Standard security (recommended) |
| 3-of-5 | Three of five must sign | Organization/board |
| 5-of-7 | Five of seven must sign | Large organization |

### Signing Multisig Transactions

```bash
# Step 1: Create transaction (any keyholder)
python src/xai/wallet/cli.py create-multisig-tx \
  --multisig-address MULTISIG_ADDRESS \
  --to RECIPIENT_ADDRESS \
  --amount 100

# Output: Unsigned transaction hex

# Step 2: First signature
python src/xai/wallet/cli.py sign-multisig-tx \
  --tx-hex UNSIGNED_TX_HEX \
  --private-key PRIVATE_KEY_1

# Output: Partially signed transaction hex

# Step 3: Second signature (if 2-of-3)
python src/xai/wallet/cli.py sign-multisig-tx \
  --tx-hex PARTIALLY_SIGNED_TX_HEX \
  --private-key PRIVATE_KEY_2

# Output: Fully signed transaction hex

# Step 4: Broadcast transaction
python src/xai/wallet/cli.py broadcast-tx \
  --tx-hex FULLY_SIGNED_TX_HEX
```

### Multisig Best Practices

1. **Key Distribution**
   - Store keys in geographically separate locations
   - Use different devices for each key
   - Consider using hardware wallets for each key

2. **Threshold Selection**
   - Balance security vs usability
   - 2-of-3 recommended for most users
   - Higher thresholds for organizations

3. **Communication**
   - Establish clear signing procedures
   - Use secure communication channels
   - Document who holds which keys

## HD Wallet Features

XAI wallets are Hierarchical Deterministic (HD) wallets following BIP-32/BIP-39 standards.

### Benefits of HD Wallets

- **Single Backup**: One mnemonic backs up unlimited addresses
- **Organized**: Hierarchical address structure
- **Privacy**: Generate new address for each transaction
- **Compatibility**: Standard derivation paths work across wallets

### Derivation Paths

XAI uses the following derivation paths:

```
Mainnet: m/44'/5841'/0'/0/n
Testnet: m/44'/1'/0'/0/n
```

Where `n` is the address index (0, 1, 2, ...)

### Generating Multiple Addresses

```bash
# Generate next address in sequence
python src/xai/wallet/cli.py generate-address --index 1

# Generate specific address index
python src/xai/wallet/cli.py generate-address --index 42

# List all addresses from HD wallet
python src/xai/wallet/cli.py list-addresses
```

### Privacy Through Address Rotation

**Recommended Practice:** Use a new address for each incoming transaction

```bash
# Get new receiving address
NEW_ADDR=$(python src/xai/wallet/cli.py generate-address --index next)
echo "Send funds to: $NEW_ADDR"
```

## Security Best Practices

### Wallet Security Checklist

- [ ] **Strong Password**: Use 16+ character password with mixed case, numbers, symbols
- [ ] **Mnemonic Backup**: Written down and stored in secure location(s)
- [ ] **Encrypted Storage**: Wallet files encrypted on disk
- [ ] **Separate Devices**: Don't store wallet and backup on same device
- [ ] **Regular Backups**: Backup wallet after significant changes
- [ ] **Test Restores**: Verify backups work before trusting them
- [ ] **Secure Environment**: Use updated OS with antivirus protection
- [ ] **Network Security**: Avoid public Wi-Fi when accessing wallets
- [ ] **Two-Factor Authentication**: Enable if available
- [ ] **Cold Storage**: Keep majority of funds in offline wallets

### Hot vs Cold Wallets

**Hot Wallet** (Online)
- Connected to internet
- Used for daily transactions
- Keep only amounts you need
- Higher convenience, lower security

**Cold Wallet** (Offline)
- Never connected to internet
- Long-term storage
- Maximum security
- Lower convenience, higher security

**Recommended Split:**
- Hot Wallet: 10-20% of holdings for daily use
- Cold Wallet: 80-90% in offline storage

### Password Management

```bash
# Change wallet password
python src/xai/wallet/cli.py change-password --address YOUR_ADDRESS

# Requirements:
# - Minimum 12 characters
# - Mixed case letters
# - Numbers and symbols
# - Not found in common password lists
```

### Protecting Against Phishing

- Only use official XAI software from verified sources
- Verify URLs before entering credentials
- Never enter mnemonic on websites
- Be suspicious of unexpected messages
- Verify transaction details before signing

### Regular Security Audits

```bash
# Check wallet integrity
python src/xai/wallet/cli.py verify-wallet --address YOUR_ADDRESS

# Review transaction history for unauthorized transactions
python src/xai/wallet/cli.py transactions --address YOUR_ADDRESS
```

## Troubleshooting

### Common Issues

#### Wallet Won't Open

**Symptoms:** Error when trying to access wallet

**Solutions:**
1. Verify wallet file exists and isn't corrupted
2. Check file permissions
3. Ensure using correct password
4. Try restoring from backup

#### Can't See Balance

**Symptoms:** Wallet shows zero balance but should have funds

**Solutions:**
1. Wait for blockchain sync to complete
2. Verify on correct network (mainnet/testnet)
3. Check address format matches network
4. Verify address on block explorer

#### Transaction Not Sending

**Symptoms:** Transaction fails or gets stuck

**Solutions:**
1. Check sufficient balance (including fees)
2. Verify network connectivity
3. Ensure node is synchronized
4. Try increasing transaction fee
5. Check if address format is valid

#### Lost Password

**Symptoms:** Cannot decrypt wallet file

**Solutions:**
- Restore from mnemonic phrase (if available)
- Try all possible password variations
- Use backup wallet file
- **No password recovery possible without mnemonic!**

#### Corrupted Wallet File

**Symptoms:** Error loading wallet file

**Solutions:**
1. Restore from backup wallet file
2. Restore from mnemonic phrase
3. Import private keys individually
4. Contact support if issues persist

### Getting Help

**Documentation:**
- [Getting Started Guide](getting-started.md)
- [Transaction Guide](transactions.md)
- [FAQ](faq.md)

**Community:**

**Support:**
- Email: info@xai.io
- Review [SECURITY.md](../../SECURITY.md) for security issues

## Advanced Topics

### Custom Derivation Paths

```bash
# Use custom derivation path
python src/xai/wallet/cli.py generate-address \
  --derivation-path "m/44'/5841'/0'/0/100"
```

### Watch-Only Wallets

Monitor addresses without private keys:

```bash
# Add watch-only address
xai wallet watch add --address XAI_ADDRESS_TO_WATCH --label "watched-wallet"

# Derive addresses from hardware wallet xpub (receiving chain)
xai wallet watch add --xpub XPUB... --derive-count 5 --label "ledger"

# List and monitor
xai wallet watch list --tag watched-wallet
```

### Paper Wallets

Generate offline for cold storage:

```bash
# Generate paper wallet (offline recommended)
python src/xai/wallet/cli.py generate-paper-wallet

# Print and store securely
# Never expose private key to online systems
```

### Integration with Hardware Wallets

XAI supports hardware wallet integration:
- Ledger Nano S/X (via `ledgerblue` library)
- Trezor Model T (via `trezor` library)

See [Wallet Advanced Features - Hardware Wallets](wallet_advanced_features.md#hardware-wallets) for detailed setup instructions.

## Next Steps

Now that you have your wallet set up:

1. **Get Some XAI**: Use the [faucet](faucet.md) (testnet) or purchase XAI
2. **Send a Transaction**: Follow the [Transaction Guide](transactions.md)
3. **Explore Features**: Try time-locked transactions, atomic swaps
4. **Advanced Features**: See [Wallet Advanced Features](wallet_advanced_features.md) for:
   - Address checksums (XIP-55)
   - Multisig wallets
   - Hardware wallet integration
   - Unsigned transactions (XUTX)
   - Typed data signing (XIP-712)
   - Watch-only wallets
   - Two-factor authentication
5. **Secure Your Funds**: Review security best practices regularly

---

**Last Updated**: January 2025

