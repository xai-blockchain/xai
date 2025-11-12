# Hardware Wallet Roadmap

The `core.hardware_wallet` module ships a extensible protocol interface and manager so we can plug in Ledger, Trezor, or other devices in the future.  
Current responsibilities:

* `HardwareWallet` (protocol): defines `connect()`, `get_address()`, and `sign_transaction(payload)` so signing occurs entirely on the device.
* `HardwareWalletManager`: tracks connected devices, exposes discovery stubs, and can be wired into the wallet creation flow once device libraries are available.

## Next steps

1. Integrate a concrete driver (e.g., `ledgerwallet` or `trezorlib`) that implements `HardwareWallet`.
2. Connect the driver to the wallet claim/setup flows so onboarding UIs accept both hot keys and paired hardware wallets.
3. Add documentation & tests showing how to refresh `HardwareWalletManager` and handle disconnects/resets.

Ledger integration is already documented separately in `docs/LEDGER_ONBOARDING.md`, which explains how to install `ledgerblue`, connect a device, and let the node register it automatically. When Ledger or any other driver is in place, reuse the `HardwareWallet` protocol so UI code stays device-agnostic.
