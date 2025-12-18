# XAI Wallet Advanced Features

This guide covers advanced wallet features for power users and developers.

## Table of Contents

1. [Address Checksums (XIP-55)](#address-checksums-xip-55)
2. [Multisig Wallets](#multisig-wallets)
3. [Hardware Wallets](#hardware-wallets)
4. [Unsigned Transactions (XUTX)](#unsigned-transactions-xutx)
5. [Typed Data Signing (XIP-712)](#typed-data-signing-xip-712)
6. [Watch-Only Wallets](#watch-only-wallets)
7. [Two-Factor Authentication](#two-factor-authentication)
8. [Security Best Practices](#security-best-practices)

---

## Address Checksums (XIP-55)

XAI uses EIP-55 style mixed-case checksumming for address validation. This detects typos and copy-paste errors.

### Checksum Format

```
Raw:      XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b
Checksum: XAI7A8b9C0d1E2f3A4b5C6D7e8F9a0B1c2D3e4F5A6b
```

Addresses starting with `TXAI` (testnet) are also supported.

### Python API Usage

```python
from xai.core.address_checksum import (
    to_checksum_address,
    is_checksum_valid,
    validate_address,
    normalize_address,
)

# Convert to checksum format
addr = to_checksum_address("XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")
# Result: 'XAI7A8b9C0d1E2f3A4b5C6D7e8F9a0B1c2D3e4F5A6b'

# Validate checksum
if is_checksum_valid(user_input):
    print("Valid address with correct checksum")

# Full validation with error messages
is_valid, result = validate_address(user_input, require_checksum=True)
if is_valid:
    print(f"Normalized address: {result}")
else:
    print(f"Error: {result}")

# Normalize any valid address to checksummed format
normalized = normalize_address("xai7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")
```

**Note:** All-lowercase or all-uppercase addresses are considered valid (no checksum applied).

---

## Multisig Wallets

Create M-of-N multisignature wallets requiring multiple parties to authorize transactions.

### CLI Commands

```bash
# Create 2-of-3 multisig wallet
xai-wallet multisig-create \
    --threshold 2 \
    --public-keys PK1 PK2 PK3 \
    -o multisig_wallet.json

# Sign transaction with your key
xai-wallet multisig-sign \
    --tx-file pending_tx.json \
    --keystore alice.keystore

# Check signature collection status
xai-wallet multisig-status --tx-file pending_tx.json

# Submit when threshold is met
xai-wallet multisig-submit --tx-file pending_tx.json
```

### Python API Usage

```python
from xai.wallet.multisig_wallet import MultiSigWallet

# Create 2-of-3 wallet
public_keys_pem = [pk1_hex, pk2_hex, pk3_hex]  # PEM-encoded public keys
wallet = MultiSigWallet(public_keys=public_keys_pem, threshold=2)

# Create pending transaction
tx_data = {"recipient": "XAI...", "amount": 100}
tx = wallet.create_transaction(
    tx_id="tx123",
    tx_data=tx_data,
    nonce=0  # Optional: prevents replay attacks
)

# Each signer adds their signature
wallet.add_partial_signature(tx_id="tx123", public_key_hex=pk1_hex, signature_hex=sig1)
wallet.add_partial_signature(tx_id="tx123", public_key_hex=pk2_hex, signature_hex=sig2)

# Check status
status = wallet.get_transaction_status("tx123")
print(f"Signatures: {status['signatures_collected']}/{status['signatures_required']}")

# Finalize when ready (automatically when threshold met)
if status['is_ready']:
    final_tx = wallet.finalize_transaction("tx123")
    # Broadcast final_tx to network
```

### Workflow

1. **Setup**: All parties agree on M-of-N configuration and exchange public keys
2. **Transaction Creation**: One party creates unsigned transaction
3. **Signature Collection**: Each signer reviews and signs using their keystore
4. **Submission**: When threshold met, any party can broadcast

### Security Features

- Nonce/sequence tracking prevents replay attacks
- Each signature is bound to canonical payload
- Maximum 15 signers supported
- Duplicate public keys rejected

---

## Hardware Wallets

Sign transactions with Ledger or Trezor devices. Private keys never leave the hardware.

### Setup

```bash
# For Ledger support
pip install ledgerblue

# For Trezor support
pip install trezor
```

### CLI Commands

```bash
# Get address from Ledger
xai-wallet hw-address --ledger

# Get address from Trezor
xai-wallet hw-address --trezor

# Send transaction (signed on device)
xai-wallet hw-send \
    --ledger \
    --recipient XAI... \
    --amount 10

# Sign arbitrary message
xai-wallet hw-sign \
    --trezor \
    --message "Hello XAI"

# Verify address on device screen
xai-wallet hw-verify --ledger
```

### Python API Usage

```python
from xai.core.hardware_wallet import get_default_hardware_wallet
from xai.core.hardware_wallet_ledger import LedgerHardwareWallet
from xai.core.hardware_wallet_trezor import TrezorHardwareWallet

# Connect to Ledger
ledger = LedgerHardwareWallet()
ledger.connect()

# Get address (shown on device screen)
address = ledger.get_address()
print(f"Ledger address: {address}")

# Sign transaction (requires user confirmation on device)
tx_bytes = b"..."  # Transaction payload
signature = ledger.sign_transaction(tx_bytes)

# Get public key
pubkey = ledger.get_public_key()
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `XAI_HARDWARE_WALLET_ENABLED` | Enable hardware wallet mode | `false` |
| `XAI_HARDWARE_WALLET_PROVIDER` | Default provider (`ledger`, `trezor`, `mock`) | `mock` |
| `XAI_LEDGER_BIP32_PATH` | Ledger derivation path | `m/44'/22593'/0'/0/0` |
| `XAI_TREZOR_BIP32_PATH` | Trezor derivation path | Same as Ledger |
| `XAI_ALLOW_MOCK_HARDWARE_WALLET` | Allow mock wallet (testing only) | `false` |

**Security Note:** MockHardwareWallet is for TESTING ONLY. Never use in production.

---

## Unsigned Transactions (XUTX)

XAI's equivalent of Bitcoin's PSBT for safe offline signing.

### Creating Unsigned Transactions

```python
from xai.core.unsigned_transaction import (
    create_transfer,
    create_multisig_transfer,
    UnsignedTransaction,
)

# Simple transfer
tx = create_transfer(
    sender="XAI_SENDER",
    recipient="XAI_RECIPIENT",
    amount=100.0,
    fee=0.001,
    memo="Payment for services",
    network="mainnet"
)

# Review before signing
print(tx.display_for_review())

# Get hash for signing
payload_hash = tx.payload_hash
print(f"Sign this hash: {payload_hash}")
```

### Review Display Example

```
============================================================
XAI UNSIGNED TRANSACTION - REVIEW CAREFULLY
============================================================
Network:     MAINNET
Type:        transfer
Status:      unsigned
------------------------------------------------------------
From:        XAI7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b
To:          XAIabcdef1234567890abcdef1234567890abcdef12
Amount:      100.0 XAI
Fee:         0.001 XAI
Total:       100.001 XAI
------------------------------------------------------------
Payload Hash: 5f3d8a9c...
Created:     2025-01-15 14:30:00
Memo:        Payment for services
------------------------------------------------------------
Signatures:  0/1
  1. [○ Pending] awaiting
============================================================
```

### Serialization

```python
# Export for transfer to another device
json_str = tx.to_json()
base64_str = tx.to_base64()

# Save to file
with open("unsigned_tx.json", "w") as f:
    f.write(json_str)

# Import on signing device
with open("unsigned_tx.json", "r") as f:
    tx = UnsignedTransaction.from_json(f.read())

# Or from base64 (compact for QR codes)
tx = UnsignedTransaction.from_base64(base64_str)
```

### Adding Signatures

```python
# Sign payload
signature = sign_with_private_key(tx.payload_bytes)

# Add signature to transaction
tx.add_signature(
    public_key="...",
    signature=signature.hex(),
    label="Alice's Ledger"
)

# Check if ready
if tx.is_ready:
    print("Transaction ready for broadcast")
```

### Transaction Status

- `unsigned`: No signatures collected
- `partially_signed`: Some signatures collected (multisig)
- `fully_signed`: Threshold met, ready to broadcast
- `broadcast`: Submitted to network
- `confirmed`: Included in block

---

## Typed Data Signing (XIP-712)

Sign structured data with domain separation to prevent replay attacks.

### Personal Message Signing (XIP-191)

```python
from xai.core.typed_signing import hash_personal_message, create_personal_sign_request

# Hash message for signing
msg_hash = hash_personal_message("I agree to the terms")

# Create wallet request (for RPC)
request = create_personal_sign_request("I agree to the terms")
# Returns: {"method": "personal_sign", "params": {...}}
```

The message is prefixed with `\x19XAI Signed Message:\n<length>` to prevent signing arbitrary transaction data.

### Typed Data Signing (XIP-712)

```python
from xai.core.typed_signing import (
    TypedDataDomain,
    hash_typed_data,
    create_typed_sign_request,
    TRANSFER_TYPES,
)

# Define domain (prevents cross-app replay)
domain = TypedDataDomain(
    name="My DApp",
    version="1",
    chain_id=1,
    verifying_contract="XAI_CONTRACT_ADDRESS"
)

# Define message
message = {
    "from": "XAI_SENDER",
    "to": "XAI_RECIPIENT",
    "amount": 1000,
    "nonce": 0,
}

# Get hash for signing
data_hash = hash_typed_data(domain, "Transfer", TRANSFER_TYPES, message)

# Or create full request for wallet
request = create_typed_sign_request(domain, "Transfer", TRANSFER_TYPES, message)
```

### Predefined Types

```python
from xai.core.typed_signing import PERMIT_TYPES, TRANSFER_TYPES, VOTE_TYPES

# PERMIT_TYPES: Gasless token approvals (ERC-2612 style)
# TRANSFER_TYPES: Token transfers
# VOTE_TYPES: Governance voting
```

### Token Permits (Gasless Approvals)

```python
from xai.core.typed_signing import create_permit_signature_request

# Create permit signature for ERC20-style gasless approval
request = create_permit_signature_request(
    token_name="XAI Token",
    token_address="XAI_TOKEN_ADDRESS",
    chain_id=1,
    owner="XAI_OWNER",
    spender="XAI_SPENDER",
    value=1000,
    nonce=0,
    deadline=1700000000,  # Unix timestamp
)
```

This allows users to approve token spending without paying gas fees. The spender submits the permit signature along with their transaction.

---

## Watch-Only Wallets

Monitor addresses and balances without storing private keys.

### CLI Commands

```bash
# Add single address
xai-wallet watch \
    --address XAI... \
    --label "Exchange Deposit" \
    --tags cold-storage audit

# Add multiple addresses from extended public key (xpub)
xai-wallet watch \
    --xpub xpub6D4BDPc... \
    --derive-count 10 \
    --start-index 0 \
    --change 0 \
    --label "HD Wallet Receiving"

# Add change addresses
xai-wallet watch \
    --xpub xpub6D4BDPc... \
    --derive-count 5 \
    --change 1 \
    --label "HD Wallet Change"

# List all watched addresses
xai-wallet watch-list

# Query balances
xai-wallet watch --address XAI... --balance
```

### Python API Usage

```python
from xai.core.watch_only_wallet import WatchOnlyWalletStore

store = WatchOnlyWalletStore()

# Add address
store.add_address(
    address="XAI...",
    label="Treasury Wallet",
    notes="Company treasury cold storage",
    tags=["treasury", "cold-storage"]
)

# Add from xpub (derives multiple addresses)
addresses = store.add_from_xpub(
    xpub="xpub6D4BDPc...",
    start_index=0,
    count=10,
    change=0,  # 0=receiving, 1=change
    label="Customer Deposits"
)

# List addresses
all_addresses = store.list_addresses(tags=["treasury"])

# Remove address
store.remove_address("XAI...")
```

### Use Cases

- Auditing exchange hot/cold wallets
- Monitoring multisig treasuries
- Tracking customer deposits
- Portfolio tracking without key exposure

---

## Two-Factor Authentication

Add TOTP-based 2FA protection to wallet operations.

### Setup

```bash
# Enable 2FA for a wallet
xai-wallet twofa-setup --keystore my_wallet.keystore

# This displays:
# 1. QR code for authenticator app
# 2. Manual entry key
# 3. Backup codes (store securely!)

# Check 2FA status
xai-wallet twofa-status --keystore my_wallet.keystore

# Disable 2FA (requires valid TOTP code)
xai-wallet twofa-disable --keystore my_wallet.keystore --code 123456
```

### Python API Usage

```python
from xai.security.two_factor_auth import TwoFactorAuthManager, TwoFactorSetup

# Setup 2FA
manager = TwoFactorAuthManager()
setup = manager.create_profile(
    identifier="alice@example.com",
    issuer="XAI Wallet"
)

# Display to user
print(f"Secret Key: {setup.secret_key}")
print(f"QR Code URI: {setup.provisioning_uri}")
print(f"Backup Codes: {setup.backup_codes}")

# Verify setup code
if manager.verify_code(setup.secret_key, user_provided_code):
    print("2FA enabled successfully")

# Later: verify transaction
if manager.verify_code(secret_key, transaction_code):
    # Proceed with transaction
    pass
```

### Security Features

- Time-based one-time passwords (TOTP) compatible with Google Authenticator, Authy, etc.
- 10 single-use backup codes for account recovery
- 30-second code rotation
- Resistant to replay attacks

---

## Security Best Practices

### Address Handling

1. **Always use checksummed addresses** - Prevents typos
   ```python
   from xai.core.address_checksum import normalize_address
   safe_addr = normalize_address(user_input)
   ```

2. **Verify addresses visually** - Compare first/last characters
3. **Use address labels** - Easier to identify recipients

### Hardware Wallets

1. **Verify on device screen** - Never trust software display alone
2. **Use official firmware** - Only download from manufacturer
3. **Physical security** - Store device securely when not in use
4. **Test with small amounts** - Before large transactions

### Multisig

1. **Use for treasuries** - No single point of failure
2. **Geographic distribution** - Spread signers across locations
3. **Verify all signers** - Know who has signing power
4. **Regular audits** - Review signature logs

### Typed Data Signing

1. **Review typed data carefully** - Understand what you're signing
2. **Check domain** - Prevents phishing (verify app name, version, contract)
3. **Verify contract address** - Ensure it matches expected DApp
4. **Be wary of blind signing** - If you can't read it, don't sign it

### Keystore Security

1. **Strong passwords** - 20+ characters, mixed case, numbers, symbols
2. **Encrypt keystores** - Use AES-256-GCM (default)
3. **Backup securely** - Store encrypted backups offline
4. **Use 2FA** - Extra layer for sensitive wallets

### Network Security

1. **Use HTTPS** - For all API connections
2. **Verify TLS certificates** - Prevent man-in-the-middle attacks
3. **Local nodes** - Run your own node when possible
4. **Testnet first** - Test integrations on testnet

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `XAI_API_URL` | Node API endpoint | `http://localhost:12001` |
| `XAI_HARDWARE_WALLET_ENABLED` | Enable hardware wallet mode | `false` |
| `XAI_HARDWARE_WALLET_PROVIDER` | Provider: `ledger`, `trezor`, `mock` | `mock` |
| `XAI_LEDGER_BIP32_PATH` | Ledger derivation path | `m/44'/22593'/0'/0/0` |
| `XAI_TREZOR_BIP32_PATH` | Trezor derivation path | Same as Ledger |
| `XAI_ALLOW_MOCK_HARDWARE_WALLET` | Allow mock (testing only) | `false` |

---

## Additional Resources

- [Basic Wallet Setup](./wallet-setup.md) - Getting started guide
- [Transaction Guide](./transactions.md) - Creating and submitting transactions
- [CLI Reference](../CLI_GUIDE.md) - Complete CLI command reference
- [Security Model](../SECURITY.md) - Overall security architecture

---

## Troubleshooting

### "Invalid checksum" error

The address checksum doesn't match. Use the suggested checksummed version or verify you copied the address correctly.

### Hardware wallet not detected

1. Check USB connection
2. Unlock device
3. Open XAI app on device (for Ledger)
4. Check permissions: `pip install ledgerblue --upgrade`

### Multisig threshold not met

Verify all signatures are from authorized public keys and correctly formatted. Check status with `multisig-status`.

### 2FA code rejected

1. Ensure device time is synchronized
2. Use current code (changes every 30s)
3. Try backup code if TOTP unavailable
4. Check for rate limiting (wait 1 minute between attempts)
