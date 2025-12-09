# Checkpoint Payload Format (Proposed)

This document defines a simple JSON container for checkpoint payload exchange to enable partial sync.

```json
{
  "height": 12345,
  "block_hash": "<block hash at checkpoint height>",
  "state_hash": "<sha256 of serialized state payload>",
  "data": {
    "utxo_root": "<merkle root or snapshot hash>",
    "state_root": "<optional state root>",
    "metadata": {
      "timestamp": 1712345678,
      "difficulty": 123456789,
      "chainwork": "<hex cumulative work>",
      "signature": "<optional signature of checkpoint issuer>"
    }
  }
}
```

## Validation Steps
1. Parse JSON and required fields (`height`, `block_hash`, `state_hash`, `data`).
2. Recompute `sha256(str(data).encode('utf-8'))` and compare to `state_hash`.
3. Optionally verify metadata signature against a trusted key list.
4. Ensure checkpoint height is not lower than the latest trusted checkpoint.

## Application Steps
- Restore UTXO/state from payload data.
- Set chain tip to `height`/`block_hash`.
- Persist provenance (source, signature, timestamp).
- Reject reorgs below checkpoint height.

## Notes
- This format is intentionally minimal for initial interoperability; future revisions may adopt a binary format and canonical serialization for hashing.
- Signatures are optional but recommended for production deployments.
