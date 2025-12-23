# Security Upgrade - Wallet CLI Private Key Protection

## Overview

The XAI wallet CLI has undergone a comprehensive security upgrade to eliminate private key exposure vulnerabilities. **All users should migrate to the new secure methods immediately.**

## Critical Security Fixes

### Vulnerabilities Eliminated

1. **Command-Line Argument Exposure**
   - Private keys in shell history (bash_history, zsh_history)
   - Visible in `ps aux` and `/proc/[pid]/cmdline`
   - Recorded in system audit logs

2. **Standard Output Exposure**
   - Private keys printed to terminal
   - Captured by terminal scrollback buffers
   - Visible in screen recordings

3. **Environment Variable Leakage**
   - Exposure in process listings
   - Leaked through crash dumps
   - Visible to all child processes

### Changes Summary

| Old Behavior | New Behavior |
|--------------|--------------|
| `--private-key` CLI argument | **REMOVED** - No longer accepted |
| Private key printed by default | **NEVER** printed without confirmation |
| No encryption for exports | Encryption **enabled by default** |
| No keystore support | **Encrypted keystore** recommended method |
| Plain environment variables | Requires `--allow-env-key` + warnings |

## Migration Required

### 🚨 URGENT: If You Used Insecure Commands

If you previously used commands like this:
```bash
xai-wallet send --private-key 0xabc... ...  # ❌ INSECURE!
```

**Your private keys may be exposed in shell history!**

### Immediate Actions Required

1. **Clean your shell history:**
   ```bash
   ./scripts/security/clean_private_key_history.sh
   ```

2. **Transfer funds to new wallets:**
   ```bash
   # Generate new secure wallet
   xai-wallet generate-address --save-keystore

   # Transfer all funds from old wallet to new wallet
   xai-wallet send \
     --sender OLD_ADDRESS \
     --recipient NEW_ADDRESS \
     --amount ALL_BALANCE \
     --keystore ~/.xai/keystores/OLD_WALLET.keystore
   ```

3. **Abandon old wallets** - Consider them compromised

## New Secure Usage

### Generate Wallet (Recommended Method)

```bash
# Create wallet with encrypted keystore
xai-wallet generate-address --save-keystore

# Advanced: Specify custom location and stronger KDF
xai-wallet generate-address \
  --save-keystore \
  --keystore-output /secure/path/wallet.keystore \
  --kdf argon2id
```

**Output:**
```
Create keystore password:
Requirements: 12+ characters, uppercase, lowercase, digit, special char
Password: ****************
Confirm password: ****************

Wallet generated successfully!
Address: XAI1234567890abcdef
Public Key: 04abcdef...

Encrypted keystore saved to: /home/user/.xai/keystores/XAI1234567890.keystore
Keep your password secure - it cannot be recovered!
```

### Send Transaction (Recommended Method)

```bash
# Using encrypted keystore (most secure)
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10.5 \
  --keystore ~/.xai/keystores/wallet.keystore
```

**Prompts:**
```
Enter keystore password: ****************
Transaction sent successfully!
TX ID: abc123...
```

### Alternative: Interactive Input

If no keystore specified, secure interactive input:

```bash
xai-wallet send \
  --sender XAI123... \
  --recipient XAI456... \
  --amount 10.5
```

**Prompts:**
```
Enter sender's private key (input hidden):
****************
Transaction sent successfully!
```

### Export Wallet

```bash
# Encrypted export (default, recommended)
xai-wallet export \
  --address XAI123... \
  --keystore ~/.xai/keystores/source.keystore \
  --output backup.enc
```

## Security Features

### Encrypted Keystore

- **Algorithm:** AES-256-GCM (authenticated encryption)
- **Key Derivation:** PBKDF2 (600,000 iterations) or Argon2id
- **Integrity:** HMAC-SHA256 verification
- **Permissions:** Automatically set to 0600 (owner only)

### Password Policy

Enforced for all keystore operations:
- ✅ Minimum 12 characters
- ✅ At least one uppercase letter
- ✅ At least one lowercase letter
- ✅ At least one digit
- ✅ At least one special character

### Memory Protection

- Private keys cleared from memory after use (best effort in Python)
- Sensitive data not logged
- getpass used for all password/key input (no echo)

## Breaking Changes

