# Threat Model Overview

This document captures the current assessment of XAI’s critical assets, attackers, and mitigations. It is reviewed each release and whenever large architectural changes are introduced.

## Methodology

1. Identify trust zones and critical assets.
2. Enumerate attacker classes and their capabilities.
3. Document entry points, threats, and mitigations.
4. Capture detection/response coverage and residual risk.

## Trust Zones & Assets

| Zone | Assets | Notes |
| ---- | ------ | ----- |
| Peer-to-peer mesh | Node identity keys, peer certificates, handshake metadata, gossip payloads | Compromise leads to spoofed peers, false data propagation |
| Consensus / state | Block headers/bodies, checkpoint hashes, state roots, mempool contents | Integrity violation leads to double-spend or chain halt |
| Wallet/key custody | Wallet seeds, exchange wallet state, HSM/KMS material, txn signing flows | Highest confidentiality requirements |
| API/control plane | Admin tokens, API keys, WebSocket sessions, rate-limiter state | Entry point for DoS, fraud, or data leakage |
| Observability | SIEM/webhook credentials, Prometheus scrape tokens | Needed to ensure detections fire during attacks |

## Adversaries

| Adversary | Capabilities | Motivations |
| --------- | ------------ | ----------- |
| Malicious peer | Control one or more network identities, replay/flood, attempt MITM | Disrupt consensus or gather intelligence |
| API abuser | High-rate requests, malformed payloads, attempt auth bypass | Drain resources, trigger logic bugs |
| Compromised validator | Valid signing keys, partial view of network | Attempt long-range or short-range reorg |
| Insider | Legitimate access to wallets, trust stores, or CI/CD | Exfiltrate secrets, disable controls |
| Advanced network attacker | BGP/DNS manipulation, TLS interception attempts | Partition network, downgrade security |

## Attack Surface & Controls

### Peer-to-Peer Layer

- **Threats**: replay, identity spoofing, eclipse attacks, bandwidth exhaustion.
- **Controls**: mTLS with client cert pinning, `PeerProofOfWork`, ASN/country diversity enforcement, per-peer rate/bandwidth caps, duplicate suppression caches, signed versioned handshakes, automated peer eviction with audit logs.
- **Detection**: Prometheus `p2p_security_*` metrics, SIEM events for repeated auth failures.

### API / RPC Surface

- **Threats**: brute force, JSON bombs, path traversal, auth bypass, business-logic abuse.
- **Controls**: scoped API keys + JWT, per-endpoint rate limits, `API_MAX_JSON_BYTES`, structured validation w/ schema enforcement, CORS allowlists, replay protection on `/send`.
- **Detection**: Rate limiter counters, 4XX spike alerts, WAF/IDS logs.

### Consensus / Blockchain State

- **Threats**: long-range reorg, finalize invalid block, timestamp manipulation, difficulty manipulation.
- **Controls**: checkpoint sync manager, max reorg depth (`MAX_REORG_DEPTH`), timestamp skew limits, deterministic validation, multi-peer block download with hash verification, difficulty retarget clamps.
- **Detection**: Consensus watchdog alerts when fork depth > threshold, block validation failures exported to SIEM.

### Wallet / Key Management

- **Threats**: seed theft, signing coercion, malware injecting into signing flows.
- **Controls**: Encrypted keystores (AES-256-GCM), hardware wallet enforcement, hash preview + explicit acknowledgment on every signing interface, offline signing support, KMS rotation procedures, multi-factor CLI operations.
- **Detection**: Wallet audit logs, abnormal signing volume alerts, HSM/KMS audit trails.

### Observability & Tooling

- **Threats**: log tampering, alert suppression, webhook hijacking.
- **Controls**: Append-only log forwarding, webhook token rotation, integrity checksum on audit bundles, sandboxed SecurityEventRouter.
- **Detection**: Heartbeat monitors for SIEM/webhook connectivity, alert-on-alert detection for suspicious disabling of rules.

## Attack Trees (Summaries)

1. **Eclipse attack** → manipulate peer list → saturate connections → feed attacker-controlled blocks. Mitigated via ASN/country diversity + max inbound peers per ASN and periodic peer auditing.
2. **Fork attempt** → compromise validator → craft alternate chain → exploit timestamp/difficulty bug. Countered by checkpointing, timestamp limits, and multi-peer validation.
3. **Wallet theft** → steal CLI credentials → bypass signing prompt → exfil seed. Prevented by encrypted keystores, offline signing, hash preview, and required MFA.

## Detection & Response

- SecurityEventRouter emits structured events (`security_event` topic) to SIEM with peer, tx, proposal metadata.
- Incident Response Runbook references this threat model and defines containment actions for each adversary class.
- Automated runbooks (e.g., trust-store rotation) are exercised quarterly.

## Residual Risks

- Large-scale BGP/DNS attacks could still partition operators without diverse network providers.
- Compromised build pipeline could implant backdoors; supply-chain monitoring mitigates but does not eliminate risk.
- Stale NTP on multiple validators may allow limited timestamp manipulation; continuous monitoring partially mitigates.

## Assumptions

- Production nodes run with mTLS + pinned trust.
- Clocks are NTP-synchronized within ±2s.
- SIEM/Webhook endpoints are reachable and monitored 24/7.
- Operators follow the documented key-rotation and patching cadence.
