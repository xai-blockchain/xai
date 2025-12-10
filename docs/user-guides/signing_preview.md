# Signing Preview & Hash Verification

The wallet, browser extension, and automation surfaces require **explicit payload previews** before any signature is created. This guide explains how to verify hashes, interpret metadata, and confirm transactions safely everywhere the signer interacts with XAI.

## Why Previews Matter

- Prevents blind signing: you must see the canonical JSON + SHA-256 hash before a key ever authorizes it.
- Enables reproducibility: the same payload always hashes to the same value, so discrepancies are obvious.
- Auditable Acknowledgement: users type the first 8+ hex characters of the hash, proving they saw it.

## Browser Extension Flow

1. Review the structured payload panel: amounts, addresses, nonce, and fee are displayed directly from the canonical JSON sorted by key.
2. Verify the SHA-256 hash shown beneath the payload.
3. Type the required prefix (default 8 hex chars) into the acknowledgement box.
4. Confirm only if the preview matches your intent. The extension blocks signing if:
   - The hash prefix is wrong/too short.
   - The payload mutates (e.g., account switching) after the preview is shown.
5. Signed transactions emit telemetry containing the acknowledged prefix and txid (never the private key).

## CLI & Offline Flows

### `xai-wallet send/export`

```
Payload hash: 7c1e1b7f9f41b4f6cf1a8c6b9b580d054736a2f3a7a8fd62b77aeb6800a5b0aa
Type the first 8 hex characters to acknowledge: 7c1e1b7f
```

Steps:
1. CLI prints the canonical payload as JSON and the full 64-character hash.
2. You type the prefix (or pass `--ack-hash-prefix` for automation; it must match the preview).
3. The CLI records the prefix in logs (with timestamps) and includes it in `/send` or `/wallet/sign` requests.

Offline signing helpers follow the same flow but write the preview + hash to a file for air-gapped review. A second device verifies the hash before loading it into hardware wallets or the CLI signer.

## Verification Checklist

- **Match addresses/amounts**: compare the preview to trusted sources (UI, invoice, governance proposal).
- **Check nonce/fee**: prevents replay or overpayment.
- **Confirm timestamp**: stale payloads will later be rejected.
- **Hash prefix entry**: must match exactly; otherwise the signing command aborts.

## Troubleshooting

- Hash mismatch errors usually mean the payload changed between preview and submission. Re-run the command to regenerate both sides.
- Automation should log the preview hash and prefix; use these logs to compare against `/send` rejections for `txid_mismatch`.
- If the extension shows `Payload changed after preview`, close the request and restart—this indicates the dApp mutated the transaction behind the scenes.

## Security Best Practices

- Never auto-confirm previews; always require the user (or automation policy) to explicitly acknowledge the hash.
- Keep preview UIs minimal but precise: highlight addresses, amounts, and network to reduce misclicks.
- Store acknowledged prefixes + txids in tamper-evident logs for investigations or audits.
- Refuse signing when metadata (network, chain ID, derivation path) mismatches expectations.

Following this philosophy ensures every signing surface—browser, CLI, or offline pipeline—meets professional validator standards and prevents blind-signing vulnerabilities.
