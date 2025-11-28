# Signed Premine Manifest

After `generate_premine.py` runs it now writes `premine_manifest.json` alongside the encrypted wallets. That manifest:

- Lists every generated wallet (without private keys).
- Includes `network`, `address_prefix`, timestamp, and the signer’s public key.
- Contains an ECDSA signature (secp256k1) produced by `AuditSigner`.

To verify or replay:

1. Download both the manifest and `premine_wallets_SUMMARY.json`.
2. Check that `signature` matches the payload (JSON sorted by keys) using the `public_key` field.
3. Ensure the `address_prefix` matches your `Config` (TXAI for testnet, XAI for mainnet).
4. Use this manifest for explorers or auditors before trusting the hot/cold wallet lists.

If you rerun the script with the same wallets, it will skip overwriting the manifest unless the generated set differs—otherwise it throws an error, preserving immutability.
