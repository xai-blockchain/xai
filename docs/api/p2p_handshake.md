# P2P Handshake & Versioning

## Headers
- `X-Node-Version` (required): protocol version. Current: `1`. Unknown versions are rejected.
- `X-Node-Pub` (required): hex-encoded public key.
- `X-Node-Signature` (required): ECDSA signature over body hash + timestamp + nonce.
- `X-Node-Timestamp` (required): unix timestamp (skew checked).
- `X-Node-Nonce` (required): unique nonce for replay protection (TTL enforced).

## Validation Rules
- Reject if missing headers.
- Reject if `X-Node-Version` not in supported set.
- Reject if timestamp skew exceeds configured TTL window.
- Reject if signature invalid or nonce replayed.

## Error Codes (API/P2P status)
- `unsupported_protocol_version`: peer must upgrade/downgrade.
- `missing_signature_headers`: incomplete handshake.
- `timestamp_out_of_window`: clock skew or replay.
- `invalid_or_stale_signature`: signature invalid or stale.
- `replay_detected`: nonce replayed within TTL window.

## Versioning Policy
- Increment `X-Node-Version` on breaking P2P changes; support a small window of versions.
- Document supported versions per release.

