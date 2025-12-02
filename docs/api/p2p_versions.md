# P2P Protocol Versions

This page tracks the supported P2P protocol versions, feature flags, and compatibility guarantees per node release. Keep this table updated whenever the handshake schema, supported feature set, or protocol semantics change.

- Source of truth: `config/p2p_versions.yaml`
- Handshake headers: `X-Node-Version`, `X-Node-Features`
- Default transport: WebSocket; optional QUIC listener on `p2p_port + 1` when enabled.

| Node Release | Protocol Version | Supported Features | Notes | Status |
|--------------|------------------|--------------------|-------|--------|
| 2.0.0        | 1                | ws, quic           | Versioned handshake with header enforcement, optional QUIC transport for low-latency peers. | current |

## Update Procedure
- Bump `P2PSecurityConfig.PROTOCOL_VERSION` and `SUPPORTED_VERSIONS` alongside the handshake/schema change.
- Update `config/p2p_versions.yaml` with the new entry; move prior release to `deprecated: true` if applicable.
- Regenerate documentation (`mkdocs build`) to ensure navigation links resolve.
- Add/extend interoperability tests that assert the supported version matrix.
- Update `docs/release_checklist.md` to reflect the new supported version for the release being cut.
