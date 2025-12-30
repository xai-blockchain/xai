---
status: pending
priority: p2
issue_id: "039"
tags: [security, high, browser-wallet, encryption]
dependencies: ["035"]
---

# Browser Wallet Encryption Not Enforced by Default

## Problem Statement

The browser wallet extension offers encryption via a confirm() dialog but users can skip it. Session secrets and API keys can be stored in plaintext if the user declines encryption.

**Why it matters:** Private keys exposed if user skips encryption and browser storage is compromised.

## Findings

**Location:** `/home/hudson/blockchain-projects/xai/src/xai/browser_wallet_extension/popup-encrypted.js:783-791`

**Evidence:** Encryption is offered but not mandatory.

## Proposed Solutions

### Option 1: Make Encryption Mandatory (Recommended)
- Remove the skip option for sensitive data
- Require password setup on first use
- **Pros:** Maximum security
- **Cons:** Slightly worse UX
- **Effort:** Small (2-4 hours)
- **Risk:** Low

## Recommended Action

Make encryption mandatory with no skip option.

## Acceptance Criteria

- [ ] No option to skip encryption for private keys
- [ ] Password required on first use
- [ ] Clear UI indicating encryption is active

## Work Log

| Date | Action | Learnings |
|------|--------|-----------|
| 2025-12-30 | Identified during security audit | Users will skip security if given the option |
