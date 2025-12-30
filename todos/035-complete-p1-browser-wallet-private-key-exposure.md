---
status: complete
priority: p1
issue_id: "035"
tags: [security, critical, browser-wallet, cryptography]
dependencies: []
---

# Browser Wallet Extension Transmits Private Keys to Backend

## Problem Statement

The browser wallet extension sends private keys over HTTP/HTTPS to a backend signing endpoint. This is a fundamental security anti-pattern that exposes private keys to network interception, server-side logging, memory exposure, and backend compromise.

**Why it matters:** Complete wallet compromise if network is intercepted. Total loss of user funds. Violation of fundamental cryptographic security principles.

## Findings

**Location:** `/home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension/popup.js:102-109`

**Evidence:**
```javascript
// From popup.js - signPayload function
const response = await fetch(`${host}/wallet/sign`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message_hash: msgHashHex,
    private_key: privateKeyHex,  // CRITICAL: Private key sent over network
  }),
});
```

**CVSS Score:** 9.8 (Critical)

## Proposed Solutions

### Option 1: Client-Side Signing with Web Crypto API (Recommended)
- **Pros:** Industry standard, no network exposure, hardware wallet compatible
- **Cons:** Requires refactoring popup.js
- **Effort:** Medium (2-3 days)
- **Risk:** Low

### Option 2: Client-Side Signing with secp256k1-js Library
- **Pros:** Well-tested library, similar to Bitcoin implementations
- **Cons:** Additional dependency
- **Effort:** Medium (2-3 days)
- **Risk:** Low

### Option 3: Hardware Wallet Only for Signing
- **Pros:** Maximum security
- **Cons:** Requires hardware wallet, poor UX for casual users
- **Effort:** High (1 week)
- **Risk:** Medium (UX impact)

## Recommended Action

Implement Option 1 (Client-Side Signing with Web Crypto API) immediately. Deprecate the `/wallet/sign` backend endpoint.

## Technical Details

**Affected files:**
- `src/xai/browser_wallet_extension/popup.js`
- `src/xai/core/api/api_wallet.py` (sign_transaction_handler)

**Components:** Browser wallet extension, Wallet API

## Acceptance Criteria

- [ ] Private keys never leave the browser extension
- [ ] `/wallet/sign` endpoint deprecated with warning
- [ ] All transaction signing happens client-side
- [ ] Existing wallets continue to function
- [ ] Unit tests verify no private key transmission

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Browser extension architecture requires complete redesign of signing flow |

## Resources

- [Web Crypto API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)
- [secp256k1-js Library](https://github.com/paulmillr/noble-secp256k1)
