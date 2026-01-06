# Security Policy

## Reporting a Vulnerability

Please do not report security issues via public issues or discussions. Send reports to:

- Email: security@xai.network

Include:
- Affected file paths and versions
- Reproduction steps and proof of concept
- Impact assessment and any mitigations

## Scope

In scope:
- Core node and API code under `src/xai/`
- Wallet CLI under `src/xai/wallet/`

Out of scope:
- Third-party dependencies (report to upstream)
- Denial-of-service testing against public infrastructure

## Coordinated Disclosure

We will acknowledge reports and coordinate a fix before public disclosure.

## Supported Versions

Only the default branch is supported for security fixes.

## Bug Bounty

There is no public bug bounty program at this time.

## Public Testnet Hardening

Operators running the public testnet should enable proxy-aware IP resolution and
optional IP allow/deny lists to protect rate limits and block abusive traffic.

Recommended environment variables:

- `XAI_TRUST_PROXY_HEADERS=1`
- `XAI_TRUSTED_PROXY_IPS` or `XAI_TRUSTED_PROXY_NETWORKS` (Cloudflare/edge IP ranges)
- `XAI_API_IP_ALLOWLIST` (optional, comma-separated IPs/CIDR ranges)
- `XAI_API_IP_DENYLIST` (optional, comma-separated IPs/CIDR ranges)
- `XAI_PUBLIC_TESTNET_HARDENED=1`
- `XAI_WRITE_AUTH_REQUIRED=1`
- `XAI_WRITE_AUTH_EXEMPT_PATHS` (optional, comma-separated path prefixes)