### Removed Arguments

These arguments have been **completely removed**:

- ❌ `--private-key` (all commands)
- ❌ `--privkey` (if existed)

### Changed Defaults

- `generate-address`: Now shows **only** address and public key by default
- `export`: Encryption is **enabled by default** (use `--no-encrypt` to disable)
- `--json`: Now **deprecated** and requires confirmation

### New Required Arguments

None! All commands work securely with defaults or interactive prompts.

### New Optional Arguments

- ✅ `--keystore PATH` - Use encrypted keystore (recommended)
- ✅ `--save-keystore` - Save to encrypted keystore on generation
- ✅ `--allow-env-key` - Allow environment variable (not recommended)
- ✅ `--show-private-key` - Display private key (requires confirmation)

## Command Reference

### Generate Address

```bash
# Default: Show address/public key only (secure)
xai-wallet generate-address

# Recommended: Save to encrypted keystore
xai-wallet generate-address --save-keystore

# Not recommended: Show private key (requires confirmation)
xai-wallet generate-address --show-private-key

# Deprecated: JSON output (requires confirmation)
xai-wallet generate-address --json
```

### Send Transaction

```bash
# Recommended: Use keystore
xai-wallet send \
  --sender ADDR \
  --recipient ADDR \
  --amount 10 \
  --keystore PATH

# Alternative: Interactive input
xai-wallet send --sender ADDR --recipient ADDR --amount 10

# Not recommended: Environment variable
export XAI_PRIVATE_KEY="..."
xai-wallet send --sender ADDR --recipient ADDR --amount 10 --allow-env-key
```

### Export Wallet

```bash
# Recommended: Encrypted export
xai-wallet export --address ADDR --keystore SOURCE

# Not recommended: Unencrypted (requires confirmation)
xai-wallet export --address ADDR --no-encrypt
```

### Import Wallet

```bash
# Import encrypted wallet
xai-wallet import --file wallet.enc

# Import without showing private key
xai-wallet import --file wallet.enc --no-private-key
```

## Testing

Run comprehensive security tests:

```bash
pytest tests/xai_tests/unit/test_wallet_cli_security.py -v
```

**Tests cover:**
- ✅ No private key arguments accepted
- ✅ No private key in default output
- ✅ Keystore encryption/decryption
- ✅ Password policy enforcement
- ✅ File permission verification
- ✅ Confirmation requirements
- ✅ Memory cleanup attempts

## Documentation

Full security documentation:
- `docs/security/wallet_cli_security.md` - Complete security guide
- `SECURITY_UPGRADE.md` - This file (migration guide)
- `scripts/security/clean_private_key_history.sh` - History cleanup tool

## Support

### Need Help?

- **Migration issues:** Check `docs/security/wallet_cli_security.md`
- **Shell history cleanup:** Run `./scripts/security/clean_private_key_history.sh`
- **Lost wallet:** If you used secure methods, recover from keystore backup

### Security Issues

Report security vulnerabilities to: security@xai-blockchain.io

**DO NOT** post private keys or passwords in public issues.

## Verification

To verify the security upgrade is active:

```bash
# This should FAIL (no --private-key argument)
xai-wallet send --sender X --recipient Y --amount 1 --private-key abc
# Error: unrecognized arguments: --private-key

# This should prompt securely
xai-wallet send --sender X --recipient Y --amount 1
# Prompts: "Enter sender's private key (input hidden):"
```

## Rollback (Not Recommended)

**There is no rollback.** The insecure `--private-key` argument has been permanently removed for your security.

If you absolutely need the old behavior for automated scripts:
1. Use `--allow-env-key` with environment variables (shows security warnings)
2. Better: Migrate scripts to use keystore files

## Timeline

- **Before:** Private keys accepted via CLI arguments (INSECURE)
- **Now:** Private keys ONLY via keystore/interactive/env (SECURE)
- **Future:** Hardware wallet integration (MOST SECURE)

## Acknowledgments

Security improvements address vulnerabilities identified in blockchain security audits and industry best practices.

Standards referenced:
- OWASP Secure Coding Practices
- NIST Special Publication 800-63B (Digital Identity Guidelines)
- CWE-214: Information Exposure Through Process Environment
- CWE-532: Insertion of Sensitive Information into Log File
