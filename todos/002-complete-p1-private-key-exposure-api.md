# Private Key Exposure via API Response

---
status: complete
priority: p1
issue_id: 002
tags: [security, wallet, api, code-review]
dependencies: []
completed_date: 2025-12-07
---

## Problem Statement

The `/wallet/create` endpoint returns private keys in plain text in the HTTP response body. This violates the fundamental security principle that private keys should **never leave the client**.

## Findings

### Location
**File:** `src/xai/core/api_wallet.py` (Lines 175-198)

### Evidence

```python
def create_wallet_handler(self) -> Tuple[Dict[str, Any], int]:
    wallet = Wallet()
    # ...
    return (
        jsonify({
            "success": True,
            "address": wallet.address,
            "public_key": public_key,
            "private_key": private_key,  # CRITICAL EXPOSURE
            "warning": "Save private key securely. Cannot be recovered.",
        }),
        200,
    )
```

### Impact

- Private keys transmitted over network (even HTTPS can be intercepted via MITM, compromised CAs, or TLS stripping)
- Keys may be logged by proxies, load balancers, or application logs
- Browser history/cache exposure
- **Any compromise = permanent loss of funds**
- Violates blockchain security best practices

## Proposed Solutions

### Option A: Client-Side Only Generation (Recommended)
**Effort:** Medium | **Risk:** Low

Remove server-side wallet generation entirely. Force client-side generation:

```python
@app.route("/wallet/create", methods=["POST"])
def create_wallet_handler():
    return jsonify({
        "error": "Wallet generation must be performed client-side",
        "documentation": "/docs/wallet-generation",
        "libraries": {
            "javascript": "ethers.js, web3.js",
            "python": "eth-account, web3.py"
        }
    }), 400
```

### Option B: Encrypted Wallet Response
**Effort:** Medium | **Risk:** Medium

If server-side generation is required, return encrypted wallet:

```python
def create_wallet_handler(self):
    password = request.json.get("encryption_password")
    if not password or len(password) < 12:
        return jsonify({"error": "Strong password required"}), 400

    wallet = Wallet()
    encrypted_keystore = wallet.encrypt_keystore(password)  # AES-256-GCM

    return jsonify({
        "success": True,
        "address": wallet.address,
        "encrypted_keystore": encrypted_keystore,  # User decrypts locally
        "warning": "Never share your password"
    }), 200
```

### Option C: BIP-39 Mnemonic Only
**Effort:** Small | **Risk:** Low

Return only mnemonic phrase (still risky but standard practice):

```python
def create_wallet_handler(self):
    mnemonic = Wallet.generate_mnemonic()
    # Derive address from mnemonic for verification
    address = Wallet.from_mnemonic(mnemonic).address

    return jsonify({
        "success": True,
        "mnemonic": mnemonic,  # 12/24 words
        "address": address,
        "warning": "Write down mnemonic. Never store digitally."
    }), 200
```

## Recommended Action

Implement Option A (client-side only) as primary approach. This is a **production blocker**.

## Technical Details

**Affected Components:**
- Wallet API (`api_wallet.py`)
- Mobile wallet bridge
- Browser extension

**Database Changes:** None

## Acceptance Criteria

- [x] `/wallet/create` endpoint returns encrypted keystore (Option B implemented)
- [x] No private keys appear in any API response
- [x] Security audit confirms no key leakage paths
- [x] Wallet class has __repr__ and __str__ guards to prevent accidental exposure
- [x] All security tests pass (17/17 tests)

## Work Log

| Date | Action | Result |
|------|--------|--------|
| 2025-12-05 | Issue identified by security-sentinel agent | Critical vulnerability |
| 2025-12-07 | Implemented encrypted keystore response (Option B) | `/wallet/create` now requires password, returns AES-256-GCM encrypted keystore |
| 2025-12-07 | Added Wallet serialization guards | Added __repr__, __str__, __getstate__ to prevent accidental key exposure |
| 2025-12-07 | Verified all security tests pass | 17/17 tests pass, no private keys in any response |

## Resolution Summary

**Implementation:** Option B (Encrypted Wallet Response) was implemented with enhanced security.

**Changes Made:**

1. **API Endpoint Protection** (`src/xai/core/api_wallet.py`):
   - `/wallet/create` now requires 12+ character encryption password
   - Returns AES-256-GCM encrypted keystore instead of plain private key
   - Uses PBKDF2 key derivation with 100k iterations
   - Includes comprehensive security warnings and client decryption guide
   - HTTP 400 error for missing/weak passwords

2. **Wallet Class Hardening** (`src/xai/core/wallet.py`):
   - Added `__repr__()` method: Returns safe representation without private key
   - Added `__str__()` method: Returns safe string without private key
   - Added `__getstate__()` method: Logs security warning on pickle serialization
   - Existing `to_dict()` and `to_public_dict()` already safe (no private key)

3. **Security Test Coverage**:
   - 17 comprehensive security tests verify no private key exposure
   - Tests validate password requirements, encryption strength, and response structure
   - Regression tests ensure vulnerability stays fixed

**Security Posture:**
- Private keys NEVER transmitted in plain text over HTTP
- Encrypted keystores use industry-standard AES-256-GCM
- Client-side decryption enforced (password never stored server-side)
- Multiple layers of protection prevent accidental key exposure

## Resources

- [OWASP Cryptographic Failures](https://owasp.org/Top10/A02_2021-Cryptographic_Failures/)
- [BIP-39 Mnemonic Standard](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)
