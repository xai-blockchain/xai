# Threat Model Overview

## Scope
- P2P transport and handshake
- Transaction/mempool validation
- Consensus/fork choice and reorg handling
- Key management and trust stores

## Assets
- Node identity keys (signing P2P messages/blocks)
- Wallet private keys (users/operators)
- Blockchain state (UTXO set, blocks)
- P2P trust stores (pubkeys, cert fingerprints)
- SIEM/webhook secrets

## Adversaries
- Malicious peers attempting replay/DoS/spam
- Man-in-the-middle altering or replaying P2P traffic
- Malicious API clients submitting invalid/high-rate transactions
- Compromised validators attempting long-range/fork attacks
- Insider threat with access to trust stores or webhook secrets

## Entry Points & Controls
- **P2P**: mTLS (`XAI_PEER_REQUIRE_CLIENT_CERT`), trust stores, nonce TTL, rate/bandwidth caps, signature verification, versioned handshake (`X-Node-Version`).
- **API**: request validation, auth keys, rate limits, content-length caps.
- **Consensus**: bounded reorg depth, checkpoint protection, deterministic validation, difficulty retarget rules.
- **Mempool**: min fee, per-sender caps, invalid ban windows, replay/nonce enforcement.
- **Observability**: SecurityEventRouter to SIEM, Prometheus alerts, P2P security dashboards.

## Threats & Mitigations
- Replay/stale P2P messages → Nonce TTL, replay counters/alerts, mTLS, pinned trust.
- Flood/DoS on P2P → Rate limiters, bandwidth caps, NetworkPolicy CIDRs, reputation bans.
- Invalid signatures → Signature verification, invalid-signature counters/alerts, trust-store enforcement.
- Fork/reorg attempts → Checkpoint manager, max reorg depth, integrity validation, reorg simulations in tests.
- Key compromise → Trust-store rotation runbook + tool, webhook token rotation, SIEM monitoring.
- Configuration drift → Hardening checks in CI, constraints/lockfiles for reproducible installs.

## Assumptions
- Nodes run with mTLS + pinned trust in production.
- Clocks reasonably synchronized (NTP) to enforce nonce TTL and timestamp checks.
- SIEM/webhook endpoint is reachable and monitored.
