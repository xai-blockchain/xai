# Wallet CLI Security Guide

## Overview

The XAI wallet CLI has been hardened to prevent private key exposure through multiple attack vectors. This document describes the security measures implemented and best practices for users.

## Security Vulnerabilities Addressed

### 1. Command-Line Argument Exposure

**Problem:** Private keys passed as CLI arguments are exposed in:
- Shell history (~/.bash_history, ~/.zsh_history)
- Process listings (`ps aux`, `/proc/[pid]/cmdline`)
- Terminal scrollback buffers
- System logs and audit trails

**Solution:** The `--private-key` argument has been **completely removed** from all commands. Private keys are now obtained through secure methods only.

### 2. Standard Output Exposure

**Problem:** Private keys printed to stdout/stderr can be:
- Recorded in terminal scrollback
- Captured by screen recording software
- Visible to anyone watching the screen
- Logged by terminal multiplexers (tmux, screen)

**Solution:** Private keys are **never** printed by default. When display is necessary, it requires:
- Explicit `--show-private-key` flag
- Interactive confirmation with exact phrase
- Prominent security warnings

### 3. Environment Variable Leakage

**Problem:** Environment variables can be:
- Visible in process listings
- Logged by system monitoring tools
- Exposed through crash dumps
- Leaked through child processes

**Solution:** Environment variable usage requires:
- Explicit `--allow-env-key` flag (disabled by default)
- Prominent security warnings when used
- Recommendation to use keystore instead

## Secure Private Key Methods

### Method 1: Encrypted Keystore (RECOMMENDED)

Encrypted keystore files provide the highest security:

```bash
# Generate new wallet with encrypted keystore
xai-wallet generate-address --save-keystore

# Use keystore for transactions
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10 \
  --keystore ~/.xai/keystores/XAI123....keystore
```

**Security features:**
- AES-256-GCM encryption
- PBKDF2 (600,000 iterations) or Argon2id key derivation
- HMAC-SHA256 integrity verification
- Strong password policy enforcement
- Restrictive file permissions (0600)
- Address stored in plaintext for easy identification

**Password requirements:**
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### Method 2: Interactive Secure Input (DEFAULT)

If no keystore is specified, the CLI prompts for private key using `getpass`:

```bash
# Send transaction with interactive input
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10

# Prompts: "Enter sender's private key (input hidden):"
# Input is not echoed, not recorded in history
```

**Security features:**
- Input is not echoed to terminal
- Not recorded in shell history
- Not visible in process listings
- Validates hex format and length

### Method 3: Environment Variable (NOT RECOMMENDED)

Only use for automated scripts where keystore is not practical:

```bash
export XAI_PRIVATE_KEY="your_private_key_here"

xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10 \
  --allow-env-key
```

**Security warnings:**
- Requires explicit `--allow-env-key` flag
- Displays prominent security warnings
- Environment variables may be logged
- Visible in process listings
- Can leak through crash dumps

## Command Reference

### Generate New Wallet

```bash
# RECOMMENDED: Generate with encrypted keystore
xai-wallet generate-address --save-keystore

# Advanced: Specify output path and KDF
xai-wallet generate-address \
  --save-keystore \
  --keystore-output /secure/path/wallet.keystore \
  --kdf argon2id

# NOT RECOMMENDED: Show private key on screen (requires confirmation)
xai-wallet generate-address --show-private-key
```

**Default behavior:** Shows address and public key only. Private key is NOT displayed.

### Send Transaction

```bash
# RECOMMENDED: Use encrypted keystore
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10 \
  --keystore ~/.xai/keystores/wallet.keystore

# Alternative: Interactive input (secure)
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10
# Prompts for private key securely

# NOT RECOMMENDED: Environment variable
export XAI_PRIVATE_KEY="..."
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10 \
  --allow-env-key
```

### Export Wallet

