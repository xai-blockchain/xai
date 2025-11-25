# Security Policy

## Supported Versions

We take security seriously and actively maintain the following versions of the XAI blockchain project:

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| < Latest | :x:               |

We recommend always using the latest version to ensure you have the most recent security patches and improvements.

## Reporting a Vulnerability

We appreciate the security research community's efforts in helping us maintain the security of the XAI blockchain. If you believe you have found a security vulnerability, please report it to us responsibly.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by:

1. **Email**: Send details to **security@xai.io** (or create a private security advisory on GitHub)
2. **Private Security Advisory**: Use GitHub's [private vulnerability reporting feature](https://github.com/[your-org]/crypto/security/advisories/new)

### What to Include

Please include as much of the following information as possible:

- Type of vulnerability (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the vulnerability
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the vulnerability
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### Response Timeline

- **Initial Response**: Within 48 hours of receiving your report
- **Status Update**: Within 7 days with an assessment of the report
- **Resolution**: Timeline varies based on severity and complexity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium: 30-90 days
  - Low: Best effort

### What to Expect

1. **Acknowledgment**: We'll acknowledge receipt of your vulnerability report
2. **Assessment**: We'll investigate and validate the reported vulnerability
3. **Updates**: We'll keep you informed about our progress
4. **Resolution**: Once fixed, we'll notify you and coordinate public disclosure
5. **Credit**: With your permission, we'll publicly acknowledge your responsible disclosure

## Security Best Practices

### For Node Operators

- Keep your node software updated to the latest version
- Use strong, unique passwords for wallet encryption
- Enable firewall protection and limit exposed ports
- Regularly backup your wallet and configuration files
- Use hardware wallets for storing significant amounts
- Enable two-factor authentication where available
- Monitor your node for unusual activity

### For Developers

- Follow secure coding practices
- Review the CONTRIBUTING.md guidelines
- Ensure all dependencies are up to date
- Run security tests before submitting pull requests
- Never commit sensitive data (private keys, passwords, API keys)
- Use environment variables for configuration secrets
- Implement proper input validation and sanitization

### For Users

- Never share your private keys or seed phrases
- Verify wallet addresses before sending transactions
- Use official wallet applications from trusted sources
- Be cautious of phishing attempts
- Keep your wallet software updated
- Use strong passwords and enable all available security features
- Consider using a hardware wallet for large holdings

## Security Features

The XAI blockchain implements multiple security layers:

- **Cryptographic Security**: Industry-standard encryption algorithms
- **Multi-signature Support**: Enhanced wallet security with multi-sig capabilities
- **Time-locked Transactions**: Protection through time capsule functionality
- **Anomaly Detection**: AI-powered fraud detection systems
- **Rate Limiting**: Protection against spam and DoS attacks
- **Peer Security**: P2P network security measures
- **Audit Trail**: Comprehensive blockchain validation and logging

## Vulnerability Disclosure Policy

When we receive a security vulnerability report:

1. We work to verify and fix the vulnerability
2. We prepare security advisories and patches
3. We coordinate with reporters on disclosure timing
4. We release patches and public advisories
5. We update our security documentation

We aim for responsible disclosure that:
- Protects users by fixing vulnerabilities before public disclosure
- Gives credit to security researchers
- Maintains transparency with our community
- Follows industry best practices

## Security Audits

We conduct regular security audits of our codebase and welcome independent security reviews. If you're interested in conducting a security audit, please contact us at security@xai.io.

## Bug Bounty Program

We operate a continuous bug bounty program so responsible researchers can report issues once they are verified on testnet or in production. Scope includes node API/auth, consensus state, monitoring pipelines, infrastructure automation, and client libraries. Targeted attack vectors such as denial of service, consensus rollback, funds theft, and sensitive-data exposure are high-impact candidates for rewards.

### Submission guidelines
- Report issues privately to **security@xai.io** (or via GitHub’s private advisories at `https://github.com/[your-org]/crypto/security/advisories/new`).
- Provide reproduction steps, configuration, expected vs. observed behavior, and any PoC code or proof logs.
- Include the environment you tested (devnet/staging/mainnet), chain height (if applicable), and the XAI addresses involved.
- We prefer coordinated disclosure timelines—please avoid public disclosure until we publish a fix or advisories together.

### Reward tiers
- **Critical** (consensus failure, fund loss, private key leakage): 20,000–50,000 XAI tokens.
- **High** (fund drainage vulnerability, persistent DoS, API misconfiguration leaking secrets): 5,000–20,000 XAI tokens.
- **Medium** (privilege escalation, validation bypass, telemetry manipulation): 1,000–5,000 XAI tokens.
- **Low** (info leaks, documentation gaps, minor fuzzable inputs): 250–1,000 XAI tokens.

All valid reports that meet quality standards are compensated in **XAI tokens only**; no other token/payment types are supported.

Rewards are ceded once we verify the issue, merge a fix, and agree on disclosure timing. We may modify payouts to reflect evolving risk or to promote important research paths.

## Contact

- **Security Email**: security@xai.io
- **General Contact**: info@xai.io
- **Website**: https://xai.io
- **GitHub Security Advisories**: [Create Private Advisory](https://github.com/[your-org]/crypto/security/advisories/new)

## Updates to This Policy

We may update this security policy from time to time. Please check back regularly for the latest information.

---

**Last Updated**: January 2025

Thank you for helping keep XAI and our community safe!
