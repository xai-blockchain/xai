# Hardware Wallet Usage (Ledger/Trezor)

XAI supports hardware wallets for secure transaction signing. Private keys never leave your device.

> **See Also:** [Wallet Advanced Features - Hardware Wallets](wallet_advanced_features.md#hardware-wallets) for Python API examples and integration details.

## Supported Devices
- **Ledger** (Nano S, Nano X, Nano S Plus) - requires `pip install ledgerblue`
- **Trezor** (Model One, Model T, Safe 3) - requires `pip install trezor`

## Derivation Path
- Default: `m/44'/22593'/0'/0/0` (XAI coin type)
- Configurable via `XAI_LEDGER_BIP32_PATH` or `XAI_TREZOR_BIP32_PATH`

## Quick Start

### 1. Install Dependencies
```bash
# For Ledger
pip install ledgerblue

# For Trezor
pip install trezor
```

### 2. Get Your Address
```bash
# Ledger
python -m xai.wallet.cli hw-address --ledger

# Trezor
python -m xai.wallet.cli hw-address --trezor
```

### 3. Send Transaction
```bash
# Ledger
python -m xai.wallet.cli hw-send --ledger --recipient XAI... --amount 10

# Trezor
python -m xai.wallet.cli hw-send --trezor --recipient XAI... --amount 10
```

## CLI Commands

### hw-address - Get Address
```bash
python -m xai.wallet.cli hw-address --ledger [--json]
python -m xai.wallet.cli hw-address --trezor [--json]
```
Displays your XAI address derived from the hardware wallet.

### hw-send - Send Transaction
```bash
python -m xai.wallet.cli hw-send --ledger \
    --recipient XAI_ADDRESS \
    --amount 10.5 \
    [--fee 0.001] \
    [--base-url http://localhost:12001] \
    [--2fa-profile wallet1] \
    [--json]
```
Signs and broadcasts a transaction. Review details on your device before confirming.

### hw-sign - Sign Message
```bash
# Sign text
python -m xai.wallet.cli hw-sign --ledger --message "Hello XAI"

# Sign file
python -m xai.wallet.cli hw-sign --trezor --message-file tx.bin
```

### hw-verify - Verify Address
```bash
python -m xai.wallet.cli hw-verify --ledger
```
Displays address on device screen for verification against phishing attacks.

## Security Best Practices

1. **Always verify addresses** - Use `hw-verify` to confirm address matches device display
2. **Review transactions** - Check amount and recipient on device before confirming
3. **Use 2FA** - Add `--2fa-profile` for additional protection
4. **Secure environment** - Only use hardware wallets on trusted machines
5. **Firmware updates** - Keep device firmware up to date

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `XAI_LEDGER_BIP32_PATH` | Ledger derivation path | `m/44'/22593'/0'/0/0` |
| `XAI_TREZOR_BIP32_PATH` | Trezor derivation path | `m/44'/22593'/0'/0/0` |
| `XAI_HARDWARE_WALLET_ENABLED` | Enable HW wallet mode | `false` |
| `XAI_HARDWARE_WALLET_PROVIDER` | Default provider | `mock` |

## Troubleshooting

**"No device found"**
- Ensure device is connected and unlocked
- Check USB permissions: `sudo usermod -aG plugdev $USER`

**"pip install failed"**
- Ledger: `sudo apt install libusb-1.0-0-dev libudev-dev`
- Trezor: `sudo apt install python3-dev cython3 libusb-1.0-0-dev libudev-dev`

**"Permission denied"**
- Add udev rules for your device
- Ledger: `/etc/udev/rules.d/20-hw1.rules`
- Trezor: `/etc/udev/rules.d/51-trezor.rules`
