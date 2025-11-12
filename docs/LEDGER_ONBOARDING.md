# Ledger Hardware Wallet Integration

1. Install the Ledger Python tooling:
   ```bash
   pip install ledgerblue
   ```

2. Launch the Ledger Bitcoin app and enable contract data export.
3. Start your node with `XAI_LEDGER_PATH="44'/0'/0'/0/0"` (default) and `XAI_WALLET_PASSWORD` set so the node can encrypt files.
4. The node automatically registers the Ledger device (if detected) via `core/hardware_wallet_ledger.py`. The Ledger-derived XAI address shows in the `HardwareWalletManager` list, and any UI can call into the manager to show devices.
5. Signing flows should send the serialized transaction to the Ledger via `LedgerHardwareWallet.sign_transaction(payload)`; the current implementation wraps the Ledger `SIGN` APDU inside the same interface, so GUI code just passes bytes and receives the signature for submission.

Note: If the Ledger device is absent, the node prints “Ledger hardware wallet unavailable” but continues to run. Use the `HardwareWalletManager` helpers to check connected devices before prompting users to confirm on-screen.
