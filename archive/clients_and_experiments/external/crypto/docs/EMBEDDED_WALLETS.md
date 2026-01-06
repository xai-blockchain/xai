# Embedded Wallets & Account Abstraction

Embedded wallets provide seamless account abstraction through email/social identifiers.

## Workflow

1. **Create** `POST /wallet/embedded/create` with:
   - `alias` (email/username), `contact`, and `secret` (passphrase).
   - Returns the new address plus `session_token`.
2. **Authenticate** `POST /wallet/embedded/login` with `alias` + `secret`.
   - Returns the last known address and a new `session_token`.
3. **Session usage**: `session_token` can be used by UIs to map the embedded identity to wallet actions; the node stores the token in memory per alias.

## Security

- Secrets are hashed with `Config.EMBEDDED_WALLET_SALT`.
- Wallet files are created with the provided `secret` (or default `XAI_WALLET_PASSWORD`) via `WalletManager`.
- There's no private key leakage thanks to the existing wallet flow; tokens expire when the node restarts.

## Extending

To tie embedded wallets into a browser/mining UI, call the two endpoints during onboarding, store the returned address, and optionally rotate the secret if a user updates their social login. Use `Config.EMBEDDED_WALLET_DIR` to shard the storage if you need multi-tenant deployments.
