# Mnemonic QR Backup Guide

The CLI supports exporting a tamper-evident, encrypted QR backup of your seed phrase. Use this flow to store recovery material offline without exposing raw mnemonics on screen or disk.

## Prerequisites

- XAI CLI installed and configured.
- A wallet already initialized with a mnemonic.

## Export Steps

1. Run the QR backup command:
   ```bash
   xai-wallet mnemonic-qr --wallet <name> --output /path/to/backup.png
   ```
2. When prompted, enter the wallet password (encrypts the QR payload with AES-256-GCM).
3. The CLI writes `backup.png` and an accompanying metadata file containing:
   - Hash of the encrypted payload
   - Creation timestamp
   - Wallet name and derivation metadata (no plaintext seed)
4. Store the PNG offline (printed or on an air-gapped USB). Do not keep it on networked devices.

## Restore Steps

1. On a trusted machine, run:
   ```bash
   xai-wallet mnemonic-qr-restore --input /path/to/backup.png --output /path/to/wallet.json
   ```
2. Enter the backup password; the CLI verifies the hash from metadata before decryption.
3. Import the restored wallet into the CLI or mobile app as needed.

## Tamper-Evidence & Safety

- The metadata hash must match during restore; mismatches abort the process.
- The QR is encrypted; scanning without the password yields no mnemonic.
- Never photograph or upload the QR to cloud services; treat it as sensitive recovery data.

## Troubleshooting

- **Hash mismatch**: Re-run from the original backup source; ensure the file was not modified.
- **Wrong password**: Restores will fail; ensure you retain the backup password securely (separate from the QR).
- **Corrupted image**: Re-export a fresh QR from the wallet on a trusted device.***