```bash
# RECOMMENDED: Export with encryption (default)
xai-wallet export \
  --address XAI123... \
  --keystore ~/.xai/keystores/source.keystore \
  --output backup.enc

# NOT RECOMMENDED: Unencrypted export (requires confirmation)
xai-wallet export \
  --address XAI123... \
  --no-encrypt \
  --output backup.json
# Requires typing "EXPORT UNENCRYPTED" to confirm
```

**Default behavior:** Encryption is enabled by default. Unencrypted export requires explicit `--no-encrypt` flag and confirmation.

### Import Wallet

```bash
# Import encrypted wallet
xai-wallet import --file wallet.enc

# Import and hide private key from display
xai-wallet import --file wallet.enc --no-private-key
```

## Migration Guide

### From Insecure CLI Usage

**OLD (INSECURE):**
```bash
# NEVER DO THIS - Exposes private key in shell history
xai-wallet send --sender XAI123... --recipient XAI456... --amount 10 --private-key 0xabc...
```

**NEW (SECURE):**
```bash
# Step 1: Create encrypted keystore from existing private key
xai-wallet export \
  --address XAI123... \
  --output ~/.xai/keystores/wallet.keystore
# Prompts for private key securely, then encrypts it

# Step 2: Use keystore for all operations
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10 \
  --keystore ~/.xai/keystores/wallet.keystore
```

### Cleaning Shell History

If you previously used insecure commands, clean your shell history:

```bash
# For bash
sed -i '/--private-key/d' ~/.bash_history
history -c
history -w

# For zsh
sed -i '/--private-key/d' ~/.zsh_history
fc -W
```

## Security Best Practices

### DO

- ✅ Use encrypted keystore files for all private key storage
- ✅ Use strong, unique passwords for keystores (12+ chars, mixed case, digits, symbols)
- ✅ Store keystore files on encrypted filesystems
- ✅ Back up keystore files to secure, encrypted locations
- ✅ Use hardware wallets when available (via hardware wallet integration)
- ✅ Verify keystore file permissions are 0600 (owner read/write only)
- ✅ Clear terminal after displaying sensitive information

### DO NOT

- ❌ Pass private keys as command-line arguments
- ❌ Store private keys in environment variables
- ❌ Print private keys to stdout/logs
- ❌ Commit keystore files to version control
- ❌ Share keystore passwords via insecure channels
- ❌ Use weak passwords (less than 12 chars, no complexity)
- ❌ Store unencrypted private keys on disk
- ❌ Display private keys on shared screens

## Keystore File Format

Encrypted keystore files use the following format:

```json
{
  "version": "2.0",
  "algorithm": "AES-256-GCM",
  "kdf": "pbkdf2",
  "iterations": 600000,
  "encrypted_data": "<base64-encoded-ciphertext>",
  "salt": "<base64-encoded-salt>",
  "nonce": "<base64-encoded-nonce>",
  "hmac": "<base64-encoded-hmac>",
  "address": "XAI123..."
}
```

**Security features:**
- **AES-256-GCM:** Authenticated encryption with associated data
- **PBKDF2/Argon2id:** Slow key derivation prevents brute-force attacks
- **HMAC-SHA256:** Integrity verification prevents tampering
- **Random salt/nonce:** Prevents rainbow table attacks

## Testing

Comprehensive security tests are located in:
```
tests/xai_tests/unit/test_wallet_cli_security.py
```

Run security tests:
```bash
pytest tests/xai_tests/unit/test_wallet_cli_security.py -v
```

## Audit Trail

All security-sensitive operations are logged (without exposing private keys):
- Wallet creation events
- Keystore file creation
- Authentication attempts
- Transaction signing

Check logs at: `~/.xai/logs/wallet.log`

## Incident Response

If you suspect private key exposure:

1. **Immediately transfer funds** to a new wallet
2. **Generate a new wallet** with encrypted keystore
3. **Abandon the compromised wallet**
4. **Review logs** for unauthorized access
5. **Clean shell history** as shown above
6. **Rotate all derived keys** (if using HD wallets)

## Contact

For security issues, contact: security@xai-blockchain.io

**Do NOT** post private keys or keystore passwords in issues or support channels.
