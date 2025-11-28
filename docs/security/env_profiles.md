# P2P Security Environment Profiles

Opinionated environment presets for running XAI nodes with consistent security posture.

## Profiles

### Validator / Mainnet
Use for validator/consensus nodes. Requires mutual TLS and strict identity controls.

```
XAI_PEER_REQUIRE_CLIENT_CERT=1
XAI_TRUSTED_PEER_CERT_FPS=abc123...,def456...   # sha256 fingerprints (hex, comma-separated)
XAI_TRUSTED_PEER_PUBKEYS=02abcd...,03ef01...    # hex secp256k1 pubkeys (compressed form)
XAI_PEER_NONCE_TTL_SECONDS=90
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
XAI_TRUSTED_PEER_CERT_FPS_FILE=/etc/xai/p2p/cert_pins.txt
XAI_TRUSTED_PEER_PUBKEYS_FILE=/etc/xai/p2p/peer_keys.txt
XAI_P2P_DNS_SEEDS=seed1.xai-network.io,seed2.xai-network.io
XAI_P2P_BOOTSTRAP_NODES=wss://node1.xai-network.io:8333,wss://node2.xai-network.io:8333
```

### Public Seeder / Edge
Accepts broader connections but still enforces TLS. Pins optional; relies on rate limits + reputation.

```
XAI_PEER_REQUIRE_CLIENT_CERT=0
XAI_TRUSTED_PEER_CERT_FPS=
XAI_TRUSTED_PEER_PUBKEYS=
XAI_PEER_NONCE_TTL_SECONDS=180
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
XAI_TRUSTED_PEER_CERT_FPS_FILE=
XAI_TRUSTED_PEER_PUBKEYS_FILE=
XAI_P2P_DNS_SEEDS=
XAI_P2P_BOOTSTRAP_NODES=
```

### Devnet / Local
Relaxed settings for local testing; OK with self-signed certs and wider replay window.

```
XAI_PEER_REQUIRE_CLIENT_CERT=0
XAI_TRUSTED_PEER_CERT_FPS=
XAI_TRUSTED_PEER_PUBKEYS=
XAI_PEER_NONCE_TTL_SECONDS=300
XAI_PEER_CA_BUNDLE=
XAI_TRUSTED_PEER_CERT_FPS_FILE=
XAI_TRUSTED_PEER_PUBKEYS_FILE=
XAI_P2P_DNS_SEEDS=
XAI_P2P_BOOTSTRAP_NODES=
```

## Guidance
- Keep fingerprints/pubkeys in sync with validator set changes; distribute over authenticated channels.
- Rotate fingerprints deliberately with change control; avoid auto-updating pins in production.
- Store pins/pubkeys in files (`XAI_TRUSTED_PEER_CERT_FPS_FILE`, `XAI_TRUSTED_PEER_PUBKEYS_FILE`) managed by your secrets/pipeline tooling; hot reload is supported via mtime checks.
- Tighten `XAI_PEER_NONCE_TTL_SECONDS` on mainnet to reduce replay window; allow more slack only where latency demands it.
- Prefer CA-signed certs in production; use self-signed only on devnet/local.
- See `.env.example` at repo root for copy-pasteable blocks of these profiles.
