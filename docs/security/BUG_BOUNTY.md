# XAI Bug Bounty Program

**Version:** 1.0.0
**Effective Date:** 2025-12-30
**Status:** Active

## Program Overview

The XAI Bug Bounty Program rewards security researchers who discover and responsibly disclose vulnerabilities in the XAI blockchain and related infrastructure.

## Scope

### In Scope

| Component | Repository | Priority |
|-----------|------------|----------|
| Core Blockchain | `xai/core/` | Critical |
| Consensus Engine | `xai/core/consensus/` | Critical |
| EVM Implementation | `xai/core/vm/` | Critical |
| Wallet | `xai/core/wallet.py` | Critical |
| P2P Networking | `xai/core/p2p/` | High |
| DeFi Protocols | `xai/core/defi/` | High |
| API Server | `xai/core/api/` | Medium |
| SDKs | `sdk/` | Medium |
| Browser Extension | `browser_wallet_extension/` | High |

### Out of Scope

- Third-party dependencies (report upstream)
- Social engineering attacks
- Physical attacks
- Denial of service (volumetric)
- Issues in test/example code
- Already known issues
- Issues requiring physical access

## Vulnerability Classifications

### Critical (Up to $50,000)

- Remote code execution on node
- Private key extraction
- Consensus bypass (double-spend)
- Unauthorized fund transfer
- Complete network takeover

### High ($10,000 - $25,000)

- Significant fund loss risk
- Chain reorganization attacks
- Validator slashing exploitation
- Authentication bypass
- Privilege escalation

### Medium ($2,500 - $10,000)

- Information disclosure (keys, seeds)
- Partial DoS with low cost
- Transaction malleability
- Cross-site scripting (stored)
- Improper access control

### Low ($500 - $2,500)

- Information disclosure (non-sensitive)
- Minor logic errors
- Race conditions (limited impact)
- Cross-site scripting (reflected)

## Rewards

| Severity | Minimum | Maximum |
|----------|---------|---------|
| Critical | $25,000 | $50,000 |
| High | $10,000 | $25,000 |
| Medium | $2,500 | $10,000 |
| Low | $500 | $2,500 |

### Bonus Multipliers

| Condition | Multiplier |
|-----------|------------|
| First to report | 1.25x |
| With working PoC | 1.25x |
| With fix PR | 1.5x |
| Mainnet impact | 1.5x |

## Submission Process

### 1. Report via Email
Send to: security@xai-blockchain.io

### 2. Required Information

```
Subject: [BUG BOUNTY] Brief Description

## Summary
One paragraph describing the vulnerability.

## Severity Assessment
Your assessment of severity with justification.

## Affected Components
- File paths
- Functions
- Versions

## Steps to Reproduce
1. Step one
2. Step two
3. ...

## Proof of Concept
Code or commands to demonstrate.

## Impact
What an attacker could achieve.

## Suggested Fix
(Optional) How to remediate.

## Your Information
- Name/Handle
- Payment preference (ETH/BTC/USDC/wire)
- PGP key (optional)
```

### 3. Response Timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgment | 24 hours |
| Initial Assessment | 72 hours |
| Status Update | Weekly |
| Fix Deployed | Depends on severity |
| Reward Payment | 30 days after fix |

## Rules

### Do

- Report vulnerabilities promptly
- Provide detailed reproduction steps
- Give us reasonable time to fix
- Keep findings confidential until fixed
- Test only against your own accounts

### Do Not

- Access others' data
- Cause service disruption
- Demand payment before disclosure
- Publicly disclose before fix
- Conduct social engineering
- Use automated scanning (causes DoS)

## Legal Safe Harbor

We will not pursue legal action against researchers who:

1. Follow this policy
2. Report in good faith
3. Do not cause harm
4. Do not access others' data
5. Do not demand extortion

This safe harbor applies to security research only.

## Hall of Fame

Researchers who have contributed will be recognized:

| Researcher | Contribution | Date |
|------------|--------------|------|
| *Launching soon* | | |

## Contact

- **Email:** security@xai-blockchain.io
- **PGP Key:** [Available on keyserver]
- **Response:** 24-hour SLA

## Program Updates

This program may be updated. Researchers will be notified of material changes. The version at time of submission applies.

---

*Last updated: 2025-12-30*
