# Wallet Security Best Practices

This guide covers essential security practices for protecting your XAI wallet and private keys. Whether you're managing personal funds or enterprise assets, following these guidelines will significantly reduce the risk of theft or loss.

## Table of Contents

- [Key Management Fundamentals](#key-management-fundamentals)
- [Wallet Setup Security](#wallet-setup-security)
- [Backup and Recovery](#backup-and-recovery)
- [Two-Factor Authentication (2FA)](#two-factor-authentication-2fa)
- [Hardware Wallet Integration](#hardware-wallet-integration)
- [Operational Security](#operational-security)
- [Threat Models](#threat-models)
- [Emergency Response](#emergency-response)

## Key Management Fundamentals

### Understanding Private Keys

Your private key is the cryptographic proof of ownership for your XAI address. Anyone with access to your private key can:
- Sign transactions to spend your funds
- Export your key to other wallets
- Transfer all assets to different addresses

**Golden Rule:** Never share your private key or mnemonic phrase with anyone. XAI support will never ask for these.

### Encryption at Rest

XAI wallets use industry-standard encryption:

- **Keystores**: AES-256-CTR encryption with scrypt key derivation
- **Password Requirements**: Minimum 12 characters, enforced complexity
- **Memory Protection**: Keys zeroed after use, secure deletion

Example keystore structure:
```json
{
  "version": 3,
  "id": "uuid",
  "address": "xai1...",
  "crypto": {
    "cipher": "aes-256-ctr",
    "cipherparams": {"iv": "..."},
    "ciphertext": "...",
    "kdf": "scrypt",
    "kdfparams": {
      "dklen": 32,
      "n": 262144,
      "r": 8,
      "p": 1,
      "salt": "..."
    },
    "mac": "..."
  }
}
```

### Key Derivation (HD Wallets)

XAI uses BIP-32/BIP-39 hierarchical deterministic (HD) wallets:

- **Mnemonic**: 12 or 24 word phrase generates master seed
- **Derivation Path**: `m/44'/5841'/0'/0/n` (mainnet)
- **Unlimited Addresses**: Generate new addresses without new backups

Benefits:
- Single backup protects infinite addresses
- Organized account structure
- Cross-wallet compatibility

## Wallet Setup Security

### Creating a Secure Wallet

1. **Environment Setup**
   ```bash
   # Verify you're on the official XAI software
   shasum -a 256 xai-wallet
   # Compare with official checksums

   # Use offline or trusted device
   # Disconnect from internet for maximum security (optional)
   ```

2. **Generate Wallet**
   ```bash
   # CLI wallet
   python src/xai/wallet/cli.py generate-address --name "cold-storage"

   # Desktop wallet
   cd src/xai/electron && npm start
   # Follow on-screen setup wizard
   ```

3. **Password Selection**
   - **Minimum**: 12 characters
   - **Recommended**: 16+ characters with mixed case, numbers, symbols
   - **Use a password manager** (KeePassXC, 1Password, Bitwarden)
   - **Never reuse** passwords from other services

   Example strong password: `T7$mK9@nP2&qR5#vX8!wL3`

### Initial Security Checklist

Before funding your wallet:

- [ ] Password meets complexity requirements
- [ ] Mnemonic phrase written down (not stored digitally)
- [ ] Backup stored in secure location(s)
- [ ] Test restore from backup on testnet
- [ ] 2FA configured (see [2FA section](#two-factor-authentication-2fa))
- [ ] Wallet software verified (checksums match)
- [ ] Operating system updated and secured

## Backup and Recovery

### Mnemonic Phrase Backup

Your 12-word mnemonic phrase is the master key to your wallet.

**DO:**
- ✅ Write on paper using pen (not pencil - can fade)
- ✅ Use steel/titanium backup for fire/water protection
- ✅ Store in multiple secure locations (safe deposit box, home safe)
- ✅ Use tamper-evident bags to detect physical access
- ✅ Consider splitting mnemonic across locations (Shamir's Secret Sharing)

**DON'T:**
- ❌ Take photos or screenshots
- ❌ Store in cloud services (Google Drive, Dropbox, iCloud)
- ❌ Email to yourself
- ❌ Store on computer (even encrypted)
- ❌ Share with anyone (including family, unless inheritance planning)

### QR Code Backups

XAI supports encrypted QR code backups (see `docs/user-guides/mnemonic_qr_backup.md`):

```bash
# Generate encrypted QR backup
xai-wallet backup-qr --output backup.png --password <strong-password>

# Print QR and store physically
# The QR contains encrypted mnemonic - requires password to decrypt
```

Benefits:
- Fast restoration via camera scan
- Password-protected encryption
- Easy to duplicate and distribute

### Testing Your Backup

**Critical**: Always verify backups work before funding wallet.

```bash
# Set to testnet
export XAI_NETWORK=testnet

# Restore from mnemonic
python src/xai/wallet/cli.py restore \
  --mnemonic "your twelve word phrase here..." \
  --name "restore-test"

# Verify address matches original
python src/xai/wallet/cli.py list-wallets

# Request testnet faucet funds (see docs/user-guides/TESTNET_FAUCET.md)
# Send test transaction to verify full functionality
```

### Keystore File Backups

Encrypted wallet files provide additional recovery option:

```bash
# Locate wallet file
ls ~/.xai/wallets/

# Create encrypted backup
gpg --symmetric --cipher-algo AES256 ~/.xai/wallets/default.wallet

# Store encrypted file on separate media (USB drive)
# Keep backup password in password manager
```

## Two-Factor Authentication (2FA)

XAI supports TOTP-based 2FA for sensitive wallet operations (send, export).

### Setting Up 2FA

```bash
# Configure 2FA profile
xai-wallet 2fa-setup \
  --label my-wallet \
  --user-email you@example.com \
  --qr-output wallet-2fa.png

# Output:
# - QR code (scan with authenticator app)
# - Backup codes (single-use recovery codes)
# - TOTP secret (for manual entry)
```

### Authenticator Apps

Recommended TOTP apps:
- **Aegis** (Android) - Open source, encrypted backups
- **Raivo OTP** (iOS) - Open source, iCloud sync
- **1Password** - Integrated with password manager
- **Authy** - Multi-device sync with master password

### Using 2FA for Transactions

Once configured, sending transactions requires TOTP:

```bash
# Send transaction
xai-wallet send \
  --from 0xYourAddress \
  --to 0xRecipient \
  --amount 100 \
  --keystore ~/.xai/keystores/wallet.json \
  --2fa-profile my-wallet

# Prompts:
# 1. Wallet password
# 2. 6-digit TOTP code (or backup code)
```

### 2FA Backup Codes

During setup, you receive 10 single-use backup codes:

```
Backup Codes (save offline):
1. ABCD-EFGH
2. IJKL-MNOP
3. QRST-UVWX
...
```

**Important:**
- Each code can only be used once
- Codes are consumed on use (remaining count shown in `2fa-status`)
- Store codes separately from wallet (different location than mnemonic)
- If codes are exhausted, disable and reconfigure 2FA

### Checking 2FA Status

```bash
# View 2FA profile status
xai-wallet 2fa-status --label my-wallet

# Output:
# - Profile creation date
# - Remaining backup codes
# - Issuer label
```

## Hardware Wallet Integration

Hardware wallets provide maximum security by keeping private keys in a secure element chip.

### Supported Devices

XAI supports:
- **Ledger Nano S / Nano X** (via `ledgerblue` library)
- **Trezor Model T** (via `trezor` library)

### Setup Process

1. **Install Firmware** (if new device)
   - Follow manufacturer's setup wizard
   - Generate device seed on hardware wallet
   - Write down 24-word recovery phrase

2. **Install XAI App** (Ledger only)
   ```bash
   # Using Ledger Live
   # Navigate to Manager → Search "XAI" → Install
   ```

3. **Connect to XAI Wallet**
   ```bash
   # Connect hardware wallet via USB
   xai-wallet connect-ledger

   # Or for Trezor
   xai-wallet connect-trezor
   ```

4. **Derive XAI Addresses**
   ```bash
   # Get first address
   xai-wallet hw-address --index 0

   # Get next 5 addresses
   xai-wallet hw-addresses --count 5
   ```

### Signing Transactions

Hardware wallets require physical confirmation:

```bash
# Initiate transaction
xai-wallet send \
  --from <hw-address> \
  --to 0xRecipient \
  --amount 100 \
  --hardware ledger

# Steps:
# 1. Review transaction on device screen
# 2. Verify recipient address matches
# 3. Verify amount is correct
# 4. Press both buttons to confirm (Ledger)
```

### Hardware Wallet Best Practices

- ✅ Purchase directly from manufacturer (avoid third-party sellers)
- ✅ Verify tamper-evident packaging on arrival
- ✅ Generate seed on device (never use pre-generated seeds)
- ✅ Store recovery phrase using same security as mnemonic backup
- ✅ Set device PIN (required for Ledger/Trezor)
- ✅ Enable passphrase (25th word) for advanced users
- ✅ Test recovery process before funding
- ❌ Never enter seed on computer or website
- ❌ Never take photos of device screen

## Operational Security

### Transaction Signing

Always verify transaction details before signing:

```bash
# Transaction preview
xai-wallet send \
  --from 0xYourAddress \
  --to 0xRecipient \
  --amount 100 \
  --preview

# Output shows:
# - From address
# - To address (verify carefully!)
# - Amount
# - Fee
# - Total deducted from balance
# - Resulting balance

# Confirm? (yes/no): yes
```

### Phishing Protection

Common phishing tactics:
- Fake wallet websites with similar domains
- Browser extensions that inject malicious code
- Email/Discord scams asking for private keys
- Fake "support" requesting remote access

**Defense:**
1. **Bookmark official sites** - Always use bookmarks, not search results
2. **Verify URLs** - Check exact spelling (xai.io not xai-wallet.io)
3. **Check SSL certificates** - Look for padlock icon
4. **Use hardware wallet** - Prevents keylogging/malware
5. **Never enter mnemonic online** - Legitimate sites never ask for this

### Address Verification

XAI uses address checksums (XIP-55) to prevent typos:

```bash
# Validate checksum
xai-wallet validate-address XAI1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0

# Output:
# ✓ Valid checksum
# ✓ Mainnet address
# Network: mainnet
# Type: standard
```

Always:
- Compare first 6 and last 4 characters when sending large amounts
- Use address book for frequent recipients
- Send small test transaction first for new addresses
- Use QR codes to avoid manual entry errors

### Cold Storage Strategy

For long-term holdings (>6 months):

1. **Generate Offline**
   - Use air-gapped computer (never connected to internet)
   - Run XAI wallet from USB drive
   - Generate wallet and record address

2. **Store Keys Securely**
   - Mnemonic phrase in safe deposit box
   - Steel backup at home safe
   - Optionally use Shamir's Secret Sharing (split into 3 parts, 2 required)

3. **Fund Wallet**
   - Send test transaction from hot wallet
   - Verify receipt on block explorer
   - Send remaining funds

4. **Periodic Verification**
   - Check balance on block explorer quarterly
   - Never expose private key unless spending

## Threat Models

### Malware/Keyloggers

**Risk**: Software records keystrokes, stealing passwords and private keys.

**Mitigation**:
- Use hardware wallet for signing
- Run wallet on clean OS (live USB with Tails/Qubes)
- Use on-screen keyboard for password entry
- Keep antivirus updated
- Avoid downloading unverified software

### Physical Theft

**Risk**: Attacker steals device with wallet or backup materials.

**Mitigation**:
- Encrypt all wallet files (default in XAI)
- Use strong unique passwords
- Enable 2FA
- Store backups in multiple locations
- Use tamper-evident seals on backup storage
- For hardware wallets: PIN protection (wipes after failed attempts)

### Social Engineering

**Risk**: Attacker tricks you into revealing credentials.

**Mitigation**:
- Never share private keys, mnemonic, or passwords
- XAI support never asks for sensitive information
- Be skeptical of urgent requests
- Verify identity through official channels
- Use hardware wallet (can't be socially engineered)

### Supply Chain Attacks

**Risk**: Compromised hardware wallet or wallet software.

**Mitigation**:
- Buy hardware wallets directly from manufacturer
- Verify packaging integrity
- Check software checksums before installing
- Use open-source wallets (XAI is open source)
- Generate seeds on device, never pre-configured

### $5 Wrench Attack

**Risk**: Physical coercion to reveal keys.

**Mitigation**:
- Use plausible deniability (hidden wallets with different passphrases)
- Store majority of funds in multisig requiring geographically distributed signers
- Consider social solutions (don't advertise crypto holdings)
- Use "duress PIN" on hardware wallets (wipes device)

## Emergency Response

### Lost/Stolen Device

**Immediate Actions**:
1. Do NOT panic - wallet is encrypted
2. Assess risk (does attacker have password?)
3. If high risk: Restore wallet on new device and transfer funds immediately
4. If low risk: Monitor address on block explorer for unauthorized activity
5. Disable 2FA profile if enabled (`xai-wallet 2fa-disable`)

**Recovery Steps**:
```bash
# Restore from mnemonic on new device
python src/xai/wallet/cli.py restore \
  --mnemonic "your twelve words..."

# Generate new address for receiving
xai-wallet generate-address --index next

# Transfer funds to new address
xai-wallet send --from <old> --to <new> --amount <all>
```

### Forgotten Password

**If mnemonic available**: Restore wallet with new password
```bash
xai-wallet restore --mnemonic "..." --name "recovered"
# Set new password during restore
```

**If no mnemonic**: Funds are unrecoverable. This is by design for security.

### Compromised Mnemonic

**If you suspect mnemonic phrase is compromised**:

1. **Create new wallet immediately**
   ```bash
   xai-wallet generate-address --name "emergency-wallet"
   ```

2. **Transfer all assets**
   ```bash
   # Transfer XAI
   xai-wallet send --from <old> --to <new> --amount <all>

   # Transfer tokens (if any)
   xai-wallet token-transfer --token <address> --to <new> --amount <all>
   ```

3. **Abandon old wallet** - Never use compromised wallet again

### Lost Mnemonic (But Have Access to Wallet)

**If wallet is still accessible**:

1. **Export private keys immediately**
   ```bash
   xai-wallet export-key --address <addr> --output backup.key
   gpg --symmetric backup.key  # Encrypt the export
   ```

2. **Create new wallet and transfer funds** (as above)

3. **Properly backup new mnemonic** - Don't repeat the mistake

## Additional Resources

- **Wallet Setup Guide**: `docs/user-guides/wallet-setup.md`
- **2FA Detailed Guide**: `docs/user-guides/wallet_2fa.md`
- **QR Backup Guide**: `docs/user-guides/mnemonic_qr_backup.md`
- **Hardware Wallet Setup**: `docs/user-guides/wallet_advanced_features.md#hardware-wallets`
- **Testnet Faucet**: `docs/user-guides/TESTNET_FAUCET.md` - Practice with test funds

## Security Principles Summary

1. **Defense in Depth**: Multiple layers of security (encryption + 2FA + hardware)
2. **Minimize Attack Surface**: Use hardware wallets, avoid online storage
3. **Redundancy**: Multiple backups in separate locations
4. **Verification**: Always test backups before funding
5. **Compartmentalization**: Separate hot and cold wallets
6. **Least Privilege**: Only expose keys when necessary for signing
7. **Assume Compromise**: Regular security audits, rotate credentials

---

**Remember**: You are your own bank. XAI cannot recover lost keys or reverse transactions. Security is your responsibility.

**Last Updated**: January 2025
