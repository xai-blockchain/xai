# TLS Configuration for Peer-to-Peer Communication

## Overview

Transport Layer Security (TLS) is crucial for securing peer-to-peer communication within the XAI Network. It provides encryption, data integrity, and authentication between communicating nodes, protecting against eavesdropping, tampering, and message forgery.

## Mutual TLS (mTLS)

Our peer-to-peer communication leverages Mutual TLS (mTLS) for enhanced security. In mTLS, both the client and the server present and verify each other's certificates. This ensures that:

1.  **Client authenticates Server:** The client verifies the identity of the server it is connecting to.
2.  **Server authenticates Client:** The server verifies the identity of the client attempting to connect.

This dual authentication mechanism significantly reduces the risk of unauthorized access and ensures that only trusted nodes can participate in the network.

## Certificate Requirements

For production deployments, it is highly recommended to use certificates signed by a trusted Certificate Authority (CA). For development and testing environments, self-signed certificates can be used, but they provide a lower level of trust.

Each node requires:
*   A private key (`.pem` file)
*   A corresponding public certificate (`.pem` file)

These files are typically configured within the `PeerEncryption` class, which handles the loading and management of these cryptographic assets.

## Configuration in `PeerEncryption`

The `PeerEncryption` class (located in `src/xai/network/peer_manager.py`) is responsible for creating and managing SSL contexts for both server and client roles.

### Server-side Configuration

When `is_server` is `True`, the `create_ssl_context` method configures the context to:
*   Load the node's certificate chain (`context.load_cert_chain`).
*   Request client certificates (`ssl.Purpose.CLIENT_AUTH`).

### Client-side Configuration

When `is_server` is `False`, the `create_ssl_context` method configures the context to:
*   Verify the server's certificate (`context.verify_mode = ssl.CERT_REQUIRED`).
*   Perform hostname checking against the certificate (`context.check_hostname = True`).
*   Utilize default trusted CA certificates to validate the server's certificate.

### Configuration knobs

The networking stack now exposes explicit production-grade controls:

- `XAI_TRUSTED_PEER_PUBKEYS`: Comma-separated list of hex-encoded secp256k1 public keys allowed to send/receive signed P2P messages. If empty, all senders are allowed (not recommended for mainnet).
- `XAI_TRUSTED_PEER_CERT_FPS`: Comma-separated list of SHA-256 fingerprints for pinned peer TLS certificates. If set, pins are enforced on both inbound and outbound connections.
- `XAI_TRUSTED_PEER_CERT_FPS_FILE` / `XAI_TRUSTED_PEER_PUBKEYS_FILE`: File-based sources for pins/keys (newline-separated, `#` for comments); hot-reloaded on mtime change.
- `XAI_PEER_REQUIRE_CLIENT_CERT`: Set to `1` to require client certificates on inbound peers (automatically enabled when cert pins are configured).
- `XAI_PEER_NONCE_TTL_SECONDS`: Replay window for signed P2P messages; nonces are tracked per-sender and pruned after this TTL.
- `XAI_PEER_CA_BUNDLE`: Optional CA bundle path used by TLS contexts (client and server) for validation.
- `XAI_P2P_DNS_SEEDS` / `XAI_P2P_BOOTSTRAP_NODES`: Override peer discovery lists for your environment (comma-separated).

### Example (within `PeerEncryption.create_ssl_context`):

```python
import ssl

class PeerEncryption:
    # ... (other methods)

    def create_ssl_context(
        self,
        is_server: bool = False,
        require_client_cert: bool = False,
        ca_bundle: Optional[str] = None,
    ) -> ssl.SSLContext:
        if is_server:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(self.cert_file, self.key_file)
            if require_client_cert:
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = False
                if ca_bundle:
                    context.load_verify_locations(cafile=ca_bundle)
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            if ca_bundle:
                context.load_verify_locations(cafile=ca_bundle)
        return context
```

## Generating Certificates

The `PeerEncryption` class includes a `_generate_self_signed_cert` method that uses the `cryptography` library to generate self-signed certificates for development purposes. For production, it is recommended to use established certificate management practices and tools.

## Deployment Considerations

Ensure that:
*   Certificates and private keys are stored securely and have appropriate file permissions.
*   The common name (CN) or Subject Alternative Name (SAN) in certificates matches the hostname or IP address of the peer.
*   Trusted CA certificates are correctly configured for certificate chain validation.
*   Certificate fingerprints (`XAI_TRUSTED_PEER_CERT_FPS`) are rotated deliberately and kept in sync across nodes.
*   Trusted peer pubkeys (`XAI_TRUSTED_PEER_PUBKEYS`) are distributed securely and updated alongside validator set changes.
*   Replay window (`XAI_PEER_NONCE_TTL_SECONDS`) is tuned to balance latency tolerance with replay risk; mainnet should prefer tighter windows.

## Operational Profiles (recommended)

Use these opinionated profiles to avoid ad-hoc security drift:

- **Validator (mainnet/default):** mTLS required, cert pinning enabled, validator pubkeys whitelisted, short replay window.
- **Public seeder/edge:** TLS required with CA validation, no pubkey whitelist, pins optional; rate limiting + reputation handle abuse.
- **Devnet/local:** Self-signed OK, pins empty, pubkey whitelist empty, relaxed replay window for slow rigs.

### Example env blocks

**Validator / mainnet**
```
XAI_PEER_REQUIRE_CLIENT_CERT=1
XAI_TRUSTED_PEER_CERT_FPS=abc123...,def456...   # sha256 fingerprints
XAI_TRUSTED_PEER_PUBKEYS=02abcd...,03ef01...    # hex secp256k1 pubkeys
XAI_PEER_NONCE_TTL_SECONDS=90
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
```

**Public seeder**
```
XAI_PEER_REQUIRE_CLIENT_CERT=0
XAI_TRUSTED_PEER_CERT_FPS=
XAI_TRUSTED_PEER_PUBKEYS=
XAI_PEER_NONCE_TTL_SECONDS=180
XAI_PEER_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
```

**Devnet**
```
XAI_PEER_REQUIRE_CLIENT_CERT=0
XAI_TRUSTED_PEER_CERT_FPS=
XAI_TRUSTED_PEER_PUBKEYS=
XAI_PEER_NONCE_TTL_SECONDS=300
# Leave CA bundle empty to accept local self-signed
XAI_PEER_CA_BUNDLE=
```
