# Wallet 2FA (TOTP) Guide

Two-factor authentication adds a TOTP code requirement to sensitive wallet actions (send/export). This guide covers setup, use, and recovery.

## Setup

1. Ensure your wallet is initialized and password protected.
2. Run:
   ```bash
   xai-wallet 2fa-setup --wallet <name>
   ```
3. Scan the displayed QR code with an authenticator app (e.g., Authy, Google Authenticator) and store generated backup codes securely.
4. Confirm by entering a current 6-digit TOTP to finalize setup.

## Usage

- When sending funds or exporting keys, the CLI prompts for:
  - Wallet password
  - Current TOTP code
- If codes are wrong/expired, the operation is rejected; try the next 30s window.

## Backup Codes

- A set of one-time backup codes is generated during setup.
- Store them offline; each code is single-use and bypasses the TOTP generator if your device is unavailable.

## Disable / Reset

```bash
xai-wallet 2fa-disable --wallet <name>
```

- Requires password + current TOTP (or a valid backup code). Disabling clears stored secrets.
- To reset (lost device), disable with a backup code, then run setup again with a new authenticator.

## Best Practices

- Keep TOTP device offline when possible; avoid syncing codes to cloud backups.
- Do not reuse backup codes; regenerate if you suspect exposure.
- If clock drift causes repeated failures, resync the authenticator’s time and retry.***
