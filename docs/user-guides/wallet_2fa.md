# Wallet 2FA (TOTP) Guide

Two-factor authentication adds a TOTP check to sensitive wallet actions (send/export) so possession of the keystore alone is insufficient. Profiles live under `~/.xai/2fa_profiles/<label>.json`, contain encrypted secrets + hashed backup codes, and can be audited at any time.

## Profile Lifecycle at a Glance

| Action | Command |
| --- | --- |
| Create/rotate | `xai-wallet 2fa-setup --label <profile> [--user-email you@example.com] [--qr-output qr.png]` |
| Inspect metadata/remaining backup codes | `xai-wallet 2fa-status --label <profile>` |
| Disable/remove | `xai-wallet 2fa-disable --label <profile>` |

## Setup (xai-wallet 2fa-setup)

1. Ensure your wallet is initialized and protected with a password/keystore.
2. Run:
   ```bash
   xai-wallet 2fa-setup --label wallet-alias --user-email you@example.com --qr-output wallet-2fa.png
   ```
3. Scan the terminal QR (or the optional PNG) with an authenticator such as Aegis, 1Password, or Google Authenticator. The provisioning URI is RFC 6238 compliant.
4. Record the displayed backup codes (format `XXXX-XXXX`). Each code is single-use and hashed on disk; store them offline.
5. Enter a current 6-digit TOTP to confirm activation. Failure returns a clear error and leaves the previous profile untouched unless `--force` is used.

## Enforcement Points (send/export flows)

The CLI refuses dangerous operations unless you prove possession of both the wallet password and a recent TOTP/backup code.

```bash
xai-wallet send --from 0xABC... --to 0xDEF... --amount 1.2 \
  --keystore ~/.xai/keystores/wallet.json \
  --2fa-profile wallet-alias

xai-wallet export --address 0xABC... --keystore ~/.xai/keystores/wallet.json \
  --output wallet.enc --2fa-profile wallet-alias
```

Step-by-step prompt order:
1. CLI asks for the keystore password (never echoes input).
2. CLI prompts for a 6-digit TOTP. Use `--otp <code>` only in automation.
3. If the authenticator device is unavailable, enter a backup code (CLI removes it from the profile).
4. On success, the command proceeds; otherwise, you receive `Invalid OTP/backup code` and the operation aborts.

## Status & Auditing

`xai-wallet 2fa-status --label wallet-alias` shows:
- Profile creation time and issuer label.
- How many backup codes remain (no secrets exposed).
- Whether a QR export exists (if `--qr-output` was used).

Use this before wallet sends to ensure the profile is still active and to confirm remaining recovery codes.

## Disable / Reset

```bash
xai-wallet 2fa-disable --label wallet-alias
```

- Requires the wallet password plus a valid TOTP or backup code.
- Deletes the profile JSON and zeroes secrets in-memory before exit.
- To rotate devices, disable the old profile then rerun `2fa-setup` with a new authenticator.

## Backup Codes & Recovery

- Backup codes are generated during setup; the CLI prints them once. Save them offline (paper, secure password manager).
- During `send`/`export` prompts, type a backup code instead of a TOTP if needed—successful use consumes it.
- If you lose both the authenticator and backup codes, you must regenerate the wallet from mnemonic/keystore; support cannot recover 2FA secrets.

## Troubleshooting & Best Practices

- Keep the authenticator clock in sync (enable automatic network time). Drift beyond ±30 seconds causes failures.
- Avoid piping `--otp` from shell history. Prefer interactive prompts or secure automation secrets storage.
- When scripting, set `--2fa-profile` and feed OTPs via environment variables/secure files only inside locked-down CI secrets.
- If repeated failures occur, run `2fa-status` to confirm the profile was not disabled and regenerate if necessary.
