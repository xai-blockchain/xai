# XAI Bug Bounty Program

## Program Overview

The XAI Bug Bounty Program rewards security researchers who help secure the XAI blockchain ecosystem. As a community-driven project, all bounties are paid exclusively in **XAI tokens** from our development fund.

### Why Token Rewards?

XAI is built by and for its community. Token-only rewards:
- Align researcher incentives with project success
- Sustain the program within our limited budget
- Give researchers stake in the network they help protect

## Scope

### In Scope

| Component | Location | Priority |
|-----------|----------|----------|
| Core Blockchain | `xai/core/` | Critical |
| Consensus Engine | `xai/core/consensus/` | Critical |
| EVM Implementation | `xai/core/vm/` | Critical |
| Wallet | `xai/core/wallet.py` | Critical |
| P2P Networking | `xai/core/p2p/` | High |
| DeFi Protocols | `xai/core/defi/` | High |
| Browser Extension | `browser_wallet_extension/` | High |
| API Server | `xai/core/api/` | Medium |
| SDKs | `sdk/` | Medium |

### Out of Scope

- Third-party dependencies (report upstream)
- Social engineering attacks
- Physical attacks
- Volumetric DoS attacks
- Test/example code
- Already known issues

## Reward Structure

All rewards paid in **XAI tokens** from the development fund.

### Severity Tiers

| Severity | XAI Tokens | Vesting |
|----------|------------|---------|
| Critical | 25,000 - 50,000 XAI | 6-month linear vest |
| High | 10,000 - 25,000 XAI | 3-month linear vest |
| Medium | 2,500 - 10,000 XAI | None |
| Low | 500 - 2,500 XAI | None |

### Critical

**Network compromise or direct fund loss**
- Remote code execution on nodes
- Private key extraction
- Consensus bypass (double-spend)
- Unauthorized fund transfers
- Complete network takeover

### High

**Significant risk to funds or network**
- Chain reorganization attacks
- Validator exploitation
- Authentication bypass
- Privilege escalation
- Significant fund loss risk

### Medium

**Limited security impact**
- Information disclosure (keys, seeds)
- Partial DoS with low cost
- Transaction malleability
- Stored XSS
- Improper access control

### Low

**Minor security issues**
- Non-sensitive information disclosure
- Minor logic errors
- Limited-impact race conditions
- Reflected XSS

### Bonus Modifiers

| Condition | Modifier |
|-----------|----------|
| First report of type | +25% |
| Working PoC included | +25% |
| Fix PR included | +50% |
| Mainnet-relevant impact | +25% |

## Vesting Terms

To protect XAI token economics:

- **Critical**: 6-month linear vesting (monthly releases)
- **High**: 3-month linear vesting
- **Medium/Low**: Immediate transfer

Vesting starts after fix deployment. Researchers may opt for 50% immediate payment instead of vesting.

## Submission Process

### Submit via Email

**To**: security@xai-blockchain.io

```
Subject: [BUG BOUNTY] Brief Description

## Summary
One paragraph describing the vulnerability.

## Severity Assessment
Your assessment with justification.

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

## Suggested Fix (Optional)
How to remediate.

## Contact
- Name/Handle
- XAI address for payment
```

### Response Timeline

| Stage | Timeframe |
|-------|-----------|
| Acknowledgment | 24 hours |
| Initial Assessment | 72 hours |
| Status Updates | Weekly |
| Fix Deployed | Severity-dependent |
| Reward Payment | 30 days after fix |

## Responsible Disclosure

### Do

- Report vulnerabilities promptly
- Provide detailed reproduction steps
- Allow reasonable time to fix
- Keep findings confidential until fixed
- Test only against your own accounts

### Do Not

- Access others' data
- Cause service disruption
- Demand payment before disclosure
- Publicly disclose before fix
- Conduct social engineering
- Use aggressive automated scanning

## Legal Safe Harbor

We will not pursue legal action against researchers who:

1. Follow this policy
2. Report in good faith
3. Do not cause harm
4. Do not access others' data
5. Do not attempt extortion

## Recognition

### Hall of Fame

Contributors will be recognized by tier:

| Tier | Criteria |
|------|----------|
| Elite | Critical vulnerability found |
| Expert | 3+ High severity findings |
| Contributor | Any valid finding |

### Recognition Options

- Hall of Fame listing
- Security advisory credit
- Community contributor badge
- Anonymous if preferred

## Program Rules

### Eligibility

- Open globally (subject to legal restrictions)
- 18+ or parental consent required
- XAI team members ineligible
- First valid report receives reward

### Payment

- XAI tokens only
- Transfer to provided XAI address
- Subject to vesting for larger rewards
- Researcher responsible for taxes

### Modifications

- Terms may change with 30 days notice
- Pending submissions use terms at submission time

## Contact

- **Email**: security@xai-blockchain.io
- **PGP Key**: Available on request
- **Response**: 24-hour acknowledgment

## FAQ

**Q: Why only XAI tokens?**
A: As a community project, our development fund holds XAI. This aligns your interests with ours.

**Q: What's the vesting period for?**
A: Large rewards vest over time to protect token economics and demonstrate long-term alignment.

**Q: Can I test on mainnet?**
A: No. Use testnet only. Mainnet exploitation disqualifies you.

---

**Last Updated**: January 1, 2026
**Program Version**: 2.0
**Program Status**: Active
