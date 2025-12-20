# Security Policy

## Reporting a Vulnerability

The XAI team takes security vulnerabilities seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **security@xai.network**

Include the following information:
- Type of vulnerability (e.g., reentrancy, overflow, access control)
- Full path to the affected source file(s)
- Step-by-step instructions to reproduce the issue
- Proof of concept or exploit code (if available)
- Potential impact of the vulnerability

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 7 days
- **Resolution Timeline**: Depends on severity, typically 30-90 days
- **Disclosure**: Coordinated with reporter after fix is deployed

## Bug Bounty Program

We offer bug bounties paid in **XAI tokens** for responsibly disclosed vulnerabilities.

### Severity Levels and Rewards

| Severity | Description | Reward |
|----------|-------------|--------|
| **Critical** | Direct loss of funds, consensus failure, chain halt | Up to 50,000 XAI |
| **High** | Significant impact on functionality or security | Up to 10,000 XAI |
| **Medium** | Limited impact, requires specific conditions | Up to 2,500 XAI |
| **Low** | Minor issues, best practice violations | Up to 500 XAI |

### Scope

**In Scope:**
- Blockchain core (`src/xai/core/`)
- Wallet implementation (`src/xai/wallet/`)
- EVM/Smart contracts (`src/xai/evm/`)
- Cryptographic implementations (`src/xai/crypto/`)
- P2P networking (`src/xai/network/`)
- Atomic swap implementation
- AI governance modules

**Out of Scope:**
- Third-party dependencies (report to upstream)
- Issues already known or reported
- Theoretical vulnerabilities without proof of concept
- Social engineering attacks
- Denial of service attacks

### Rules

- Do not exploit vulnerabilities beyond proof of concept
- Do not access or modify other users' data
- Do not disrupt network operations
- Act in good faith

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x (current) | Yes |
| 0.1.x | Security fixes only |
| < 0.1 | No |

## Security Best Practices

When running an XAI node:
- Keep your node software updated
- Use strong passwords for wallet encryption
- Enable firewall and restrict RPC access
- Monitor for unusual activity
- Back up your keys securely offline
- Review smart contracts before interaction

## Security Tools

Run security checks before releases:

```bash
# Static analysis
bandit -r src/

# Dependency audit
pip-audit

# Full security suite
make security-check
```
