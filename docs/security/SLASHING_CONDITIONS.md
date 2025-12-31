# XAI Validator Slashing Conditions Matrix

**Version:** 1.0.0
**Last Updated:** 2025-12-30

## Overview

Slashing is a mechanism to penalize validators for misbehavior that threatens network security or liveness. This document provides a complete enumeration of slashable offenses.

## Slashing Categories

### Category A: Consensus Violations (Most Severe)

| Offense | Description | Penalty | Evidence Required | Cooldown |
|---------|-------------|---------|-------------------|----------|
| A1: Double Signing | Signing two different blocks at same height | 5% stake | Two conflicting signed blocks | Permanent ban |
| A2: Double Voting | Casting conflicting votes in same round | 5% stake | Two conflicting vote messages | 180 days |
| A3: Pre-commit Equivocation | Pre-committing to conflicting blocks | 5% stake | Two pre-commit messages | 180 days |

### Category B: Liveness Violations (Moderate)

| Offense | Description | Penalty | Evidence Required | Cooldown |
|---------|-------------|---------|-------------------|----------|
| B1: Extended Downtime | Offline for >24 consecutive hours | 0.1% stake | Missed block signatures | 7 days |
| B2: Chronic Downtime | <80% uptime over 30 days | 0.5% stake | Block signature records | 30 days |
| B3: Missed Checkpoints | Failing to sign 3+ checkpoints | 0.2% stake | Missing checkpoint sigs | 14 days |

### Category C: Malicious Behavior (Severe)

| Offense | Description | Penalty | Evidence Required | Cooldown |
|---------|-------------|---------|-------------------|----------|
| C1: Censorship | Provably excluding valid txs | 10% stake | Proof of censorship | 365 days |
| C2: Invalid Block Production | Producing invalid blocks | 2% stake | Invalid block proof | 90 days |
| C3: Transaction Manipulation | Reordering for MEV extraction | 3% stake | Transaction proof | 180 days |

### Category D: Protocol Violations (Variable)

| Offense | Description | Penalty | Evidence Required | Cooldown |
|---------|-------------|---------|-------------------|----------|
| D1: Invalid Signature | Submitting malformed signatures | 0.5% stake | Malformed signature | 30 days |
| D2: Timestamp Manipulation | Block timestamps outside bounds | 1% stake | Block headers | 60 days |
| D3: Difficulty Manipulation | Invalid difficulty adjustments | 2% stake | Block headers | 90 days |

## Evidence Requirements

### Double Sign Proof Structure

```json
{
  "type": "double_sign_proof",
  "validator": "0x...",
  "height": 12345,
  "block_1": {
    "hash": "0x...",
    "signature": "0x...",
    "timestamp": 1735570000
  },
  "block_2": {
    "hash": "0x...",
    "signature": "0x...",
    "timestamp": 1735570001
  }
}
```

### Downtime Proof Structure

```json
{
  "type": "downtime_proof",
  "validator": "0x...",
  "start_height": 12345,
  "end_height": 12500,
  "missed_blocks": 155,
  "expected_blocks": 155,
  "period_hours": 25.8
}
```

### Censorship Proof Structure

```json
{
  "type": "censorship_proof",
  "validator": "0x...",
  "censored_txs": [
    {
      "tx_hash": "0x...",
      "first_seen": 1735570000,
      "blocks_waited": 100,
      "fee_rank": "top_10_percent"
    }
  ],
  "blocks_produced": ["0x...", "0x..."],
  "mempool_snapshots": [...]
}
```

## Slashing Process

### 1. Evidence Submission

```
Anyone can submit slashing evidence via:
- API: POST /api/v1/slashing/submit
- CLI: xai-cli slashing submit <evidence.json>
- Governance: Submit as proposal
```

### 2. Validation Period

| Phase | Duration | Action |
|-------|----------|--------|
| Submission | Immediate | Evidence recorded on-chain |
| Validation | 24 hours | Automated evidence verification |
| Challenge | 72 hours | Validator can dispute |
| Execution | Immediate after challenge | Slash applied if valid |

### 3. Slash Execution

1. Stake deducted from validator
2. Slashed amount sent to insurance fund (50%) and reporter (50%)
3. Validator status updated
4. Event emitted on-chain

## Appeals Process

### Grounds for Appeal

1. Invalid evidence
2. Technical malfunction (not validator fault)
3. Network partition (>33% affected)
4. Force majeure events

### Appeal Timeline

| Stage | Duration |
|-------|----------|
| File appeal | Within 7 days of slash |
| Review | 14 days |
| Decision | Binding |

### Appeal Submission

```json
{
  "slash_id": "0x...",
  "grounds": "technical_malfunction",
  "evidence": {
    "logs": "...",
    "witnesses": ["0x...", "0x..."],
    "description": "..."
  }
}
```

## Jail System

### Jail Conditions

| Offense Category | Jail Duration |
|------------------|---------------|
| A (Consensus) | 180 days minimum |
| B (Liveness) | 7-30 days |
| C (Malicious) | 365 days minimum |
| D (Protocol) | 30-90 days |

### Unjailing Process

1. Wait for jail period to expire
2. Submit unjail transaction
3. Pay unjail fee (0.01% of stake)
4. Resume validation

## Tombstone (Permanent Ban)

### Tombstone Conditions

- 3+ Category A offenses
- 5+ Category C offenses
- Governance decision

### Tombstone Effects

- Permanent removal from validator set
- Stake returned minus penalties
- Cannot re-register

## Monitoring & Alerts

### Validator Self-Monitoring

```yaml
# Recommended monitoring setup
alerts:
  - name: missed_blocks
    threshold: 10
    window: 1h
    action: page

  - name: uptime
    threshold: 95%
    window: 24h
    action: warn

  - name: signature_failures
    threshold: 3
    window: 1h
    action: page
```

### Network-Level Monitoring

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Global miss rate | >5% | Network degradation |
| Validator downtime | >10% validators | Network warning |
| Slashing events | >1/day | Investigation |

## Slashing Parameters (Governance)

These parameters can be modified via governance:

| Parameter | Current Value | Min | Max |
|-----------|---------------|-----|-----|
| `double_sign_penalty` | 5% | 1% | 100% |
| `downtime_penalty` | 0.1% | 0.01% | 1% |
| `censorship_penalty` | 10% | 5% | 100% |
| `jail_duration_double_sign` | 180 days | 30 days | 365 days |
| `reporter_reward` | 50% | 10% | 100% |

## Implementation References

| Component | File |
|-----------|------|
| Slashing Manager | `src/xai/blockchain/slashing_manager.py` |
| Double Sign Detector | `src/xai/blockchain/double_sign_detector.py` |
| Tombstone Manager | `src/xai/blockchain/tombstone_manager.py` |
| Downtime Penalty | `src/xai/blockchain/downtime_penalty_manager.py` |

---

*Slashing conditions are subject to governance updates.*
