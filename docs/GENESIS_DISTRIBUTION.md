# Genesis Distribution & Verification

Every node must consume the same genesis file. The SHA-256 digest of that file is stored in `Config.SAFE_GENESIS_HASHES`, so any tampering causes the node to refuse to boot.

## Best practices

1. Before sharing a genesis archive, run:
   ```bash
   python -c "import hashlib, pathlib; path = pathlib.Path('xai/genesis_testnet.json'); print(hashlib.sha256(path.read_bytes()).hexdigest())"
   ```
2. Compare the output against the value printed by `Config.SAFE_GENESIS_HASHES[Config.NETWORK_TYPE]` and commit the hash to your release notes.
3. Transport the file via secure channels (e.g., signed torrent or HTTPS with pinned TLS). Always keep the hash visible so downstream operators can verify it.

If a node detects a mismatch, it raises `ValueError("Genesis file hash mismatch…")` before any block processing, so the chain never forks on corrupted data.
