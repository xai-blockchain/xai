# Cross-Chain Bridge Security Documentation

**Version:** 1.0.0
**Last Updated:** 2025-12-30

## Overview

This document describes the security architecture and threat model for XAI cross-chain bridges.

## Bridge Architecture

### Components

```
┌─────────────────┐         ┌─────────────────┐
│   Source Chain  │         │   Target Chain  │
│     (XAI)       │         │   (External)    │
├─────────────────┤         ├─────────────────┤
│ Lock Contract   │◄───────►│ Mint Contract   │
│ Bridge Relayer  │         │ Bridge Relayer  │
│ Validator Set   │         │ Validator Set   │
└─────────────────┘         └─────────────────┘
         │                           │
         └───────────┬───────────────┘
                     │
              ┌──────┴──────┐
              │  Relayers   │
              │  (N of M)   │
              └─────────────┘
```

### Bridge Types

| Type | Description | Security Model |
|------|-------------|----------------|
| Lock/Mint | Lock on source, mint on target | Multisig relayers |
| Burn/Mint | Burn on source, mint on target | Multisig relayers |
| Atomic Swap | Hash time-locked contracts | Trustless |

## Threat Model

### Attack Vectors

#### 1. Relayer Compromise
**Threat:** Malicious relayer submits false proofs
**Mitigations:**
- N-of-M multisig requirement
- Fraud proof window (7 days)
- Slashing for misbehavior

#### 2. Double-Spending
**Threat:** Spend on source, then again on target
**Mitigations:**
- Wait for finality on source
- Minimum confirmation depth
- Reorg monitoring

#### 3. Replay Attacks
**Threat:** Replay bridge message on different chain
**Mitigations:**
- Chain ID in message
- Unique nonce per message
- Message expiration

#### 4. Oracle Manipulation
**Threat:** Fake price data for wrapped asset
**Mitigations:**
- Multi-oracle redundancy
- TWAP validation
- Circuit breakers

#### 5. Smart Contract Bugs
**Threat:** Vulnerabilities in bridge contracts
**Mitigations:**
- Formal verification
- Multiple audits
- Bug bounty
- Upgradeable with timelock

### Trust Assumptions

| Component | Trust Level | Failure Impact |
|-----------|-------------|----------------|
| Source Chain | High | Loss of locked funds |
| Target Chain | High | Invalid minted tokens |
| Relayers | Medium | Delayed transfers |
| Oracle | Medium | Price manipulation |
| Admin Keys | High | Full control |

## Security Controls

### Multi-Signature Requirements

| Operation | Threshold | Total Keys |
|-----------|-----------|------------|
| Normal transfers | 4 of 7 | 7 |
| Emergency pause | 2 of 7 | 7 |
| Parameter changes | 5 of 7 | 7 |
| Upgrade contracts | 6 of 7 | 7 |

### Time Locks

| Operation | Delay |
|-----------|-------|
| Contract upgrade | 48 hours |
| Fee changes | 24 hours |
| Relayer changes | 24 hours |
| Emergency pause | Immediate |

### Rate Limits

| Asset | Per-Transaction | Per-Hour | Per-Day |
|-------|-----------------|----------|---------|
| XAI | 100,000 | 1,000,000 | 10,000,000 |
| USDC | 500,000 | 5,000,000 | 50,000,000 |

### Monitoring & Alerts

| Event | Alert Level | Response SLA |
|-------|-------------|--------------|
| Large transfer (>$1M) | High | 15 minutes |
| Unusual volume (10x) | Medium | 1 hour |
| Relayer offline | High | 15 minutes |
| Contract pause | Critical | Immediate |
| Fraud proof submitted | Critical | Immediate |

## Emergency Procedures

### Pause Bridge

```python
# Emergency pause (2 of 7 signers)
bridge.emergency_pause(
    reason="Suspected exploit",
    signer_signatures=[sig1, sig2]
)
```

### Recovery Process

1. **Detection:** Monitoring alerts triggered
2. **Assessment:** Security team evaluates (15 min)
3. **Pause:** Emergency pause if needed (immediate)
4. **Investigation:** Root cause analysis (24-48h)
5. **Fix:** Develop and audit fix (1-7 days)
6. **Deploy:** Upgrade with timelock (48h)
7. **Resume:** Unpause after verification

### Fund Recovery

| Scenario | Recovery Method | Timeline |
|----------|-----------------|----------|
| Contract bug | Governance vote | 7 days |
| Key compromise | Emergency multisig | 24-48 hours |
| Chain reorg | Automatic | After finality |

## Implementation Reference

### Lock Contract Interface

```solidity
interface IBridgeLock {
    // Lock tokens for bridging
    function lock(
        address token,
        uint256 amount,
        uint256 targetChainId,
        address recipient
    ) external returns (bytes32 lockId);

    // Unlock tokens (by relayer consensus)
    function unlock(
        bytes32 lockId,
        bytes[] calldata signatures
    ) external;

    // Emergency pause
    function emergencyPause() external;
}
```

### Message Format

```json
{
    "version": 1,
    "sourceChainId": 1,
    "targetChainId": 137,
    "sender": "0x...",
    "recipient": "0x...",
    "token": "0x...",
    "amount": "1000000000000000000",
    "nonce": 12345,
    "timestamp": 1735570000,
    "deadline": 1735573600,
    "signature": "0x..."
}
```

## Audit Requirements

### Pre-Launch

- [ ] Smart contract audit (2+ firms)
- [ ] Cryptographic review
- [ ] Economic analysis
- [ ] Penetration testing

### Ongoing

- [ ] Annual re-audit
- [ ] Quarterly code review
- [ ] Continuous monitoring
- [ ] Bug bounty program

## Related Documentation

- [Cross-Chain Messaging](../protocol/CROSS_CHAIN_MESSAGING.md)
- [Atomic Swaps](../protocol/ATOMIC_SWAPS.md)
- [Relayer Guide](../ops/RELAYER_OPERATIONS.md)

---

*Bridge security is critical. Any suspected vulnerabilities should be reported to security@xai-blockchain.io*
